# sanrio_search

LINE webhook service that accepts image messages, sends them to Google Lens through `playwright-cli`, and replies with a preferred URL.

## Behavior

- Prefer `www.sanrio.co.jp`
- Then prefer other `*.sanrio.co.jp`
- Otherwise return the first visible `.jp` result
- Reply with the matched URL only

## Environment Variables

Use [.env.example](./.env.example) as the reference.

Required:

- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `APP_BASE_URL`

Recommended for Zeabur:

- `PLAYWRIGHT_HEADLESS=false`
- `PLAYWRIGHT_CLI_COMMAND=playwright-cli`

If you want to experiment with lower resource usage later, switch to:

- `PLAYWRIGHT_HEADLESS=true`
- `PLAYWRIGHT_FALLBACK_TO_HEADED=true`

The Docker image now starts a long-lived Xvfb display at container startup, so headed lookups there should use plain `playwright-cli`. Do not wrap each CLI call in `xvfb-run`, because that can tear down the display between `open` and follow-up commands.
For direct Linux or WSL `uvicorn` runs outside the container, leave `PLAYWRIGHT_CLI_COMMAND` unset unless you already have a long-lived X display. In that path the app falls back to `xvfb-run -a playwright-cli` for headed lookups.
The current default is headed mode because Google Lens uploads are currently being redirected to `/sorry/` in headless mode.

## Local Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Local Smoke Test

Run the same lookup flow locally before redeploying:

```bash
python -m app.scripts.smoke_lookup --image-path ./messageImage_1776450410880.jpg --json
```

Use `--headless` only when you explicitly want to test the lower-resource mode.

To mimic the Zeabur container locally:

```powershell
./scripts/smoke_zeabur.ps1 -ImagePath .\messageImage_1776450410880.jpg
```

Use `-Headed` only when you want to force an explicit headed CLI run inside the container.

## Deploy

This repo includes a [Dockerfile](./Dockerfile) intended for Zeabur deployment.
