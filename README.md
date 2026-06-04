# lynx-fact-checker 🐱

Verificación de contenido de TikTok con IA. Pega un link (o compártelo directo desde TikTok), el pipeline extrae metadata, clasifica el claim y prepara el texto para análisis por IA.

## Stack

- **Frontend:** Svelte 5 + Vite + PWA (Web Share Target)
- **Backend:** FastAPI + Python
- **Pipeline:** extract-tiktok.py → verificaia-filter.py → OCR / Whisper condicional

## Inicio rápido (desarrollo)

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

## Deploy

### Frontend → GitHub Pages

1. Ir a Settings > Pages > Source: **GitHub Actions**
2. Agregar variable de repositorio: `Settings > Secrets and variables > Actions > Variables`
   - `VITE_API_URL` = URL del backend deployado (ej: `https://lynx-fact-checker-api.onrender.com`)
3. Pushear a `master` → el workflow deploya automáticamente el frontend

### Backend → Render

1. Crear cuenta en [render.com](https://render.com)
2. Conectar repositorio
3. Render detecta `render.yaml` automáticamente, o crear Web Service manual:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Agregar variable de entorno `CORS_ORIGINS` con la URL del frontend (ej: `https://tu-usuario.github.io`)

### Share Sheet de TikTok (PWA)

Para que Lynx Fact Checker aparezca en el menú de compartir:
1. La app debe servirse por **HTTPS** (GitHub Pages lo da)
2. Abrir la app en Chrome Android
3. Chrome muestra banner "Instalar Lynx Fact Checker" (por el manifest.json)
4. Una vez instalada como PWA, aparece en el share sheet de TikTok

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
4. Si requiere Whisper, marca `whisper_needed: true` para transcripción de audio
5. Devuelve JSON combinado listo para IA

## Próximos pasos

- [x] Share sheet de TikTok (PWA + Web Share Target)
- [x] Mini tutorial en frontend con cards paso a paso
- [ ] Integración con IA (OpenAI/Claude/local)
- [ ] Whisper para transcripción de audio
- [ ] Capacitor (Android/iOS nativo)
