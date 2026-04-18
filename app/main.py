from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.lens_lookup import find_preferred_url
from app.line_api import fetch_message_content, reply_text, verify_signature


logger = logging.getLogger(__name__)

app = FastAPI(title="LINE Google Lens Bot")


def build_instruction_message() -> str:
    return "請直接傳圖片給我，我會先找三麗鷗官網連結，沒有的話回傳第一個 .jp 網域結果。"


@app.on_event("startup")
async def startup() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app.state.settings = settings
    app.state.http = httpx.AsyncClient()
    logger.info("Service started")


@app.on_event("shutdown")
async def shutdown() -> None:
    client: httpx.AsyncClient | None = getattr(app.state, "http", None)

    if client is not None:
        await client.aclose()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    settings: Settings = app.state.settings
    return {
        "status": "ok",
        "webhook": f"{settings.app_base_url}/webhook" if settings.app_base_url else "/webhook",
    }


async def _handle_image_event(event: dict[str, Any]) -> str:
    settings: Settings = app.state.settings
    client: httpx.AsyncClient = app.state.http

    message = event.get("message", {})
    message_id = message.get("id")
    if not message_id:
        raise RuntimeError("Missing LINE message id")

    content_provider = message.get("contentProvider", {})
    if content_provider.get("type") not in (None, "line"):
        raise RuntimeError("Only LINE-hosted image content is supported")

    content, content_type = await fetch_message_content(client, settings.line_channel_access_token, message_id)
    suffix = ".jpg"
    if content_type and "png" in content_type:
        suffix = ".png"
    elif content_type and "webp" in content_type:
        suffix = ".webp"

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        lookup = await find_preferred_url(
            tmp_path,
            session_name=f"line-image-{message_id}",
            cli_command=settings.playwright_cli_command or None,
            headless=settings.playwright_headless,
        )
        logger.info("Matched %s via %s", lookup.matched_url, lookup.matched_rule)
        return lookup.matched_url
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


async def _build_reply_text(event: dict[str, Any]) -> str | None:
    event_type = event.get("type")
    if event_type == "follow":
        return build_instruction_message()

    if event_type != "message":
        return None

    message_type = event.get("message", {}).get("type")
    if message_type == "image":
        try:
            return await _handle_image_event(event)
        except Exception as exc:
            logger.exception("Image lookup failed")
            return f"查找失敗：{exc}"

    return build_instruction_message()


@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str | None = Header(default=None)) -> JSONResponse:
    settings: Settings = app.state.settings
    raw_body = await request.body()

    if not verify_signature(settings.line_channel_secret, raw_body, x_line_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(raw_body.decode("utf-8"))
    events = payload.get("events", [])
    client: httpx.AsyncClient = app.state.http

    for event in events:
        reply_token = event.get("replyToken")
        if not reply_token:
            continue

        text = await _build_reply_text(event)
        if not text:
            continue

        await reply_text(client, settings.line_channel_access_token, reply_token, text[:5000])

    return JSONResponse({"ok": True})
