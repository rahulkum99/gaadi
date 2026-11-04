FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    DEEPFACE_HOME=/opt/deepface

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        curl \
        libxcb1 \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

#
COPY . .

RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/staticfiles && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["sh", "/app/entrypoint.sh"]