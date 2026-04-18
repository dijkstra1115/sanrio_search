# Repository Guidelines

## Project Structure & Module Organization
`app/` contains the service code. Use `app/main.py` for FastAPI routes and webhook flow, `app/lens_lookup.py` for Google Lens automation, `app/line_api.py` for LINE Messaging API calls, and `app/config.py` for environment-driven settings. Helper scripts live in `app/scripts/`. Operational scripts such as containerized smoke tests live in `scripts/`. Root-level sample images and debug screenshots are for local verification only; keep new generated artifacts out of commits unless they document a reproducible issue.

## Build, Test, and Development Commands
Install dependencies with `pip install -r requirements.txt`.
Run the API locally with `uvicorn app.main:app --host 0.0.0.0 --port 8080`.
Run the primary smoke test with `python -m app.scripts.smoke_lookup --image-path .\messageImage_1776450410880.jpg --json`.
Use `.\scripts\smoke_zeabur.ps1 -ImagePath .\messageImage_1776450410880.jpg` to validate the Dockerized Zeabur path.
Build the deployment image with `docker build -t sanrio-search-local .`.

## Coding Style & Naming Conventions
Follow existing Python conventions: 4-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and explicit type hints on public functions. Keep modules focused: webhook concerns in `main.py`, external API glue in `line_api.py`, and browser automation in `lens_lookup.py`. Prefer small, reversible changes and keep environment variable names uppercase, matching `.env.example`.

## Testing Guidelines
There is no committed `tests/` suite yet, so smoke testing is the current baseline. Run at least the local smoke lookup before opening a PR, and use the Docker smoke script for changes that affect Playwright, Linux runtime behavior, or deployment settings. If you add automated tests, place them under a new `tests/` package and name files `test_*.py`. Mock LINE and Google interactions where possible; do not make external network calls a hard requirement for unit tests.

## Commit & Pull Request Guidelines
Recent commits use short, imperative subjects such as `Add local smoke test scripts` and `Fix headless session command selection`. Follow that pattern and keep each commit scoped to one change. PRs should explain the behavior change, list the commands you ran, and note any environment or deployment implications. Include screenshots only when UI or browser-automation behavior changed in a way logs cannot explain.

## Security & Configuration Tips
Never commit live LINE credentials or copied `.env` files. Use `.env.example` as the source of truth for required settings. When changing Playwright execution mode, document whether the change was verified in headed mode, headless mode, or both.
