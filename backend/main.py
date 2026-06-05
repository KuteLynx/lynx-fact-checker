"""
Lynx Fact Checker — FastAPI Backend 🐱
POST /verify → recibe URL de TikTok, ejecuta pipeline, devuelve JSON combinado.
"""

from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno desde backend/.env (desarrollo local)
load_dotenv(Path(__file__).parent / ".env")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import verify
import os

app = FastAPI(title="lynx-fact-checker", version="0.1.0")

# Orígenes permitidos: configurable via env, fallback a dev
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST"],
    allow_headers=["*"],
)


class VerifyRequest(BaseModel):
    url: str


class VerifyResponse(BaseModel):
    success: bool
    extractor: dict | None = None
    filter: dict | None = None
    combined_text: str | None = None
    whisper_needed: bool = False
    whisper_output: str | None = None
    ai_analysis: dict | None = None
    error: str | None = None


@app.post("/verify", response_model=VerifyResponse)
async def verify_endpoint(req: VerifyRequest):
    result = verify(req.url)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Error desconocido"))

    return VerifyResponse(**result)


@app.get("/health")
async def health():
    return {"status": "ok"}
