# Hangar Aircraft Positioning & Collision Detection System

Aircraft detection (computer vision), hangar space optimization (search
algorithms), and collision detection for FBO hangar operations — a portfolio
project built around the CV + algorithms stack described in Starlight
Hangars' job posting ([starlighthangars.com](https://sttugs.com)).

Full problem breakdown, dataset research, and experiment log live in
[`docs/`](docs/) and [`05-python-cv-hangar-automation/00-project-breakdown.md`](https://github.com/geffaa/Portfolio-Ideas) (SDLC plan this project follows).

## Status

Runs fully locally (backend + frontend both verified end-to-end). **Not yet
deployed to a public URL** — Hugging Face Spaces' free Docker tier now
requires a PRO subscription, and both Azure and Render require payment-method
verification on file even for their free tiers. Rather than add a card for a
portfolio demo, the project is documented here for local reproduction; a
public deploy is a five-minute follow-up once a target platform is settled.

## Services (Python / FastAPI, `src/hangar_cv_optimizer/`)

- **`POST /detect`** — YOLOv8 aircraft detection. mAP50 0.932 on a held-out
  test set (16 images). See [`docs/experiments/EXPERIMENTS.md`](docs/experiments/EXPERIMENTS.md)
  for the v1→v2 experiment log and [`docs/cv-methodology.md`](docs/cv-methodology.md)
  for why YOLOv8 specifically.
- **`POST /optimize-layout`** — greedy first-fit placement + simulated
  annealing over placement order, maximizing hangar utilization subject to
  clearance constraints.
- **`POST /check-collision`** — Shapely-based geometric overlap/clearance
  validator; also run automatically on every solver output, so a client never
  has to trust the solver blindly.

Dataset: [Airbus Aircraft Detection](https://huggingface.co/datasets/jason1966/airbusgeo_airbus-aircrafts-sample-dataset)
(CC BY-NC-SA 4.0), 103 satellite images, 3425 annotated aircraft. Comparison
against 12 other open aircraft-detection datasets, and why this one was kept
as the training basis, is in [`docs/dataset-research.md`](docs/dataset-research.md).

## Architecture

The Python backend does all CV/algorithm work. A separate Blazor Server
(.NET 8) frontend (`frontend/`) consumes it purely as a REST client via
`HttpClient` — no positioning/collision logic is duplicated across languages.
Chosen over Streamlit/React specifically because the job posting names
ASP.NET Core + Blazor.

```
Upload image ──▶ /detect (YOLOv8) ──▶ pixel bounding boxes
Hangar + aircraft list ──▶ /optimize-layout (greedy + simulated annealing)
                                │
                                ▼
                     /check-collision (Shapely) ── validates every layout
                                │
                                ▼
                     Blazor Server UI ── SVG render, red = violation
```

## Running locally

Backend:

```bash
uv sync
uv run uvicorn hangar_cv_optimizer.api.main:app --reload
```

Frontend (separate terminal, requires .NET 8 SDK):

```bash
cd frontend
HangarBackend__BaseUrl="http://127.0.0.1:8000" dotnet run
```

Then open the URL `dotnet run` prints (defaults to `http://127.0.0.1:5000` or
similar) — the Layout Planner and Aircraft Detection pages are both wired to
the local backend.

### Reproducing the trained model

Weights are committed at `models/aircraft_detector.pt` (small, deliberately
tracked — see `.gitignore`) so `/detect` works out of the box. To retrain
from scratch:

```bash
uv run python scripts/prepare_yolo_dataset.py   # download the dataset first, see docs/dataset-research.md
uv run yolo detect train data=data/yolo/data.yaml model=yolov8n.pt imgsz=1280 epochs=80 batch=4 patience=20
```

## Running via Docker

Both services have a `Dockerfile` (backend at repo root, frontend at
`frontend/Dockerfile`) and a `render.yaml` Blueprint for deploying both to
Render in one step, once payment-method verification is set up:

```bash
docker build -t hangar-cv-optimizer .
docker run -p 7860:7860 hangar-cv-optimizer
```

## Tests

```bash
uv run pytest -q
```

28 tests: unit tests for the collision checker and solver, a property-based
test (Hypothesis) verifying the solver's "no overlap" invariant across 200
generated cases, and integration tests against the real FastAPI app. CV tests
skip gracefully if the gitignored dataset/training-run artifacts aren't
present locally.
