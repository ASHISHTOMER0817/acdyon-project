"""
Process-wide logging setup.

Imported as `app.config.logging` so it does not collide with the stdlib
`logging` module at the top level.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure root logging once.

    Streamlit and Flask both import the app package; without the guard we
    would attach duplicate handlers on every Streamlit rerun.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid stacking handlers if another library already configured logging.
    if not root.handlers:
        root.addHandler(handler)

    # Keep noisy HTTP / browser loggers quieter in the demo.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger after ensuring logging is configured."""
    configure_logging()
    return logging.getLogger(name)
