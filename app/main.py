# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
from app import api
import tempfile, pathlib

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join("static", "index.html"))

app.include_router(api.router)

app.mount(
    "/generated",
    StaticFiles(directory=pathlib.Path(tempfile.gettempdir())),
    name="generated",
)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
