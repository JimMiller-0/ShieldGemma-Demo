FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/model_service

ENV PYTHONPATH=/app
ENV MODEL_DIR=/app/models

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/v1/health')"

CMD ["uvicorn", "model_service.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
