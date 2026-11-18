"""Stderr-only logging for stdio-safe MCP operation (never write to stdout)."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger to stderr with a compact format.

    Safe to call more than once. MCP stdio transport uses stdout for JSON-RPC, so
    application logs must go to stderr only.
    """
    root = logging.getLogger()
    # Replace any existing handlers so a prior library config cannot reattach stdout.
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    # Keep noisy third-party loggers quieter by default.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
