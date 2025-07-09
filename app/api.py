from __future__ import annotations

import base64, tempfile, uuid, aiofiles
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import AsyncOpenAI, OpenAIError

from app.standardize import standardize_csv, ColumnMappingNeeded
from app.visualize  import create_visualizations

client       = AsyncOpenAI()
OPENAI_MODEL = "gpt-4o"
router       = APIRouter()

# single-user in-memory state (latest CSV + analysis cache + goals)
STATE: dict[str, object] = {
    "csv"     : None,   # Path to last uploaded CSV
    "analysis": None,   # {summary, images}
    "use_case": None,   # e.g. "Revenue Optimization"
    "goals"   : None,   # free-form text supplied by user
}

# ────────────────────────────────────────────
# /upload – save file & remember use-case
# ────────────────────────────────────────────

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    use_case: str = Query(..., description="Business use-case, e.g. 'Revenue Optimization'"),
):
    tmpdir = Path(tempfile.gettempdir())
    saved  = tmpdir / f"{uuid.uuid4().hex}_{file.filename}"
    async with aiofiles.open(saved, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    STATE.update({"csv": saved, "analysis": None, "use_case": use_case, "goals": None})
    return {"ok": True}


# ────────────────────────────────────────────
# /chat – first call runs analysis, later calls follow-up
# ────────────────────────────────────────────


@router.post("/chat")
async def chat(request: Request):
    """Single-user chat flow:
       1) first prompt  -> treat as goals, try analysis
       2) mapping phase -> user maps missing columns
       3) follow-ups    -> normal Q&A, staying on topic
    """
    data   = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt required.")

    if not STATE["csv"]:
        raise HTTPException(400, "Upload a CSV first.")

    # ──────────────────────────────────────────────
    # 1) FIRST CALL  ➜ run analysis or ask for mapping
    # ──────────────────────────────────────────────
    if STATE["analysis"] is None:
        STATE["goals"] = prompt                 # remember goals
        try:
            std_csv = standardize_csv(STATE["csv"])
            images  = create_visualizations(std_csv, STATE["csv"].parent)
        except ColumnMappingNeeded as e:
            # ask user to map missing columns
            STATE["missing"] = e.missing
            missing_lines   = "\n".join(f"* {c}" for c in e.missing)
            return JSONResponse({
                "reply": (
                    "I need your help mapping these missing columns:\n"
                    f"{missing_lines}\n\n"
                    "Please reply in the format:\n"
                    "`<CSV column>` = <Canonical column>`"
                )
            })

        # analysis succeeded — call GPT, cache & return
        summary = await _gpt_analysis(images)
        STATE["analysis"] = {"summary": summary, "images": images}
        return JSONResponse({"reply": summary, "chart_paths": [img.name for img in images]})

    # ──────────────────────────────────────────────
    # 2) MAPPING PHASE  ➜ user supplies column map
    # ──────────────────────────────────────────────
    if STATE.get("missing"):
        user_map = {}
        for line in prompt.splitlines():
            if "=" in line:
                src, canon = [s.strip() for s in line.split("=", 1)]
                user_map[src] = canon

        try:
            std_csv = standardize_csv(STATE["csv"], user_map=user_map)
            images  = create_visualizations(std_csv, STATE["csv"].parent)
            del STATE["missing"]            # mapping worked
        except ColumnMappingNeeded as e:
            STATE["missing"] = e.missing    # still missing
            return JSONResponse({"reply": "Still missing: " + ", ".join(e.missing)})

        summary = await _gpt_analysis(images)
        STATE["analysis"] = {"summary": summary, "images": images}
        return JSONResponse({"reply": summary, "chart_paths": [img.name for img in images]})

    # ──────────────────────────────────────────────
    # 3) FOLLOW-UP QUESTIONS
    # ──────────────────────────────────────────────
    follow_system = (
        f"You are ConsultBot, specialised in {STATE['use_case']}.\n"
        f"User goals: {STATE['goals']}.\n"
        "Only answer questions related to this dataset and goals.\n"
        "If out of scope, say:\n"
        "\"I'm here to help with business insights based on your data. Let's focus on that.\""
    )

    try:
        res = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system",    "content": follow_system},
                {"role": "assistant", "content": STATE['analysis']['summary']},
                {"role": "user",      "content": prompt},
            ],
        )
        answer = res.choices[0].message.content
    except OpenAIError as exc:
        raise HTTPException(500, f"OpenAI error: {exc}") from exc

    return JSONResponse({"reply": answer})


# ------------------------------------------------------------------
# helper: call GPT for the initial analysis (with images & goals)
# ------------------------------------------------------------------
async def _gpt_analysis(images):
    encoded = [
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(img.read_bytes()).decode()
            },
        } for img in images
    ]

    system_prompt = (
        f"You are ConsultBot, a highly-skilled data analyst specialised in {STATE['use_case']}.\n"
        f"User goals: {STATE['goals']}.\n"
        "Focus ONLY on insights from the dataset and charts.\n"
        "If asked something unrelated, reply:\n"
        "\"I'm here to help with business insights based on your uploaded data. Let's focus on that.\""
    )

    res = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": [*encoded, {"type": "text", "text": "Provide your analysis."}]},
        ],
    )
    return res.choices[0].message.content