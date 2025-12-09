FROM python:3.12-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN poetry install --no-root --only main --no-interaction --no-ansi \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY main.py ./
COPY .env.example README.md AGENTS.md ./ 

CMD ["python", "main.py"]
