"""
Lynx Fact Checker — Pipeline orquestador 🐱
Ejecuta extract-tiktok.py via subprocess, pasa el resultado al filtro
(importado con importlib por el guión en el nombre), y ejecuta OCR
condicional si el árbol de decisión lo indica.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

from filter_loader import filtrar
from ai_analyzer import analyze

logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).parent / "scripts"


def _run_extractor(url: str, ocr: bool = False) -> dict:
    """Ejecuta extract-tiktok.py y devuelve el JSON parseado."""
    script = SCRIPTS_DIR / "extract-tiktok.py"
    cmd = [sys.executable, str(script), url]
    if ocr:
        cmd.append("--ocr")

    logger.info("Ejecutando extractor: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        # El error puede venir en stderr o en stdout (según qué falle)
        err = result.stderr.strip() or result.stdout.strip() or "Error desconocido"
        logger.error("Extractor falló (exit %d): %s", result.returncode, err)
        return {"error": f"Extractor falló: {err}"}

    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        return {"error": f"JSON inválido del extractor: {e}"}


def verify(url: str) -> dict:
    """
    Pipeline completo:
    1. Ejecutar extractor → metadata JSON
    2. Pasar metadata al filtro → decisión (STOP/PASA + herramienta)
    3. Si herramienta es OCR, re-ejecutar extractor con --ocr
    4. Si herramienta es Whisper, transcribir audio del video
    5. Combinar texto final (descripción + slides + OCR + Whisper)
    6. Análisis LLM
    7. Devolver JSON completo
    """
    # Paso 1: Extraer metadata
    extractor_data = _run_extractor(url)
    if "error" in extractor_data:
        return {"success": False, "error": extractor_data["error"]}

    # Paso 2: Filtrar
    filter_result = filtrar(extractor_data)

    # Paso 3: OCR condicional
    ocr_texts = []

    if filter_result.get("herramienta") == "👁️ OCR":
        ocr_data = _run_extractor(url, ocr=True)
        if "error" not in ocr_data and "extracted_text" in ocr_data:
            ocr_texts = ocr_data["extracted_text"]

    # Paso 4: Whisper condicional (transcripción de audio)
    whisper_text = ""
    if filter_result.get("herramienta") == "🎤 Whisper":
        if url:
            try:
                from whisper_transcriber import transcribir_video
                whisper_result = transcribir_video(url)
                if whisper_result:
                    whisper_text = whisper_result
            except Exception as e:
                logger.warning("Whisper falló: %s", e)

    # Paso 5: Combinar texto final
    desc = extractor_data.get("description", "") or ""
    slides = extractor_data.get("text_slides", []) or []
    slides_text = "\n".join(slides) if slides else ""
    ocr_block = "\n".join(ocr_texts) if ocr_texts else ""

    parts = [desc, slides_text, ocr_block]
    if whisper_text:
        parts.append(f"[Transcripción del audio]:\n{whisper_text}")

    combined_text = "\n\n".join(p for p in parts if p.strip())

    # Paso 6: Armar respuesta
    response = {
        "success": True,
        "extractor": extractor_data,
        "filter": filter_result,
        "combined_text": combined_text,
    }

    if not whisper_text and filter_result.get("herramienta") == "🎤 Whisper":
        response["whisper_needed"] = True

    if whisper_text:
        response["whisper_output"] = whisper_text

    # Paso 7: Análisis LLM (si hay API key configurada)
    if combined_text.strip():
        response["ai_analysis"] = analyze(combined_text, filter_result)

    return response
