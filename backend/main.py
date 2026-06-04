"""
Lynx Fact Checker — FastAPI Backend 🐱
POST /verify → recibe URL de TikTok, ejecuta pipeline, devuelve JSON combinado.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import verify

app = FastAPI(title="lynx-fact-checker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
