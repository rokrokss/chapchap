FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl build-essential gcc libpq-dev && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-root

COPY . ./

EXPOSE 8000

ENV APP_ENV=production
ENV LOG_JSON_FORMAT=false

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "uvicorn_disable_logging.json"]
