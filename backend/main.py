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

import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import verify
import os

app = FastAPI(title="lynx-fact-checker", version="0.1.0")

# Patrón para validar que sea URL de TikTok
TIKTOK_URL_PATTERN = re.compile(
    r'^https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/',
    re.IGNORECASE
)

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
    text: str | None = None  # Texto opcional que el usuario pega manualmente


class VerifyResponse(BaseModel):
    success: bool
    extractor: dict | None = None
    extraction_limited: bool = False
    filter: dict | None = None
    combined_text: str | None = None
    manual_text_status: dict | None = None
    whisper_needed: bool = False
    whisper_output: str | None = None
    ai_analysis: dict | None = None
    error: str | None = None


@app.post("/verify", response_model=VerifyResponse)
async def verify_endpoint(req: VerifyRequest):
    # Validar que sea URL de TikTok
    if not TIKTOK_URL_PATTERN.match(req.url.strip()):
        raise HTTPException(
            status_code=400,
            detail="El link no es de TikTok. Comparte un link válido de TikTok (vt.tiktok.com/... o tiktok.com/@usuario/video/...)."
        )

    result = verify(req.url, manual_text=req.text or "")

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Error desconocido"))

    return VerifyResponse(**result)


@app.get("/health")
async def health():
    return {"status": "ok"}
