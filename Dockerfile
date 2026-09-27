FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies trước để tận dụng triệt để Docker layer cache
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn và metadata gói
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

# Cài đặt package cục bộ
RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/data /app/logs

EXPOSE 8080

CMD ["python", "-m", "my_bot"]
