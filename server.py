"""Entry point for the multi-threaded HTTP server.

This module currently parses CLI arguments and prepares the environment.
It does not yet start the actual HTTP server; that will be implemented next.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="server.py",
        description=(
            "Multi-threaded HTTP server (skeleton). Provide optional positional "
            "arguments in the order: port host thread_pool_size."
        ),
        epilog=(
            "Examples:\n"
            "  python server.py\n"
            "  python server.py 9090\n"
            "  python server.py 9090 0.0.0.0\n"
            "  python server.py 9090 0.0.0.0 32\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=8080,
        help="TCP port to bind (default: 8080)",
    )
    parser.add_argument(
        "host",
        nargs="?",
        default="127.0.0.1",
        help="Host/IP address to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "thread_pool_size",
        nargs="?",
        type=int,
        default=10,
        help="Number of worker threads for handling requests (default: 10)",
    )

    return parser.parse_args(argv)


def ensure_directories() -> Path:
    resources_dir = Path("resources")
    uploads_dir = resources_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Basic, friendly logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("server")

    uploads_dir = ensure_directories()

    # Print parsed args for visibility as requested
    print(
        f"Parsed args: port={args.port}, host={args.host}, "
        f"thread_pool_size={args.thread_pool_size}"
    )

    # Startup log line
    logger.info(
        "Starting server on %s:%s with %s threads (uploads dir: %s)",
        args.host,
        args.port,
        args.thread_pool_size,
        uploads_dir,
    )

    # TODO: Initialize socket, thread pool, and accept loop here
    return 0


if __name__ == "__main__":
    raise SystemExit(main())