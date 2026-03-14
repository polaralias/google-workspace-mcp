FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && pip install --no-cache-dir uv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md fastmcp.json server.py ./
COPY tool_manifest_google.json ./
COPY tool_manifest_google_admin_calendar_chat_docs.json ./
COPY tool_manifest_google_drive_gmail.json ./
COPY tool_manifest_google_keep_people_forms_meet.json ./
COPY tool_manifest_google_keep_unofficial.json ./
COPY tool_manifest_google_sheets_slides_tasks.json ./
COPY scripts ./scripts

RUN uv sync --no-dev

EXPOSE 3002

CMD ["/app/.venv/bin/python", "scripts/run_server.py", "serve"]
