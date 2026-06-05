"""whisper_transcriber: Transcripcion de audio con whisper.cpp
Usa yt-dlp para descargar el audio de TikTok (CDN URLs expiran),
luego whisper.cpp para transcribir localmente.
"""

import subprocess
import os
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Rutas
WHISPER_DIR = Path(__file__).parent / "whisper"
WHISPER_CLI = WHISPER_DIR / "build" / "bin" / "whisper-cli"
MODELS_DIR = WHISPER_DIR / "models"
YT_DLP = Path(__file__).parent / "yt-dlp"  # binario portable

# Modelo base: ~142MB, multilingüe y más preciso en español que tiny
MODEL_NAME = "ggml-base"
MODEL_PATH = MODELS_DIR / f"{MODEL_NAME}.bin"


def descargar_modelo():
    """Descarga el modelo tiny si no existe."""
    if MODEL_PATH.exists():
        return True

    logger.info("Descargando modelo Whisper tiny (~75MB)...")
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Usar el script de descarga de whisper.cpp
    script = WHISPER_DIR / "models" / "download-ggml-model.sh"
    if script.exists():
        result = subprocess.run(
            ["bash", str(script), MODEL_NAME],
            cwd=str(MODELS_DIR),
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            logger.error("Error descargando modelo: %s", result.stderr)
            return False
    else:
        # Fallback: descarga directa desde HuggingFace
        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{MODEL_NAME}.bin"
        result = subprocess.run(
            ["curl", "-sL", "-o", str(MODEL_PATH), url],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0 or not MODEL_PATH.exists():
            return False

    return MODEL_PATH.exists()


def descargar_audio(tiktok_url: str) -> str | None:
    """
    Descarga el audio de un video de TikTok usando yt-dlp + ffmpeg.
    Retorna la ruta al archivo WAV temporal, o None si falla.
    """
    # Crear directorio temporal
    tmp_dir = tempfile.mkdtemp()
    output_template = os.path.join(tmp_dir, "audio.%(ext)s")

    # yt-dlp extrae el audio y lo convierte a WAV 16kHz mono
    result = subprocess.run(
        [str(YT_DLP), "-x", "--audio-format", "wav",
         "--audio-quality", "0",
         "--postprocessor-args", "ffmpeg:-ar 16000 -ac 1",
         "--no-playlist",
         "-o", output_template,
         tiktok_url],
        capture_output=True, text=True, timeout=180
    )

    if result.returncode != 0:
        logger.error("yt-dlp falló: %s", result.stderr[:300])
        return None

    # Buscar el archivo WAV generado
    wav_path = os.path.join(tmp_dir, "audio.wav")
    if os.path.exists(wav_path):
        return wav_path

    # Fallback: buscar cualquier .wav en tmp_dir
    for f in os.listdir(tmp_dir):
        if f.endswith(".wav"):
            return os.path.join(tmp_dir, f)

    logger.error("No se generó archivo WAV en %s", tmp_dir)
    return None


def transcribir(audio_path: str) -> str | None:
    """
    Transcribe un archivo de audio usando whisper.cpp.
    Retorna el texto transcrito o None si falla.
    """
    if not WHISPER_CLI.exists():
        logger.error("whisper-cli no encontrado en %s", WHISPER_CLI)
        return None

    if not MODEL_PATH.exists():
        if not descargar_modelo():
            logger.error("No se pudo descargar el modelo Whisper")
            return None

    result = subprocess.run(
        [str(WHISPER_CLI), "-m", str(MODEL_PATH),
         "-f", audio_path, "-otxt", "--no-timestamps",
         "-l", "es"],  # forzar detección de español
        capture_output=True, text=True, timeout=300
    )

    # La salida va a stdout (el texto transcrito)
    texto = result.stdout.strip()

    if not texto:
        logger.warning("Transcripción vacía para %s", audio_path)
        return None

    return texto


def transcribir_video(tiktok_url: str) -> str | None:
    """
    Pipeline completo: descargar audio → transcribir.
    Retorna el texto transcrito o None.
    """
    audio_path = descargar_audio(tiktok_url)
    if not audio_path:
        logger.error("No se pudo descargar el audio")
        return None

    tmp_dir = os.path.dirname(audio_path)
    try:
        texto = transcribir(audio_path)
        return texto
    finally:
        # Limpiar directorio temporal completo
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except OSError:
            pass


if __name__ == "__main__":
    # Prueba rápida
    import sys
    if len(sys.argv) > 1:
        texto = transcribir_video(sys.argv[1])
        print(texto or "[falló la transcripción]")
    else:
        print("Uso: python3 whisper_transcriber.py <video_url>")
