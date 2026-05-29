FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY gunicorn.conf.py ./
COPY scripts ./scripts
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8080

CMD ["./scripts/entrypoint.sh"]
