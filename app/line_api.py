from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

import httpx


LINE_API_BASE = "https://api.line.me"
LINE_CONTENT_BASE = "https://api-data.line.me"


def verify_signature(channel_secret: str, body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def build_headers(channel_access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {channel_access_token}",
        "Content-Type": "application/json",
    }


async def fetch_message_content(
    client: httpx.AsyncClient,
    channel_access_token: str,
    message_id: str,
) -> tuple[bytes, str | None]:
    response = await client.get(
        f"{LINE_CONTENT_BASE}/v2/bot/message/{message_id}/content",
        headers={"Authorization": f"Bearer {channel_access_token}"},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.content, response.headers.get("content-type")


async def reply_text(
    client: httpx.AsyncClient,
    channel_access_token: str,
    reply_token: str,
    text: str,
) -> None:
    payload: dict[str, Any] = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text,
            }
        ],
    }
    response = await client.post(
        f"{LINE_API_BASE}/v2/bot/message/reply",
        headers=build_headers(channel_access_token),
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
