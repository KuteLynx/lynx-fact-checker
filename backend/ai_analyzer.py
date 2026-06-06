"""
ai_analyzer — Análisis LLM del texto extraído de TikTok 🐱
Usa OpenAI-compatible API (DeepSeek, OpenAI, etc.) para analizar
claims factuales en el texto extraído del video.

Uso:
    from ai_analyzer import analyze
    result = analyze("texto del video", {"score_claim": 2, ...})
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Prompt base para el análisis
SYSTEM_PROMPT = """Eres un fact-checker experto. Analiza el texto extraído de un video de TikTok.

Tu tarea:
1. Identifica claims concretos verificables en el texto.
2. Para cada claim, indica si parece verdadero, falso, no verificable o es una opinión.
3. Proporciona una justificación breve.
4. Indica tu nivel de confianza (alta, media, baja).

Responde ÚNICAMENTE con un objeto JSON con esta estructura:
{
  "claims": [
    {
      "claim": "texto del claim identificado",
      "veredicto": "verdadero | falso | no_verificable | opinion",
      "confianza": "alta | media | baja",
      "justificacion": "breve explicación"
    }
  ],
  "resumen": "resumen general del análisis",
  "tiene_claims_verificables": true | false
}

No incluyas texto fuera del JSON."""


def analyze(combined_text: str, filter_data: dict | None = None) -> dict | None:
    """
    Envía el texto combinado a un LLM para análisis de claims.

    Args:
        combined_text: Texto extraído del video (descripción + slides + OCR).
        filter_data: Datos del filtro (score, factores, etc.) para contexto adicional.

    Returns:
        dict con:
          - raw_response: texto crudo de la respuesta del LLM
          - structured: dict parseado con claims, resumen, etc.
          - model: modelo usado
        None si no hay API key configurada o si falla la llamada.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.info("OPENAI_API_KEY no configurada — análisis IA omitido")
        return None

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get("LLM_API_URL", "https://api.deepseek.com/v1"),
        )

        model = os.environ.get("LLM_MODEL", "deepseek-chat")

        # Armar mensaje usuario con contexto del filtro
        contexto = ""
        if filter_data:
            contexto = (
                f"\nContexto del análisis previo:\n"
                f"- Score de claim: {filter_data.get('score_claim', 'N/A')}/4\n"
                f"- Decisión del filtro: {filter_data.get('decision', 'N/A')}\n"
            )

        user_message = (
            f"Analiza el siguiente texto extraído de un TikTok:\n\n"
            f"---\n{combined_text}\n---\n"
            f"{contexto}"
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4096,
            timeout=30,
        )

        raw = resp.choices[0].message.content or ""

        # Intentar parsear como JSON
        structured = None
        try:
            structured = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Respuesta del LLM no es JSON válido: %s", raw[:100])

        return {
            "raw_response": raw,
            "structured": structured,
            "model": model,
        }

    except Exception as e:
        logger.error("Error llamando al LLM: %s", e)
        return None
