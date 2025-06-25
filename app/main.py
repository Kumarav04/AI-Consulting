# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app import api
import os

app = FastAPI()

# CORS (if front-end is separate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to your frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/")
def read_root():
    return FileResponse(os.path.join("static", "index.html"))

# Include your API routes
app.include_router(api.router)
