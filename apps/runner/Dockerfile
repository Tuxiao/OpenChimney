FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /runner

RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY README.md ./
COPY app ./app

RUN pip install --no-cache-dir .
RUN useradd --create-home --shell /usr/sbin/nologin runner \
  && chown -R runner:runner /runner

USER runner

CMD ["sqlite-service-runner", "run"]
