"""Excepciones propias del conector Google Docs.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del cliente HTTP subyacente.
"""


class DocsConnectorError(Exception):
    """Error base del conector."""


class DocsAuthError(DocsConnectorError):
    """Credenciales inválidas, refresh token vencido o permisos insuficientes."""


class DocsNetworkError(DocsConnectorError):
    """No se pudo alcanzar la API de Docs (red, timeout, error temporal del servidor)."""


class DocsDataError(DocsConnectorError):
    """La operación es válida pero el recurso no existe o los datos son inválidos."""
