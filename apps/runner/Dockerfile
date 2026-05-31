FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /runner

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates chromium git nodejs npm \
  && rm -rf /var/lib/apt/lists/*

RUN npm install -g agent-browser@0.27.0

COPY pyproject.toml ./
COPY README.md ./
COPY app ./app

RUN pip install --no-cache-dir .
RUN useradd --create-home --shell /usr/sbin/nologin runner \
  && chown -R runner:runner /runner

USER runner

CMD ["sqlite-service-runner", "run"]
