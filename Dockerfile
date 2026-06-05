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

# Copiar backend y compilar whisper.cpp
COPY backend/ ./

# Compilar whisper.cpp
RUN cd whisper && mkdir -p build && cd build && \
    cmake .. && make -j$(nproc) && \
    echo "✅ whisper.cpp compilado"

# Descargar modelo base multilingüe (~142MB, mejor precisión en español)
RUN cd whisper/models && \
    bash download-ggml-model.sh base && \
    echo "✅ Modelo Whisper descargado"

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
