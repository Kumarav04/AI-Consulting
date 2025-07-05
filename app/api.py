from __future__ import annotations

"""ConsultBot backend – revised for two‑step workflow & per‑use‑case prompting."""

import base64
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import AsyncOpenAI, OpenAIError

from app.standardize import standardize_csv
from app.visualize import create_visualizations

# ────────────────────────────────────────────────────────────
# Runtime stores
# ────────────────────────────────────────────────────────────

# Dialogue turns (for normal chat history)
SESSIONS: dict[str, list[dict]] = defaultdict(list)

# Upload bookkeeping per session: {session_id: {file, use_case, goals, analysis}}
UPLOAD_STORE: dict[str, dict] = {}


def get_session_id(session_id: str | None = Header(None)) -> str:
    """Return supplied X‑Session‑ID or create a new UUID."""
    return session_id or str(uuid4())


# ────────────────────────────────────────────────────────────
# OpenAI client
# ────────────────────────────────────────────────────────────

client = AsyncOpenAI()  # picks up OPENAI_API_KEY from env
OPENAI_MODEL = "gpt-4o"

router = APIRouter()

# ────────────────────────────────────────────────────────────
# /upload  – store file & use‑case (no analysis yet)
# ────────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    use_case: str = Query(..., description="Business use‑case, e.g. 'Revenue Optimization'"),
    session_id: str = Depends(get_session_id),
):
    """Persist raw file; analysis happens later when user goals are known."""

    # Save to tmp
    tmpdir = Path(tempfile.gettempdir())
    saved_path = tmpdir / f"{uuid.uuid4().hex}_{file.filename}"
    async with aiofiles.open(saved_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    # Cache metadata
    UPLOAD_STORE[session_id] = {
        "file": saved_path,
        "use_case": use_case,
        "goals": None,
        # "analysis" key will be added later
    }

    return JSONResponse({"ok": True, "session_id": session_id})


# ────────────────────────────────────────────────────────────
# /chat – two‑stage: (1) collect goals, (2) analyse & converse
# ────────────────────────────────────────────────────────────


@router.post("/chat")
async def chat(
    request: Request,
    session_id: str = Depends(get_session_id),
    x_chat_stage: str = Header("follow_up"),  # "user_goals" | "follow_up"
    x_use_case: str = Header("General"),
):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return PlainTextResponse("No prompt provided.", status_code=400)

    # ───────── Stage 1 – record user goals ──────────
    if x_chat_stage == "user_goals":
        if session_id not in UPLOAD_STORE:
            return PlainTextResponse("Please upload a file first.", status_code=400)
        UPLOAD_STORE[session_id]["goals"] = prompt
        return JSONResponse({"reply": "Got it – I'll analyse the data next."})

    # ───────── Stage 2 – analyse & chat ──────────
    if session_id not in UPLOAD_STORE:
        return PlainTextResponse("No file found for this session.", status_code=400)

    record = UPLOAD_STORE[session_id]
    csv_path: Path = record["file"]
    use_case: str = record["use_case"]
    goals: str = record.get("goals") or "No specific goals supplied."

    # Perform heavy work **once** per session
    if "analysis" not in record:
        try:
            std_csv = standardize_csv(csv_path)
            images = create_visualizations(std_csv, csv_path.parent)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(400, f"Processing failed: {exc}") from exc

        # Build context‑aware system prompt
        system_prompt = (
            f"You are ConsultBot specialising in {use_case}. "
            f"The user's objectives: {goals}. "
            "First describe what the charts reveal, then give data‑driven recommendations."
        )

        encoded_images = [
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,"
                    + base64.b64encode(img.read_bytes()).decode()
                },
            }
            for img in images
        ]

        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            *encoded_images,
                            {"type": "text", "text": "Provide your analysis."},
                        ],
                    },
                ],
            )
            summary = response.choices[0].message.content
        except OpenAIError as exc:  # pragma: no cover
            raise HTTPException(500, f"OpenAI request failed: {exc}") from exc

        # Cache
        record["analysis"] = {
            "csv": std_csv,
            "images": images,
            "summary": summary,
        }

        # Return charts + summary
        return JSONResponse(
            {
                "reply": summary,
                "chart_paths": [img.name for img in images],
                "session_id": session_id,
            }
        )

    # ───────── Subsequent follow‑ups ──────────
    history = SESSIONS[session_id][-15:]
    messages = [
        {
            "role": "system",
            "content": (
                f"You are ConsultBot specialising in {use_case}. "
                "Use the earlier summary and any charts as context."
            ),
        },
        {"role": "assistant", "content": record["analysis"]["summary"]},
        *history,
        {"role": "user", "content": prompt},
    ]

    try:
        response = await client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
        reply = response.choices[0].message.content
    except OpenAIError as exc:  # pragma: no cover
        raise HTTPException(500, f"OpenAI request failed: {exc}") from exc

    # Store history for context (optional)
    SESSIONS[session_id].extend(
        [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": reply},
        ]
    )

    return PlainTextResponse(reply, headers={"X-Session-ID": session_id})
