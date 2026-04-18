from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from app.lens_lookup import find_preferred_url


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local smoke test for Google Lens lookup.")
    parser.add_argument("--image-path", required=True, help="Path to the local image file.")
    parser.add_argument("--session-name", help="Optional playwright-cli session name.")
    parser.add_argument("--cli-command", help="Optional override for the playwright-cli command.")
    parser.add_argument("--headed", action="store_true", help="Run the browser in headed mode.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    return parser.parse_args()


async def _main() -> int:
    args = parse_args()
    image_path = Path(args.image_path).expanduser().resolve()
    session_name = args.session_name or f"smoke-{uuid.uuid4().hex[:10]}"

    result = await find_preferred_url(
        image_path,
        session_name=session_name,
        cli_command=args.cli_command,
        headless=not args.headed,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "matched_url": result.matched_url,
                    "matched_host": result.matched_host,
                    "matched_text": result.matched_text,
                    "matched_rule": result.matched_rule,
                    "session_name": session_name,
                    "headless": not args.headed,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(result.matched_url)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
