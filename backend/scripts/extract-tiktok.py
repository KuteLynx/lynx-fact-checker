#!/usr/bin/env python3
"""
TikTok Fact-Check Extractor 🐱
Toma un link de TikTok, extrae SÓLO los datos relevantes,
y los devuelve como JSON limpio para que una IA analice.

Soporta:
  - Videos normales (descripción + slides de texto)
  - Photo posts (imagePost) — extrae URLs de imágenes
  - Con --ocr: descarga imágenes y extrae texto con EasyOCR

Usage:
  python3 extract-tiktok.py "https://vt.tiktok.com/ZSx3kRf5B/"
  python3 extract-tiktok.py --ocr "https://vt.tiktok.com/ZSx..."
"""

import re
import json
import sys
import subprocess
import os
import argparse
from datetime import datetime


def extract_url_info(url: str) -> dict:
    """
    Extrae username y video ID desde la URL de TikTok.
    Funciona sin depender del HTML renderizado.

    Formatos soportados:
      - https://www.tiktok.com/@username/video/1234567890
      - https://vm.tiktok.com/XXXXXX/
      - https://vt.tiktok.com/XXXXXX/
      - https://m.tiktok.com/v/1234567890
    """
    info = {"url": url}

    # Formato: www.tiktok.com/@username/video/{id}
    m = re.search(r'tiktok\.com/@([^/]+)/video/(\d+)', url)
    if m:
        info["username"] = m.group(1)
        info["video_id"] = m.group(2)
        info["source"] = "tiktok.com"
        return info

    # Formato: m.tiktok.com/v/{id}
    m = re.search(r'm\.tiktok\.com/v/(\d+)', url)
    if m:
        info["video_id"] = m.group(1)
        info["source"] = "m.tiktok.com"
        return info

    # Formato: vm.tiktok.com/{shortcode}
    m = re.search(r'(vm|vt)\.tiktok\.com/([^/\s?]+)', url)
    if m:
        info["shortcode"] = m.group(2)
        info["source"] = f"{m.group(1)}.tiktok.com"
        return info

    info["source"] = "unknown"
    return info


def resolve_url(short_url: str) -> str:
    """Resuelve un shortlink vt.tiktok a la URL real."""
    result = subprocess.run(
        ["curl", "-sI", "-L", short_url],
        capture_output=True, text=True, timeout=15
    )
    locations = re.findall(
        r'^Location:\s*(.+)$', result.stdout, re.MULTILINE | re.IGNORECASE
    )
    if locations:
        final = locations[-1].strip().split('?')[0]
        return final
    return short_url


