from __future__ import annotations

import os
from dataclasses import dataclass


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value.strip())


@dataclass(frozen=True)
class Settings:
    line_channel_secret: str
    line_channel_access_token: str
    app_base_url: str
    log_level: str
    lookup_timeout_seconds: float
    playwright_cli_command: str
    playwright_headless: bool
    playwright_fallback_to_headed: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            line_channel_secret=_require_env("LINE_CHANNEL_SECRET"),
            line_channel_access_token=_require_env("LINE_CHANNEL_ACCESS_TOKEN"),
            app_base_url=os.getenv("APP_BASE_URL", "").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            lookup_timeout_seconds=_env_float("LOOKUP_TIMEOUT_SECONDS", default=45.0),
            playwright_cli_command=os.getenv("PLAYWRIGHT_CLI_COMMAND", "").strip(),
            playwright_headless=_env_flag("PLAYWRIGHT_HEADLESS", default=False),
            playwright_fallback_to_headed=_env_flag("PLAYWRIGHT_FALLBACK_TO_HEADED", default=False),
        )
