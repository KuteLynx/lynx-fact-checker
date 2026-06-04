# lynx-fact-checker 🐱

Verificación de contenido de TikTok con IA. Pega un link, el pipeline extrae metadata, clasifica el claim y prepara el texto para análisis por IA.

## Stack

- **Frontend:** Svelte 5 + Vite
- **Backend:** FastAPI + Python
- **Pipeline:** extract-tiktok.py → verificaia-filter.py → OCR condicional

## Inicio rápido

```bash
# Terminal 1 — Backend
cd backend
uv venv && uv pip install -r requirements.txt
uv run uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

O usa `make`:

```bash
make dev-backend   # Terminal 1
make dev-frontend  # Terminal 2
```

Abrir `http://localhost:5173` y pegar un link de TikTok.

## Endpoint

```
POST /verify
Content-Type: application/json

{"url": "https://vt.tiktok.com/..."}
```

Respuesta:

```json
{
  "success": true,
  "extractor": { ... },
  "filter": {
    "decision": "PASA",
    "herramienta": "🤖 IA directo",
    "score_claim": 2,
    "razon": "..."
  },
  "combined_text": "...",
  "whisper_needed": false
}
```

## Pipeline

1. `extract-tiktok.py` extrae metadata del video (autor, stats, descripción, imágenes)
2. `verificaia-filter.py` clasifica el contenido con árbol de decisión (STOP/PASA + herramienta)
3. Si requiere OCR, re-ejecuta extractor con `--ocr`
4. Devuelve JSON combinado listo para IA

## Próximos pasos

- [ ] Integración con IA (OpenAI/Claude/local)
- [ ] Capacitor (Android/iOS)
- [ ] Share sheet de TikTok
- [ ] Whisper para transcripción de audio