def download_image(url: str, output_path: str) -> bool:
    """Descarga una imagen desde URL."""
    result = subprocess.run(
        ["curl", "-sL", "-o", output_path, url],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0 and os.path.getsize(output_path) > 0


def image_to_text(path: str, use_easyocr: bool = False) -> str:
    """Extrae texto de una imagen usando Tesseract o EasyOCR."""
    if not use_easyocr:
        # Try Tesseract first (fast)
        try:
            result = subprocess.run(
                ["tesseract", path, "stdout", "-l", "spa+eng"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass  # Tesseract not installed, fall through to EasyOCR

    # Fallback: EasyOCR
    try:
        import easyocr
        reader = easyocr.Reader(["es", "en"], gpu=False)
        results = reader.readtext(path)
        return "\n".join([t[1] for t in results])
    except ImportError:
        return "[OCR no disponible: instalar easyocr o tesseract]"


def fetch_tiktok_data(url: str, ocr: bool = False, ocr_images_dir: str = "/tmp") -> dict:
    """Obtiene los datos relevantes de un video de TikTok.

    Args:
        url: URL del video o photo post
        ocr: Si True, descarga imágenes de photo posts y extrae texto
        ocr_images_dir: Directorio temporal para descargar imágenes

    Returns:
        dict con datos estructurados del post
    """

    # Extraer info básica del URL siempre
    url_info = extract_url_info(url)

    if url_info.get("source") == "unknown":
        return {"error": f"No se pudo interpretar la URL: {url}"}

    # Resolver shortlink si es necesario
    if url_info.get("source") in ("vm.tiktok.com", "vt.tiktok.com"):
        resolved = resolve_url(url)
        if resolved != url:
            url = resolved
            # Re-extraer del URL resuelto para tener username/video_id
            url_info = extract_url_info(url)

    # Intentar extraer datos del HTML (TikTok SSR - puede fallar si no hay SSR)
    result = subprocess.run(
        ["curl", "-sL", "-A",
         "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36",
         url],
        capture_output=True, text=True, timeout=30
    )
    html = result.stdout

    # Extraer JSON desde el script api-data (mobile)
    match = re.search(
        r'<script id="api-data"[^>]*type="application/json">\s*(.*?)\s*</script>',
        html, re.DOTALL
    )
    if not match:
        # Fallback: buscar en el script inline grande (desktop)
        match = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if not match:
            # Sin SSR disponible — devolver datos básicos del URL
            return _build_url_only_output(url_info, url)

        raw = json.loads(match.group(1))
        scope = raw.get("__DEFAULT_SCOPE__", {})
        # Buscar en distintas rutas posibles
        for prefix in ["webapp.video-detail", "video-detail"]:
            if prefix in scope:
                item = scope[prefix].get("itemInfo", {}).get("itemStruct", {})
                if item:
                    break
        else:
            # No se encontró itemStruct
            return _build_url_only_output(url_info, url)
    else:
        # Mobile api-data path
        raw = json.loads(match.group(1))
        item = raw.get("videoDetail", {}).get("itemInfo", {}).get("itemStruct", {})

    if not item:
        # Estructura vacía (TikTok bloqueó SSR)
        return _build_url_only_output(url_info, url)

    # --- Extracción completa desde itemStruct ---
    output = _build_full_output(item, url)

    # OCR para photo posts
    if ocr and output.get("type") == "photo" and output.get("image_urls"):
        output["extracted_text"] = []
        os.makedirs(ocr_images_dir, exist_ok=True)
        for i, img_url in enumerate(output["image_urls"]):
            img_path = os.path.join(ocr_images_dir, f"tiktok_slide_{i}.jpg")
            if download_image(img_url, img_path):
                text = image_to_text(img_path)
                if text and not text.startswith("[OCR no disponible"):
                    output["extracted_text"].append(text)
                try:
                    os.remove(img_path)
                except OSError:
                    pass

    return output


def _build_url_only_output(url_info: dict, original_url: str) -> dict:
    """Construye un output mínimo solo con la info del URL."""
    output = {
        "extraction_limited": True,
        "type": "video",
        "url": original_url,
        "description": "",
        "video": {
            "id": url_info.get("video_id"),
            "duration_sec": None,
            "created": "N/A",
            "location": None,
            "language": None,
            "is_ad": False,
            "is_aigc": False,
            "play_url": "",
            "download_url": "",
        },
        "creator": {
            "username": url_info.get("username"),
            "display_name": url_info.get("username"),
            "bio": "",
            "verified": False,
            "followers": 0,
            "total_videos": 0,
        },
        "text_slides": [],
        "subtitles_available": False,
        "has_subtitle_text": False,
        "subtitle_languages": [],
        "stats": {
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "views": 0,
            "saves": 0,
        },
        "labels": [],
        "sponsored": False,
        "music": {
            "title": None,
            "original": False,
        },
        "imagePost": False,
        "image_count": 0,
        "image_urls": [],
        "note": (
            "TikTok ya no incluye datos del video en el HTML. "
            "El análisis usará solo el URL. "
            "Para mejores resultados, proporciona la descripción o el texto del video manualmente."
        ),
    }
    return output


def _build_full_output(item: dict, url: str) -> dict:
    """Construye output completo desde itemStruct de TikTok."""
    author = item.get("author", {})
    stats = item.get("stats", {})
    auth_stats = item.get("authorStats", {})
    video = item.get("video", {})

    # Timestamp legible
    created_ts = int(item.get("createTime", 0))
    created_date = (
        datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M:%S")
        if created_ts else "N/A"
    )

    # Slides de texto (para videos carrusel)
    slides = []
    for c in item.get("contents", []):
        desc = c.get("desc", "").strip()
        if desc:
            slides.append(desc)

    # Información de subtítulos
    cla = item.get("claInfo", {})
    subtitle_languages = []
    if cla:
        for cap in cla.get("captionInfos", []):
            subtitle_languages.append(cap.get("language", "unknown"))

    # Armar salida estructurada
    output = {
        "extraction_limited": False,
        "type": "video",  # Will be "photo" if imagePost detected below
        "url": url,
        "video": {
            "id": item.get("id"),
            "duration_sec": video.get("duration"),
            "created": created_date,
            "location": item.get("locationCreated"),
            "language": item.get("textLanguage"),
            "is_ad": item.get("isAd", False),
            "is_aigc": item.get("IsAigc", False),
            "play_url": video.get("playAddr", ""),
            "download_url": video.get("downloadAddr", ""),
        },
        "creator": {
            "username": author.get("uniqueId"),
            "display_name": author.get("nickname"),
            "bio": author.get("signature", "").strip(),
            "verified": author.get("verified", False),
            "followers": auth_stats.get("followerCount", 0),
            "total_videos": auth_stats.get("videoCount", 0),
        },
        "description": item.get("desc", "").strip(),
        "text_slides": slides,
        "subtitles_available": len(subtitle_languages) > 0,
        "has_subtitle_text": len(subtitle_languages) > 0,
        "subtitle_languages": subtitle_languages,
        "stats": {
            "likes": stats.get("diggCount", 0),
            "shares": stats.get("shareCount", 0),
            "comments": stats.get("commentCount", 0),
            "views": stats.get("playCount", 0),
            "saves": stats.get("collectCount", 0),
        },
        "labels": item.get("diversificationLabels", []),
        "sponsored": item.get("isAd", False),
        "music": {
            "title": item.get("music", {}).get("title"),
            "original": item.get("music", {}).get("original", False),
        },
    }

    # Image post detection (photo slideshows)
    if "imagePost" in item:
        ip = item["imagePost"]
        images = ip.get("images", [])
        output["type"] = "photo"
        output["imagePost"] = True
        output["image_count"] = len(images)
        output["image_urls"] = [
            img["imageURL"]["urlList"][0]
            for img in images
            if img.get("imageURL", {}).get("urlList")
        ]
    else:
        output["imagePost"] = False
        output["image_count"] = 0
        output["image_urls"] = []

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TikTok Fact-Check Extractor 🐱 — extrae datos limpios de TikTok"
    )
    parser.add_argument("url", help="URL del video o photo post de TikTok")
    parser.add_argument(
        "--ocr", action="store_true",
        help="Descargar imágenes de photo posts y extraer texto con OCR"
    )
    parser.add_argument(
        "--ocr-dir", default="/tmp",
        help="Directorio temporal para imágenes OCR (default: /tmp)"
    )
    args = parser.parse_args()

    data = fetch_tiktok_data(args.url, ocr=args.ocr, ocr_images_dir=args.ocr_dir)

    if "error" in data:
        print(json.dumps({"error": data["error"]}, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    # Print to stdout for piping
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # Stats to stderr
    json_str = json.dumps(data, ensure_ascii=False)
    tokens_approx = len(json_str) // 4
    print(f"\n--- 📊 ~{tokens_approx} tokens (vs ~100K+ raw HTML) ---",
          file=sys.stderr)
