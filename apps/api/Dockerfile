FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    API_WORKERS=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations

RUN pip install --no-cache-dir .
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
  && mkdir -p /data \
  && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host ${API_HOST} --port ${API_PORT} --workers ${API_WORKERS}"]
