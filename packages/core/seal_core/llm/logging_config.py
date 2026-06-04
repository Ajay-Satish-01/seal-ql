"""Reduce LiteLLM console noise in server logs."""

from __future__ import annotations

import logging

import litellm

_configured = False


def configure_litellm_logging() -> None:
    """Suppress LiteLLM debug banners and lower logger verbosity (idempotent)."""
    global _configured
    if _configured:
        return
    _configured = True

    litellm.set_verbose = False
    litellm.suppress_debug_info = True
    for name in ("LiteLLM", "litellm"):
        logging.getLogger(name).setLevel(logging.WARNING)
