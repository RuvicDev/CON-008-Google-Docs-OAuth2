"""Conector Ruvic para Google Docs (cuenta personal o Google Workspace)
vía OAuth2 con refresh token."""

from .client import DocsClient
from .config import ENV_PREFIX, DocsConfig
from .exceptions import (
    DocsAuthError,
    DocsConnectorError,
    DocsDataError,
    DocsNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "DocsAuthError",
    "DocsClient",
    "DocsConfig",
    "DocsConnectorError",
    "DocsDataError",
    "DocsNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
