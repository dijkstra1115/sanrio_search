from __future__ import annotations

import asyncio
import json
import os
import platform
import shlex
from dataclasses import dataclass
from pathlib import Path


IMAGE_SEARCH_TARGET = "getByRole('button', { name: /画像で検索|以圖搜尋|Search by image/i })"
UPLOAD_BUTTON_TARGET = "getByRole('button', { name: /ファイルをアップロード|上傳檔案|Upload a file/i })"


@dataclass(frozen=True)
class LensLookupResult:
    matched_url: str
    matched_host: str
    matched_text: str
    matched_rule: str


def _default_cli_command() -> str:
    if platform.system().lower().startswith("win"):
        return "playwright-cli.cmd"
    return "xvfb-run -a playwright-cli"


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


async def find_preferred_url(
    image_path: Path,
    *,
    session_name: str,
    cli_command: str | None = None,
) -> LensLookupResult:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    cli_command = cli_command or os.getenv("PLAYWRIGHT_CLI_COMMAND", "").strip() or _default_cli_command()
    session_arg = f"-s={session_name}"
    extract_script = (Path(__file__).parent / "scripts" / "extract_preferred_url.js").resolve()

    try:
        await _run_cli(cli_command, session_arg, "open", "https://www.google.com/?hl=ja", "--headed")
        await _run_cli(cli_command, session_arg, "resize", "1440", "1100")
        await _run_cli(cli_command, session_arg, "click", IMAGE_SEARCH_TARGET)
        await _run_cli(cli_command, session_arg, "click", UPLOAD_BUTTON_TARGET)
        await _run_cli(cli_command, session_arg, "upload", str(image_path))
        raw = await _run_cli(cli_command, session_arg, "--raw", "run-code", f"--filename={extract_script}")
        result = _extract_json(raw)
        return LensLookupResult(**result)
    finally:
        try:
            await _run_cli(cli_command, session_arg, "close")
        except Exception:
            pass
