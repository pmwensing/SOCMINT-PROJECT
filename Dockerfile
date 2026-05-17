FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock ./

RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.lock


FROM python:3.13-slim

ARG SOCMINT_INSTALL_CONNECTORS=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOCMINT_DATA_DIR=/var/lib/socmint

WORKDIR /app

COPY requirements.lock pyproject.toml ./
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.lock \
    && rm -rf /wheels

RUN if [ "$SOCMINT_INSTALL_CONNECTORS" = "true" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends \
        git \
        curl \
        gcc \
        build-essential \
        python3-dev \
        pkg-config \
        cmake \
        libcairo2-dev \
      && python -m pip install --no-cache-dir --upgrade pip wheel setuptools \
      && python -m pip install --no-cache-dir --upgrade \
        maigret \
        sherlock-project \
        socialscan \
        holehe \
        h8mail \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "SOCMINT connector CLI toolchain disabled; build with --build-arg SOCMINT_INSTALL_CONNECTORS=true to enable."; \
    fi

COPY src ./src
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN useradd --system --create-home --home-dir /var/lib/socmint socmint \
    && mkdir -p /var/log/socmint \
    && chown -R socmint:socmint /var/lib/socmint /var/log/socmint /app

USER socmint

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/readyz', timeout=3).read()"

CMD ["gunicorn", "--bind", "127.0.0.1:5000", "src.socmint.wsgi:app"]
