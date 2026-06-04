#!/usr/bin/env python3
"""
VerificaIA — Filtro de Relevancia + Árbol de Decisión 🐱🔍
Recibe el JSON del extractor de TikTok y decide:
  - 🛑 STOP (no verificable)
  - 👁️ OCR (photo post con texto en imágenes)
  - 🎤 Whisper (video sin texto, ≥30s, no entretenimiento)
  - 🤖 IA directo (tiene claim concreto verificable)

Uso:
  python3 extract-tiktok.py "https://vt.tiktok.com/..." | python3 verificaia-filter.py
  python3 verificaia-filter.py --json dato.json
  python3 verificaia-filter.py --url "https://vt.tiktok.com/..."
"""

import json
import sys
import re
import subprocess
import argparse
from pathlib import Path


# ─── Labels de entretenimiento puro → STOP automático ───
LABELS_ENTRETENIMIENTO = {
    "entertainment", "comedy", "music", "dance",
    "celebrity clips & variety show", "mukbangs & tasting",
    "gaming", "random shoot", "others",
    "movies & tv works", "entertainment culture",
    "movies & animation",
}

# ─── Señales de bio que indican creador serio/experto ───
SENALES_BIO = {
    "dr", "phd", "ph.d", "profesor", "professor", "docente",
    "médico", "medico", "doctor", "investigador", "researcher",
    "científico", "cientifico", "scientist", "especialista",
    "abogado", "licenciado", "ingeniero", "engineer",
    "therapist", "terapeuta", "psicólogo", "psicologo",
    "psychologist", "nutritionist", "nutriólogo", "nutriologo",
    "académico", "academico", "academic", "university",
    "universidad", "catedrático", "catedratico",
}

# ─── Términos que hacen que una descripción sea "seria" ───
TEMAS_SERIOS = {
    "salud", "health", "enfermedad", "disease", "síntoma", "symptom",
    "tratamiento", "treatment", "cura", "vaccine", "vacuna",
    "estudio", "study", "research", "investigación",
    "cientifico", "científico", "science", "ciencia",
    "gobierno", "government", "ley", "law", "derecho",
    "economía", "economy", "inflation", "inflación",
    "cambio climático", "climate change", "ambiente", "environment",
    "política", "politics", "presidente", "president",
    "adhd", "dopamine", "depression", "anxiety",
    "neurodivergent", "mental health", "terapia",
    "education", "educación", "aprender", "learn",
}


