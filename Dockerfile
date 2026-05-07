FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOCMINT_DATA_DIR=/var/lib/socmint

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --system --create-home --home-dir /var/lib/socmint socmint \
    && chown -R socmint:socmint /var/lib/socmint /app

USER socmint

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=3).read()"

CMD ["gunicorn", "--bind", "127.0.0.1:5000", "src.socmint.wsgi:app"]
