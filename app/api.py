# app/api.py
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
import asyncio
import openai

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}

@router.post("/chat")
async def chat(prompt: str):
    async def stream():
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in response:
            yield chunk.choices[0].delta.get("content", "")
            await asyncio.sleep(0)
    return StreamingResponse(stream(), media_type="text/plain")
