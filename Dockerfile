FROM python:3.13-slim

# opencv (an ultralytics dependency) needs these at import time even headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY models ./models
RUN uv sync --frozen --no-dev

ENV HANGAR_CV_MODEL_PATH=/app/models/aircraft_detector.pt
ENV PATH="/app/.venv/bin:$PATH"

# Hugging Face Spaces (Docker SDK) routes traffic to port 7860 by default.
EXPOSE 7860

CMD ["uv", "run", "uvicorn", "hangar_cv_optimizer.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
