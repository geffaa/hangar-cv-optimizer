---
name: run-hangar-cv-optimizer
description: Build, run, and drive hangar-cv-optimizer (Python/FastAPI CV+optimization backend + Blazor Server .NET 8 frontend). Use when asked to start the app, run its tests, take a screenshot of the Layout Planner or Aircraft Detection pages, or verify an end-to-end change actually works in the browser.
---

Two-process web app: a Python (FastAPI) backend does aircraft detection
(YOLOv8), hangar layout optimization, and collision checking; a separate
Blazor Server (.NET 8) frontend (`frontend/`) consumes it purely as a REST
client. Both must be running. Drive it via
`.claude/skills/run-hangar-cv-optimizer/driver.mjs`, a headless-Chromium
Playwright script — Blazor Server needs a real SignalR/WebSocket circuit
for its interactive buttons, so `curl` alone can't click "Optimize Layout"
or drive a file upload.

All paths below are relative to the repo root (`hangar-cv-optimizer/`).
Verified on macOS (Homebrew); no Linux/container-specific steps were needed.

## Prerequisites

```bash
brew install uv                 # Python package manager for the backend
brew install dotnet-sdk@8       # .NET 8 SDK for the frontend (not on default PATH)
```

`dotnet` is not automatically on `PATH` after this brew install — every
command below that touches the frontend needs:

```bash
export PATH="/opt/homebrew/opt/dotnet@8/bin:$PATH"
```

The driver itself needs Node + Playwright's Chromium, installed once inside
this skill directory (kept local so ESM module resolution finds it
regardless of your current working directory — `NODE_PATH` does **not**
work for ESM imports):

```bash
cd .claude/skills/run-hangar-cv-optimizer
npm init -y && npm install --no-save playwright
npx playwright install chromium
```

## Setup

```bash
uv sync   # backend deps
```

Trained model weights are committed at `models/aircraft_detector.pt` (small,
deliberately tracked - see root `.gitignore`), so `/detect` works without
any training step. No other setup/config required for a local run.

## Run (agent path)

**Backend** (background, port 8811 - 8000 is often already taken by
something else on a dev machine):

```bash
cd hangar-cv-optimizer
nohup uv run uvicorn hangar_cv_optimizer.api.main:app --port 8811 > /tmp/backend.log 2>&1 &
for i in $(seq 1 30); do curl -sf http://127.0.0.1:8811/health >/dev/null && echo up && break; sleep 1; done
```

**Frontend** (background, port 5299):

```bash
export PATH="/opt/homebrew/opt/dotnet@8/bin:$PATH"
cd hangar-cv-optimizer/frontend
HangarBackend__BaseUrl="http://127.0.0.1:8811" \
ASPNETCORE_URLS="http://127.0.0.1:5299" \
ASPNETCORE_ENVIRONMENT=Development \
nohup dotnet run --no-launch-profile > /tmp/frontend.log 2>&1 &
for i in $(seq 1 30); do curl -sf http://127.0.0.1:5299/ >/dev/null && echo up && break; sleep 1; done
```

`ASPNETCORE_ENVIRONMENT=Development` is not optional - see Gotchas.

**Drive it** and get screenshots:

```bash
SAMPLE=$(ls hangar-cv-optimizer/data/yolo/images/test/*.jpg | head -1)  # or any real photo/satellite image
mkdir -p /tmp/shots
node hangar-cv-optimizer/.claude/skills/run-hangar-cv-optimizer/driver.mjs "$SAMPLE" http://127.0.0.1:5299 /tmp/shots
```

Prints `CONSOLE_ERRORS: [...]` (should be `[]`) and writes three
screenshots to `/tmp/shots/`: `01-home.png` (empty Layout Planner),
`02-optimized.png` (after clicking "Optimize Layout" - collision status
badge + placed aircraft rendered as SVG rectangles), `03-detect.png`
(after uploading `$SAMPLE` - green bounding boxes overlaid on the image).
`data/yolo/images/test/*.jpg` only exists after running
`scripts/prepare_yolo_dataset.py`; any other real image file works fine for
a quick check, it just won't have ground-truth aircraft to compare against.

**Stop** (kill by port - `pkill -f` on a process-name pattern is
unreliable here, see Gotchas):

```bash
lsof -ti:5299,8811 | xargs -r kill -9
```

## Run (human path)

Same launch commands as above, then open `http://127.0.0.1:5299` in a real
browser. Layout Planner is the home page; Aircraft Detection is at
`/detect`. Backend's interactive API docs: `http://127.0.0.1:8811/docs`.