def extractor_pipe(url: str) -> dict:
    """Ejecuta el extractor y devuelve el JSON."""
    script_path = Path(__file__).parent / "extract-tiktok.py"
    if not script_path.exists():
        # Fallback: buscar en PATH
        script_path = "extract-tiktok.py"

    result = subprocess.run(
        [sys.executable, str(script_path), url],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        return {"error": f"Extractor falló: {result.stderr.strip()}"}

    try:
        # Parsear solo el JSON (los tokens van a stderr)
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        return {"error": f"JSON inválido del extractor: {e}"}


def clasificar_claim(descripcion: str, bio: str, labels: list) -> dict:
    """
    Evalúa si el contenido contiene un claim concreto verificable.
    Retorna score y desglose de factores.
    """
    texto = descripcion.lower()
    bio_lower = bio.lower()
    labels_lower = [l.lower() for l in labels]

    factores = {}

    # 📊 Cuantificable: números, estadísticas, porcentajes
    tiene_numeros = bool(re.search(r'\d+[,.]?\d*%?', texto))
    palabras_cuantitativas = {
        "mil", "millón", "millones", "billón", "billones",
        "porcentaje", "percentage", "promedio", "average",
        "estadística", "statistic", "cifra", "figure",
        "costo", "cost", "precio", "price",
        "cada", "cada año", "per year", "anualmente",
    }
    tiene_palabras_cuantitativas = any(p in texto for p in palabras_cuantitativas)
    factores["cuantificable"] = tiene_numeros or tiene_palabras_cuantitativas

    # 🎯 Atribuible: menciona fuente, persona, organización, estudio
    patrones_atribucion = [
        r'según\s+\w+', r'de acuerdo con', r'according to',
        r'estudio de', r'study by', r'investigación de',
        r'la oms', r'who said', r'la unicef', r'el gobierno',
        r'la nasa', r'la universidad', r'university of',
        r'doctor\s+\w+', r'dr\.?\s+\w+',
        r'organización', r'organization', r'instituto',
        r'dice que', r'afirma que', r'claims that',
        r'según expertos', r'according to experts',
        r'publicado en', r'published in',
    ]
    tiene_atribucion = any(re.search(p, texto) for p in patrones_atribucion)
    # También si el creador tiene bio con señales de autoridad
    bio_autoridad = any(s in bio_lower for s in SENALES_BIO)
    factores["atribuible"] = tiene_atribucion or bio_autoridad

    # ✅ Falsificable: se puede probar como verdadero o falso
    # Señales de opinión/filosofía = NO falsificable
    senales_opinion = {
        "creo que", "i think", "en mi opinión", "in my opinion",
        "debería", "should", "tal vez", "maybe",
        "será que", "se podría", "quizás",
        "filosofía", "philosophy", "moral", "ethics", "ética",
        "dios", "god", "fe", "faith", "espiritual", "spiritual",
    }
    es_opinion = any(s in texto for s in senales_opinion)

    # ─── Señales de afirmación factual ───
    # NOTA: "es" se maneja por separado con word boundary (\bes\b)
    # porque en español aparece como substring de muchas palabras
    # (curiosidades, gatos, atigrados, encantarán, etc.)
    senales_facto = {
        "es que", "esto es", "esto causa",
        "provoca", "causa", "causa que",
        "aumenta", "reduce", "disminuye",
        "previene", "cura", "trata",
        "contiene", "tiene", "está hecho de",
        "demostrado", "probado", "proven",
        "está comprobado", "está demostrado",
        # Señales de contenido informativo/divulgativo
        "datos", "curiosidades", "sabías que",
        "data", "facts", "did you know",
        "fun fact", "fun facts",
        "información", "information",
        "consejos", "tips",
    }
    es_factual = any(s in texto for s in senales_facto)
    # Standalone "es" con word boundary para evitar falsos positivos
    if re.search(r'\bes\b', texto):
        es_factual = True

    factores["falsificable"] = es_factual and not es_opinion

    # 🕐 Contexto Temporal
    patrones_tiempo = [
        r'en \d{4}', r'en el año', r'in \d{4}',
        r'este año', r'this year', r'este mes',
        r'hace \d+', r'\d+ años', r'\d+ days',
        r'\d+ semanas', r'\d+ weeks',
        r'próximo', r'next', r'pasado', r'last',
        r'ayer', r'yesterday', r'hoy', r'today',
        r'durante la pandemia', r'post-pandemic',
        r'202\d', r'203\d',
    ]
    tiene_contexto = any(re.search(p, texto) for p in patrones_tiempo)
    factores["temporal"] = tiene_contexto

    # Score total
    score = sum(1 for v in factores.values() if v)

    return {
        "score": score,
        "max": 4,
        "factores": factores,
        "es_claim_concreto": score >= 2,
    }


def filtrar(data: dict) -> dict:
    """
    Aplica el árbol de decisión de VerificaIA.
    Retorna: {decision, herramienta, razon, score, ...}
    """
    if "error" in data:
        return {"decision": "error", "razon": data["error"]}

    resultado = {
        "url": data.get("url", "desconocida"),
        "creator": data.get("creator", {}).get("username", "desconocido"),
        "type": data.get("type", "video"),
    }

    # ─── Paso 1: Labels de entretenimiento ───
    labels = [l.lower() for l in data.get("labels", [])]
    if any(l in LABELS_ENTRETENIMIENTO for l in labels):
        resultado["decision"] = "STOP"
        resultado["herramienta"] = "🛑 Ninguna"
        resultado["razon"] = f"Label de entretenimiento detectado: {labels}"
        resultado["score_claim"] = 0
        return resultado

    # ─── Paso 2: Detectar tipo de post ───
    es_photo = data.get("type") == "photo"
    descripcion = data.get("description", "")
    text_slides = data.get("text_slides", [])
    bio = data.get("creator", {}).get("bio", "")
    duracion = data.get("video", {}).get("duration_sec", 0)
    subtitulos = data.get("subtitles_available", False)

    # ─── Paso 3: ¿Hay texto barato? ───
    texto_disponible = bool(descripcion.strip()) or bool(text_slides) or subtitulos

    # ─── Paso 4: Clasificar claim ───
    texto_para_analisis = descripcion + " " + " ".join(text_slides)
    claim = clasificar_claim(texto_para_analisis, bio, labels)
    resultado["score_claim"] = claim["score"]
    resultado["factores_claim"] = claim["factores"]

    # ─── Árbol de decisión ───
    if es_photo:
        # Photo post → siempre OCR (no tiene audio)
        resultado["decision"] = "PASA"
        resultado["herramienta"] = "👁️ OCR"
        resultado["razon"] = "Photo post detectado — requiere extracción de texto de imágenes"
        resultado["image_count"] = data.get("image_count", 0)

    elif claim["es_claim_concreto"] and texto_disponible:
        # Tiene claim concreto Y texto disponible → IA directo
        resultado["decision"] = "PASA"
        resultado["herramienta"] = "🤖 IA directo"
        resultado["razon"] = f"Claim concreto detectado (score {claim['score']}/4) con texto disponible"

    elif texto_disponible and not claim["es_claim_concreto"]:
        # Hay texto (descripción) pero el claim es vago
        # Si solo tenemos descripción (sin subtítulos ni slides) y el video es largo,
        # el contenido real está en el audio → Whisper
        tiene_contenido_accesible = bool(text_slides) or subtitulos
        if not tiene_contenido_accesible and duracion >= 30:
            resultado["decision"] = "PASA"
            resultado["herramienta"] = "🎤 Whisper"
            resultado["razon"] = (f"Video de {duracion}s sin subtítulos ni slides de texto — "
                                   "la descripción sugiere contenido informativo "
                                   "pero el contenido real está en el audio, requiere transcripción")
        else:
            resultado["decision"] = "STOP"
            resultado["herramienta"] = "🛑 Ninguna"
            resultado["razon"] = f"Texto disponible pero claim vago (score {claim['score']}/4, mínimo 2)"

    elif not texto_disponible and duracion >= 30:
        # No hay texto pero el video es largo → Whisper
        resultado["decision"] = "PASA"
        resultado["herramienta"] = "🎤 Whisper"
        resultado["razon"] = f"Video sin texto de {duracion}s — requiere transcripción de audio"

    elif not texto_disponible and duracion < 30:
        # Video corto sin texto → STOP (mudo/informativo sin datos)
        resultado["decision"] = "STOP"
        resultado["herramienta"] = "🛑 Ninguna"
        resultado["razon"] = "Video corto sin texto disponible — insuficiente para verificar"

    else:
        resultado["decision"] = "STOP"
        resultado["herramienta"] = "🛑 Ninguna"
        resultado["razon"] = "No pasa ningún criterio del pipeline"

    return resultado


def main():
    parser = argparse.ArgumentParser(
        description="VerificaIA Filtro de Relevancia 🐱 — decide qué herramienta usar"
    )
    parser.add_argument("--json", help="Archivo JSON con datos del extractor")
    parser.add_argument("--url", help="URL de TikTok para extraer y filtrar")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Muestra desglose completo de factores")
    args = parser.parse_args()

    data = None

    if args.url:
        data = extractor_pipe(args.url)
    elif args.json:
        with open(args.json) as f:
            data = json.load(f)
    else:
        # Leer de stdin (pipe)
        try:
            raw = sys.stdin.read().strip()
            if raw:
                data = json.loads(raw)
        except json.JSONDecodeError:
            pass

    if not data:
        print(json.dumps({"error": "No se recibieron datos. Usa --url, --json o pipe."},
                         indent=2, ensure_ascii=False))
        sys.exit(1)

    resultado = filtrar(data)

    if args.verbose and "error" not in resultado:
        # Mostrar datos relevantes + resultado
        print("═══════════════════════════════════════")
        print("🔗 VerificaIA — Resultado del Filtro")
        print("═══════════════════════════════════════")
        print(f"Creador:   @{resultado.get('creator', '?')}")
        print(f"Tipo:      {resultado.get('type', '?')}")
        print(f"Decisión:  {resultado['decision']} → {resultado['herramienta']}")
        print(f"Score:     {resultado['score_claim']}/4")
        if "factores_claim" in resultado:
            print("Factores:")
            for k, v in resultado["factores_claim"].items():
                icono = "✅" if v else "❌"
                print(f"  {icono} {k}")
        print(f"Razón:     {resultado['razon']}")
        print("───────────────────────────────────────")
    else:
        # Salida JSON limpia para pipe
        print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
