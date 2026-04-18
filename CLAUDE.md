# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**sanrio_search** — a LINE webhook bot that receives image messages, runs them through Google Lens via `playwright-cli`, and replies with the best matching URL. Matching priority: `www.sanrio.co.jp` > `*.sanrio.co.jp` > any `.jp` domain.

Deployed on Windows + ngrok. A Dockerfile exists but is not actively used (Google Lens blocks headless/container environments).

## Commands

```bash
# Install
pip install -r requirements.txt
npm install -g @playwright/cli@latest

# Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8080

# One-click startup (ngrok + uvicorn)
# Double-click start.bat

# Local smoke test (the primary way to verify changes)
python -m app.scripts.smoke_lookup --image-path ./messageImage_1776450410880.jpg --json
```

No test suite exists yet; smoke tests are the verification baseline.

## Architecture

The app is a small FastAPI service with four modules:

- **`app/main.py`** — FastAPI app, LINE webhook handler. Receives image messages, downloads them, calls `find_preferred_url`, replies with the matched URL. Enforces one-at-a-time lookup via `lookup_in_progress` + asyncio lock.
- **`app/lens_lookup.py`** — Orchestrates Google Lens lookups by shelling out to `playwright-cli` (open, click, upload, extract). Includes Google bot-block detection with exponential backoff cooldown.
- **`app/line_api.py`** — LINE Messaging API client: signature verification, content download, reply.
- **`app/config.py`** — `Settings` dataclass loaded from environment variables.

The URL extraction logic lives in **`app/scripts/extract_preferred_url.js`** — a Playwright page function that scrapes visible links from Google Lens results and applies the sanrio preference rules.

**`start.bat`** / **`scripts/start.ps1`** — one-click startup: loads `.env`, starts ngrok tunnel, runs uvicorn.

## Key Design Decisions

- **Headed mode is the default** because Google Lens detects and blocks headless browsers (redirects to `/sorry/`).
- **One lookup at a time** — concurrent lookups are rejected with a "busy" message to prevent memory exhaustion.
- **Temp files in `.tmp/`** — playwright-cli sandboxes file access to the project directory, so temp images are saved to `.tmp/` instead of the system temp directory.
- **Exponential backoff** — consecutive Google blocks trigger cooldown (5 min → 30 min → 2 hr) to avoid hammering.

## Environment Variables

See `.env.example`. Required: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `APP_BASE_URL`.

## Commit Style

Short imperative subjects (e.g., "Fix headless session command selection"). One logical change per commit.
