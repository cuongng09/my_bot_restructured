FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Cài đặt các gói hệ thống cần thiết (Tesseract OCR, FFmpeg cho audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python package và dependencies
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

RUN mkdir -p /app/data /app/logs /app/fonts /app/voices

EXPOSE 8080

CMD ["python", "-m", "main"]

