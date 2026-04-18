from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shlex
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

IMAGE_SEARCH_TARGET = "getByRole('button', { name: /画像で検索|Search by image/i })"
UPLOAD_BUTTON_TARGET = "getByRole('button', { name: /ファイルをアップロード|Upload a file/i })"


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
    stdout, stderr = await process.communicate()
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
    raise RuntimeError("playwright-cli did not return JSON output")


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
    fallback_to_headed: bool = False,
) -> LensLookupResult:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        return await _find_preferred_url_once(
            image_path,
            session_name=session_name,
            cli_command=_resolve_cli_command(cli_command, headless=headless),
            headless=headless,
        )
    except GoogleBotBlockedError:
        if not headless or not fallback_to_headed:
            raise

        logger.warning("Headless Google Lens session was blocked; retrying in headed mode")
        return await _find_preferred_url_once(
            image_path,
            session_name=f"{session_name}-headed",
            cli_command=_resolve_cli_command(cli_command, headless=False),
            headless=False,
        )