## Test

```bash
cd hangar-cv-optimizer
uv run pytest -q       # 28 tests: collision/solver unit + property-based + API integration
```

CV-specific tests skip automatically if `data/` (gitignored dataset) isn't
present locally - not a failure, just reduced coverage.

```bash
export PATH="/opt/homebrew/opt/dotnet@8/bin:$PATH"
cd frontend && dotnet build   # 0 warnings, 0 errors expected
```

## Gotchas

- **Missing `ASPNETCORE_ENVIRONMENT=Development` → unstyled page, no
  crash.** Without it, `dotnet run` serves the app in Production mode,
  which does not dynamically serve the CSS-isolation bundle
  (`HangarDashboard.styles.css`, generated from `*.razor.css` files like
  the sidebar's `MainLayout.razor.css`). The page loads and Bootstrap/
  `app.css` still 200, but the dark sidebar and component-scoped styles
  silently 404 and vanish - no error banner, just wrong-looking output
  that's easy to mistake for "it's running fine." `dotnet publish` (real
  deploys) bundles this file into `wwwroot` physically regardless of
  environment, so this is a `dotnet run`-only trap, not a deploy bug.
- **Locale-dependent decimal separators break SVG rendering.** On a
  machine with a comma-decimal locale (e.g. id-ID), Razor's default
  `@someDouble` interpolation into markup renders `"617,37"` instead of
  `"617.37"` - browsers reject that as an invalid SVG length
  (`<rect>` silently fails to render, `console --errors` shows `Expected
  length` for every affected attribute) and .NET's `HttpClient` query-string
  building does the same to numeric query params (`?confidence_threshold=0,25`
  → FastAPI 422s on every call). Already fixed project-wide via
  `Services/InvariantFormat.cs`'s `.Inv()` extension - if you add a new
  `@someDouble` anywhere in `.razor` markup or a new HTTP query param, use
  `.Inv()`, not bare interpolation, or this regresses silently (it will
  *not* throw a compile error or an obvious runtime exception - the page
  just renders wrong for demo/deploy in certain locales).
- **`pkill -f "dotnet.*HangarDashboard"` unreliably kills the frontend.**
  Observed it leave a stale process holding port 5299, causing the next
  `dotnet run` to crash with `AddressInUseException` while looking like
  a hang. Kill by port instead: `lsof -ti:5299 | xargs -r kill -9`.
- **Playwright + ESM (`import { chromium } from 'playwright'`) ignores
  `NODE_PATH`.** Installing `playwright` in some other directory (e.g. a
  scratch `/tmp` folder) and running `driver.mjs` from elsewhere fails with
  `ERR_MODULE_NOT_FOUND` even with `NODE_PATH` set - Node's ESM resolver
  doesn't consult it (that's a CommonJS-only env var). `node_modules` must
  be a sibling of `driver.mjs`, hence installing playwright directly in
  this skill directory.
- **First `/detect` call is slow (~3-5s).** The YOLO model lazy-loads via
  `functools.lru_cache` on first request, not at server startup - the
  health check passing does not mean detection is warm yet. The driver's
  30s timeout on `wait-for svg image` accounts for this; don't shrink it.
- **Port 8000 is often already taken** by something unrelated on a dev
  machine (observed a stray PHP process). The backend commands above use
  8811; adjust `HangarBackend__BaseUrl` and the driver's frontend-url arg
  together if you pick a different port.

## Troubleshooting

- **`dotnet: command not found`**: `dotnet-sdk@8` installs to
  `/opt/homebrew/opt/dotnet@8/bin`, not a default `PATH` location on
  Homebrew/Apple Silicon. Export the `PATH` line from Prerequisites.
- **`Failed to bind to address http://127.0.0.1:5299: address already in
  use`**: a previous frontend process is still holding the port (see the
  `pkill -f` gotcha above). `lsof -ti:5299 | xargs -r kill -9`, confirm
  with `lsof -ti:5299` (empty output), then relaunch.
- **`driver.mjs` throws `ERR_MODULE_NOT_FOUND: Cannot find package
  'playwright'`**: you're running it with `node_modules` missing next to
  it. Re-run the Prerequisites `npm install` step inside
  `.claude/skills/run-hangar-cv-optimizer/`, not some other directory.
- **`/detect` returns 422 with a query-string decimal error**, or bounding
  boxes silently don't appear despite a 200 response: locale/culture bug
  regression - see the Gotchas entry on `.Inv()`. Check every new
  `@someDouble` in `.razor` markup and every new numeric query param.
