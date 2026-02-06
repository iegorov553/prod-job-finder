FROM python:3.12-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --with dev --no-interaction --no-ansi

COPY src ./src
COPY apps/web ./apps/web
COPY tests ./tests
COPY main.py ./
COPY .env.example README.md ./ 

WORKDIR /app/apps/web
RUN npm install

WORKDIR /app

CMD ["python", "main.py"]
