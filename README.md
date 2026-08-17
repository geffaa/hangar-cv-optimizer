---
title: Hangar CV Optimizer
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Hangar Aircraft Positioning & Collision Detection System

Aircraft detection (computer vision), hangar space optimization (search algorithms),
and collision detection for FBO hangar operations — built as a portfolio project
demonstrating the CV + algorithms stack described in Starlight Hangars' job posting.

Full problem breakdown, dataset research, and experiment log: see `docs/`.

## Services

- **`/detect`** — YOLOv8 aircraft detection (mAP50 0.932 on held-out test set). See `docs/experiments/EXPERIMENTS.md`.
- **`/optimize-layout`** — greedy first-fit + simulated annealing placement solver, maximizing hangar utilization.
- **`/check-collision`** — Shapely-based geometric collision/clearance validator, also run automatically on every solver output.

## Architecture

Python (FastAPI) backend does all CV/algorithm work; a separate Blazor Server
(.NET 8) frontend (`frontend/`) consumes it purely as a REST client — no
positioning/collision logic is duplicated across languages. See
`docs/cv-methodology.md` for why YOLOv8 specifically, and
`docs/dataset-research.md` for the dataset comparison behind the CV pipeline.

## Running locally

```bash
uv sync
uv run uvicorn hangar_cv_optimizer.api.main:app --reload
```

Frontend (separate terminal, requires .NET 8 SDK):

```bash
cd frontend
HangarBackend__BaseUrl="http://127.0.0.1:8000" dotnet run
```

## Running via Docker

```bash
docker build -t hangar-cv-optimizer .
docker run -p 7860:7860 hangar-cv-optimizer
```
