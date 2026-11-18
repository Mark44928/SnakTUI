"""Serve the real SnakTUI Textual application in a browser with textual-serve."""

from __future__ import annotations

import argparse
import os
import shlex
import sys
from collections.abc import Sequence


def build_command() -> str:
    """Command textual-serve launches for each browser session."""

    return f"{shlex.quote(sys.executable)} -m snaktui"


def default_port() -> int:
    raw = os.environ.get("PORT", "").strip()
    if not raw:
        return 8000
    try:
        port = int(raw)
    except ValueError:
        return 8000
    return port if 0 < port < 65536 else 8000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snaktui-web",
        description="Serve SnakTUI as the actual Textual app in a browser.",
    )
    parser.add_argument("--host", default=os.environ.get("SNAKTUI_WEB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=default_port())
    parser.add_argument("--title", default="SnakTUI")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        from textual_serve.server import Server
    except ImportError:
        print(
            'SnakTUI web requires textual-serve. Install with: pip install "snaktui[web]"',
            file=sys.stderr,
        )
        return 1
    server = Server(
        build_command(),
        host=args.host,
        port=args.port,
        title=args.title,
    )
    server.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
