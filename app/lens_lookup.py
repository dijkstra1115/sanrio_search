from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shlex
import time
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

IMAGE_SEARCH_TARGET = "getByRole('button', { name: /画像で検索|Search by image/i })"
UPLOAD_BUTTON_TARGET = "getByRole('button', { name: /ファイルをアップロード|Upload a file/i })"

# ---------------------------------------------------------------------------
# Exponential back-off state (module-level, survives across requests)
# ---------------------------------------------------------------------------
_consecutive_blocks: int = 0
_last_block_ts: float = 0.0
_BACKOFF_SECONDS = [300, 1800, 7200]  # 5 min, 30 min, 2 hr


def _check_cooldown() -> None:
    """Raise if we are still in a back-off cooldown window."""
    if _consecutive_blocks == 0:
        return
    idx = min(_consecutive_blocks - 1, len(_BACKOFF_SECONDS) - 1)
    cooldown = _BACKOFF_SECONDS[idx]
    elapsed = time.monotonic() - _last_block_ts
    remaining = cooldown - elapsed
    if remaining > 0:
        raise GoogleBotBlockedError(
            f"In cooldown after {_consecutive_blocks} consecutive block(s). "
            f"Retry in {remaining:.0f}s."
        )


def _record_block() -> None:
    global _consecutive_blocks, _last_block_ts
    _consecutive_blocks += 1
    _last_block_ts = time.monotonic()
    idx = min(_consecutive_blocks - 1, len(_BACKOFF_SECONDS) - 1)
    logger.warning(
        "Google blocked lookup (%d consecutive). Cooling down for %ds.",
        _consecutive_blocks,
        _BACKOFF_SECONDS[idx],
    )


def _record_success() -> None:
    global _consecutive_blocks, _last_block_ts
    if _consecutive_blocks > 0:
        logger.info("Lookup succeeded — resetting block counter from %d.", _consecutive_blocks)
    _consecutive_blocks = 0
    _last_block_ts = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LensLookupResult:
    matched_url: str
    matched_host: str
    matched_text: str
    matched_rule: str


class GoogleBotBlockedError(RuntimeError):
    pass


def _default_cli_command() -> str:
    if platform.system().lower().startswith("win"):
        return "playwright-cli.cmd"
    return "playwright-cli"


def _resolve_cli_command(cli_command: str | None, *, headless: bool) -> str:
    command = cli_command or os.getenv("PLAYWRIGHT_CLI_COMMAND", "").strip()
    if not command:
        if platform.system().lower().startswith("win"):
            return _default_cli_command()
        return "playwright-cli" if headless else "xvfb-run -a playwright-cli"

    if not platform.system().lower().startswith("win") and headless:
        parts = shlex.split(command)
        if parts and parts[0] == "xvfb-run":
            return parts[-1]

    return command


def _command_parts(command: str) -> list[str]:
    if platform.system().lower().startswith("win"):
        return [command]
    return shlex.split(command)


async def _run_cli(cli_command: str, *args: str) -> str:
    process = await asyncio.create_subprocess_exec(
        *_command_parts(cli_command),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        process.kill()
        await process.communicate()
        raise
    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")

    if process.returncode != 0:
        message = stderr_text.strip() or stdout_text.strip() or f"playwright-cli failed: {' '.join(args)}"
        raise RuntimeError(message)

    return stdout_text


def _extract_json(text: str) -> dict[str, str]:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("{") or candidate.startswith("["):
            return json.loads(candidate)
    raise RuntimeError(f"playwright-cli did not return JSON output. Raw ({len(text)} chars): {text[:500]}")


def _extract_scalar(text: str) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate.strip("\"'")
    return ""


def _is_google_sorry_url(url: str) -> bool:
    return "google.com/sorry/" in url or "/sorry/index" in url


async def _find_preferred_url_once(
    image_path: Path,
    *,
    session_name: str,
    cli_command: str,
    headless: bool,
) -> LensLookupResult:
    session_arg = f"-s={session_name}"
    extract_script = (Path(__file__).parent / "scripts" / "extract_preferred_url.js").resolve()
    open_args = [session_arg, "open", "https://www.google.com/?hl=ja"]
    if not headless:
        open_args.append("--headed")

    try:
        await _run_cli(cli_command, *open_args)
        await _run_cli(cli_command, session_arg, "resize", "1440", "1100")
        await _run_cli(cli_command, session_arg, "click", IMAGE_SEARCH_TARGET)
        await _run_cli(cli_command, session_arg, "click", UPLOAD_BUTTON_TARGET)
        await _run_cli(cli_command, session_arg, "upload", str(image_path))

        current_url = _extract_scalar(await _run_cli(cli_command, session_arg, "--raw", "eval", "location.href"))
        if _is_google_sorry_url(current_url):
            raise GoogleBotBlockedError(f"Google Lens blocked the session with {current_url}")

        raw = await _run_cli(cli_command, session_arg, "--raw", "run-code", f"--filename={extract_script}")
        result = _extract_json(raw)
        return LensLookupResult(**result)
    finally:
        try:
            await _run_cli(cli_command, session_arg, "close")
        except Exception:
            pass


async def find_preferred_url(
    image_path: Path,
    *,
    session_name: str,
    cli_command: str | None = None,
    headless: bool = False,
) -> LensLookupResult:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    _check_cooldown()

    try:
        result = await _find_preferred_url_once(
            image_path,
            session_name=session_name,
            cli_command=_resolve_cli_command(cli_command, headless=headless),
            headless=headless,
        )
        _record_success()
        return result
    except GoogleBotBlockedError:
        _record_block()
        raise
