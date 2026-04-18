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

- `PLAYWRIGHT_HEADLESS=true`

If Google Lens starts returning anti-bot pages in headless mode, switch to:

- `PLAYWRIGHT_HEADLESS=false`
- `PLAYWRIGHT_CLI_COMMAND=xvfb-run -a playwright-cli`

Do not use `xvfb-run -a playwright-cli` together with `PLAYWRIGHT_HEADLESS=true`. In headless mode that wrapper can tear down the session between CLI calls.

## Local Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Local Smoke Test

Run the same lookup flow locally before redeploying:

```bash
python -m app.scripts.smoke_lookup --image-path ./messageImage_1776450410880.jpg --json
```

To mimic the Zeabur container locally:

```powershell
./scripts/smoke_zeabur.ps1 -ImagePath .\messageImage_1776450410880.jpg
```

Use `-Headed` only when you explicitly want the Linux container path with `xvfb-run`.

## Deploy

This repo includes a [Dockerfile](./Dockerfile) intended for Zeabur deployment.
