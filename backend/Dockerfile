ARG PYTHON_VERSION=3.13.5

FROM python:${PYTHON_VERSION} as builder

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc libpq5 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

COPY . .



FROM  python:${PYTHON_VERSION}-slim as runtime

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libxcb1 \
    libx11-xcb1 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG UID=10001
RUN mkdir -p /home/appuser && \
    adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser && \
    chown -R appuser:appuser /home/appuser

USER appuser

# Copy the venv and the source separately: the multi-GB venv layer stays
# cached across code changes, and the venv is not duplicated into the image.
COPY --chown=appuser:appuser --from=builder /app/.venv ./.venv

ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=appuser:appuser --from=builder /app/src ./src
COPY --chown=appuser:appuser --from=builder /app/config.py ./config.py

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

