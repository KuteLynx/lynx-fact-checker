# Render: Dockerfile para lynx-fact-checker
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    ffmpeg \
    cmake \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar backend completo (excepto whisper/ que se clona aparte)
COPY backend/*.py ./
COPY backend/requirements.txt ./

# Clonar whisper.cpp completo (el gitlink no lleva archivos reales al clonar)
RUN git clone --depth=1 https://github.com/ggml-org/whisper.cpp.git /app/whisper && \
    cd /app/whisper && \
    cmake -B build && \
    cmake --build build -j$(nproc) && \
    echo "✅ whisper.cpp compilado"

# Descargar modelo base multilingüe (~142MB)
RUN cd /app/whisper/models && \
    bash download-ggml-model.sh base && \
    echo "✅ Modelo Whisper descargado"

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
