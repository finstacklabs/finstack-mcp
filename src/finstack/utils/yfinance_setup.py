"""Centralized yfinance runtime setup for FinStack."""

from __future__ import annotations

import logging
from pathlib import Path

import yfinance as yf

logger = logging.getLogger("finstack.utils.yfinance_setup")

_CONFIGURED = False


def configure_yfinance_cache() -> Path | None:
    """Point yfinance's timezone cache to a writable project-local directory."""
    global _CONFIGURED
    if _CONFIGURED:
        return None

    try:
        project_root = Path(__file__).resolve().parents[3]
        cache_dir = project_root / ".tmp" / "yfinance_tz_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        _CONFIGURED = True
        logger.debug("Configured yfinance timezone cache at %s", cache_dir)
        return cache_dir
    except Exception as exc:  # pragma: no cover - defensive runtime setup
        logger.debug("Unable to configure yfinance cache: %s", exc)
        return None
