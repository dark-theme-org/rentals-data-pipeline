FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-cache

COPY . .

ARG TASK_NAME
ENV TASK_NAME=${TASK_NAME}

ENV PYTHONPATH=/app/src

CMD ["python", "scripts/setup_docker.py"]
