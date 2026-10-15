"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_DOCS_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_DOCS_"


def _read_timeout(default: int = 30) -> int:
    """Lee REQUEST_TIMEOUT tratando el string vacío como ausente: la
    plataforma envía "" cuando el campo opcional queda en blanco."""
    raw = (os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT") or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"{ENV_PREFIX}REQUEST_TIMEOUT debe ser un número entero de segundos, no {raw!r}."
        ) from None
    if value <= 0:
        raise ValueError(f"{ENV_PREFIX}REQUEST_TIMEOUT debe ser mayor que 0, no {value}.")
    return value


@dataclass(frozen=True)
class DocsConfig:
    """Parámetros de conexión a Google Docs vía OAuth2 (refresh token de usuario).

    Funciona tanto con cuentas de Google personales como con Google
    Workspace: el refresh_token identifica al usuario que autorizó el
    acceso (obtenido una única vez con el flujo OAuth "installed app",
    o mediante el botón "Autorizar con Google" de la plataforma).
    """

    client_id: str
    client_secret: str
    refresh_token: str
    request_timeout: int = 30

    @classmethod
    def from_env(cls) -> "DocsConfig":
        """Construye la configuración desde las variables RUVIC_DOCS_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = DocsConfig.from_env()
            >>> config.client_id
            '1234567890-abc.apps.googleusercontent.com'
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN")
            if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector docs: "
                + ", ".join(missing)
                + ". Configura el conector en Settings -> Conectores."
            )

        return cls(
            client_id=os.environ[f"{ENV_PREFIX}CLIENT_ID"],
            client_secret=os.environ[f"{ENV_PREFIX}CLIENT_SECRET"],
            refresh_token=os.environ[f"{ENV_PREFIX}REFRESH_TOKEN"],
            request_timeout=_read_timeout(),
        )
