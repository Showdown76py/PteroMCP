"""Allow running the server as `python -m pteromcp`."""

from __future__ import annotations

import argparse
import sys

from pteromcp._version import __version__
from pteromcp.server import run_stdio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pteromcp",
        description="Model Context Protocol server for Pterodactyl and Pelican panels.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"pteromcp {__version__}",
    )
    parser.add_argument(
        "transport",
        nargs="?",
        default="stdio",
        choices=["stdio"],
        help="MCP transport to use (only stdio is supported for now).",
    )
    parser.parse_args(argv)
    run_stdio()
    return 0


if __name__ == "__main__":
    sys.exit(main())
