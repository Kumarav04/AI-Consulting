from __future__ import annotations

import base64, tempfile, uuid, aiofiles
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import AsyncOpenAI, OpenAIError

from app.standardize import standardize_csv
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
    data   = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt required.")

    if not STATE["csv"]:
        raise HTTPException(400, "Upload a CSV first.")

    # ── First call after upload: treat prompt as user goals & analyse ──
    if STATE["analysis"] is None:
        STATE["goals"] = prompt            # remember the goals
        try:
            std_csv = standardize_csv(STATE["csv"])
            images  = create_visualizations(std_csv, STATE["csv"].parent)
        except Exception as exc:
            raise HTTPException(400, f"Processing failed: {exc}") from exc

        encoded = [
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64," + base64.b64encode(img.read_bytes()).decode()
                },
            }
            for img in images
        ]

        system_prompt = (
            f"You are ConsultBot, a highly skilled data analyst with expertise in {STATE['use_case']}.\n"
            f"The user’s goals are: {STATE['goals']}.\n\n"
            "Your task is to interpret the uploaded dataset and the associated charts to generate practical, data-driven insights and recommendations that directly support the user's goals.\n"
            "- Do not speculate or hallucinate data.\n"
            "- Use only what is visible in the charts and dataset.\n"
            "- If you are unsure, say so.\n\n"
            "Important: If the user asks a question unrelated to the dataset, charts, or stated goals, respond politely:\n"
            "→ \"I'm here to help with business insights based on your uploaded data. Let's focus on that.\"\n"
        )

        try:
            res = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": [*encoded, {"type": "text", "text": "Provide your analysis."}]},
                ],
            )
            summary = res.choices[0].message.content
        except OpenAIError as exc:
            raise HTTPException(500, f"OpenAI error: {exc}") from exc

        STATE["analysis"] = {"summary": summary, "images": images}
        return JSONResponse({"reply": summary, "chart_paths": [img.name for img in images]})

    # ── Follow-up questions ──────────────────────────────────────────
    follow_system = (
        f"You are ConsultBot, continuing to assist with business analytics for {STATE['use_case']}.\n"
        f"The user’s goals are: {STATE['goals']}.\n\n"
        "Use only the original dataset, the charts, and the prior analysis to answer follow-up questions.\n"
        "Stay strictly within the context of the dataset and business goals.\n"
        "- Do not answer questions about unrelated topics (e.g., tanks, philosophy, life advice).\n"
        "- If a question is out of scope, say:\n"
        "→ \"I'm here to help with business insights based on your uploaded data. Let's focus on that.\"\n"
    )

    try:
        res = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": follow_system},
                {"role": "assistant", "content": STATE["analysis"]["summary"]},
                {"role": "user", "content": prompt},
            ],
        )
        answer = res.choices[0].message.content
    except OpenAIError as exc:
        raise HTTPException(500, f"OpenAI error: {exc}") from exc

    return JSONResponse({"reply": answer})