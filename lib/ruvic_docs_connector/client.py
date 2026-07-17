"""Cliente de Google Docs (cuenta personal o Google Workspace) vía OAuth2
con refresh token de usuario.

Capacidades:
- read_document():   leer el título y el texto completo de un documento.
- create_document():  crear un documento nuevo (con texto inicial opcional).
- append_text():      agregar texto al final de un documento.
- replace_text():     buscar y reemplazar texto en todo el documento.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_DOCS_*
(ver config.DocsConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import socket
from typing import Any

from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import DocsConfig
from .exceptions import (
    DocsAuthError,
    DocsConnectorError,
    DocsDataError,
    DocsNetworkError,
)
from .logging_utils import get_logger

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_SCOPES = ["https://www.googleapis.com/auth/documents"]


def _service_disabled_info(exc: HttpError) -> tuple[str, str] | None:
    """Detecta el caso 403 SERVICE_DISABLED (la API no está habilitada en
    el proyecto de Google Cloud) y retorna (nombre de la API, URL de
    activación), o None si el error es de otro tipo."""
    try:
        details = exc.error_details or []
    except Exception:
        details = []
    for detail in details:
        if isinstance(detail, dict) and detail.get("reason") == "SERVICE_DISABLED":
            meta = detail.get("metadata", {})
            return (
                meta.get("serviceTitle", "API de Google"),
                meta.get(
                    "activationUrl",
                    "Google Cloud Console -> APIs y servicios -> Biblioteca",
                ),
            )
    return None


def _wrap_http_error(exc: HttpError) -> DocsConnectorError:
    """Traduce un error HTTP de la API de Docs a una excepción propia,
    sin dejar escapar nunca el tipo crudo del cliente HTTP."""
    status = exc.resp.status if getattr(exc, "resp", None) is not None else None
    if status == 403:
        disabled = _service_disabled_info(exc)
        if disabled is not None:
            service_title, activation_url = disabled
            return DocsAuthError(
                f"La {service_title} no está habilitada en el proyecto de "
                f"Google Cloud del Client ID configurado. Habilítala en "
                f"{activation_url} y espera 1-2 minutos antes de reintentar."
            )
    if status in (401, 403):
        return DocsAuthError(
            "Credenciales inválidas o sin permiso suficiente sobre este "
            "documento. Verifica que el refresh token no esté revocado o "
            "vencido, que se haya autorizado con el scope de Docs, y que la "
            "cuenta autenticada tenga acceso al documento (compartido con "
            "ella si es de otro usuario)."
        )
    if status == 404:
        return DocsDataError(
            "El documento solicitado no existe, o la cuenta autenticada no "
            "tiene acceso a él."
        )
    if status == 429 or (status is not None and status >= 500):
        return DocsNetworkError(
            f"Docs API no respondió correctamente (HTTP {status}). "
            "Puede ser un límite de cuota temporal; reintenta en unos segundos."
        )
    return DocsDataError(f"Error de Docs API (HTTP {status}): {exc}")


def _validate_document_id(document_id: str) -> str:
    document_id = document_id.strip()
    if not document_id:
        raise DocsDataError("document_id no puede estar vacío.")
    return document_id


def _extract_text(content: list[dict[str, Any]]) -> str:
    """Recorre los elementos estructurales de un documento y concatena el
    texto de párrafos y tablas, en orden."""
    parts: list[str] = []
    for element in content:
        if "paragraph" in element:
            for pe in element["paragraph"].get("elements", []):
                text = pe.get("textRun", {}).get("content")
                if text:
                    parts.append(text)
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    parts.append(_extract_text(cell.get("content", [])))
        elif "tableOfContents" in element:
            parts.append(_extract_text(element["tableOfContents"].get("content", [])))
    return "".join(parts)


class DocsClient:
    """Cliente de Google Docs para leer y editar documentos vía OAuth2
    (refresh token).

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_DOCS_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = DocsClient()           # lee RUVIC_DOCS_* del entorno
        >>> client.read_document("1AbC...xyz")
        {'id': '1AbC...xyz', 'title': 'Acta de reunión', 'body_text': '...'}
    """

    def __init__(self, config: DocsConfig | None = None) -> None:
        self.config = config or DocsConfig.from_env()
        self._logger = get_logger()
        self._service: Any = None
        self._credentials: Credentials | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_credentials(self) -> Credentials:
        if self._credentials is None:
            self._credentials = Credentials(
                token=None,
                refresh_token=self.config.refresh_token,
                token_uri=_TOKEN_URI,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                scopes=_SCOPES,
            )
        return self._credentials

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        credentials = self._get_credentials()
        try:
            self._service = build(
                "docs",
                "v1",
                credentials=credentials,
                cache_discovery=False,
                static_discovery=False,
            )
        except (GoogleAuthError, OSError) as exc:
            raise DocsNetworkError(
                f"No se pudo inicializar el cliente de Docs: {exc}"
            ) from exc
        return self._service

    def ping(self) -> bool:
        """Verifica que las credenciales OAuth sean válidas refrescando el
        token de acceso (no requiere un documento específico).

        Returns:
            True si las credenciales funcionan.

        Raises:
            DocsAuthError / DocsNetworkError según el fallo.
        """
        credentials = self._get_credentials()
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise DocsAuthError(
                "No se pudo autenticar: el refresh token puede estar revocado, "
                "vencido, o el client_id/client_secret no corresponden al mismo "
                "cliente OAuth con el que se generó. Vuelve a autorizar el "
                "conector para obtener un refresh token nuevo."
            ) from exc
        except (socket.error, TimeoutError, OSError) as exc:
            raise DocsNetworkError(f"No se pudo conectar con Google OAuth: {exc}") from exc
        self._logger.info("Ping exitoso: credenciales OAuth válidas.")
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1 — Leer un documento
    # ------------------------------------------------------------------ #

    def read_document(self, document_id: str) -> dict[str, Any]:
        """Lee el título y el texto completo de un documento.

        Args:
            document_id: ID del documento (de la URL:
                docs.google.com/document/d/{document_id}/edit).

        Returns:
            Dict con: id, title, body_text (texto plano, incluye el
            contenido de tablas en orden de aparición).

        Ejemplo:
            >>> client.read_document("1AbC...xyz")
            {'id': '1AbC...xyz', 'title': 'Acta de reunión', 'body_text': '...'}
        """
        document_id = _validate_document_id(document_id)
        service = self._get_service()
        try:
            doc = service.documents().get(documentId=document_id).execute(num_retries=1)
        except HttpError as exc:
            raise _wrap_http_error(exc) from exc
        body_text = _extract_text(doc.get("body", {}).get("content", []))
        self._logger.info(
            "Leído documento %s (%d caracteres)", document_id, len(body_text)
        )
        return {
            "id": doc.get("documentId"),
            "title": doc.get("title", ""),
            "body_text": body_text,
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2 — Crear un documento nuevo
    # ------------------------------------------------------------------ #

    def create_document(self, title: str, body_text: str | None = None) -> dict[str, Any]:
        """Crea un documento nuevo en el Drive de la cuenta autenticada.

        Args:
            title: título del documento.
            body_text: texto inicial del cuerpo (opcional).

        Returns:
            Dict con: id, title, url del documento creado.

        Ejemplo:
            >>> client.create_document("Acta de reunión", "Asistentes: ...")
            {'id': '1AbC...xyz', 'title': 'Acta de reunión', 'url': 'https://docs.google.com/document/d/1AbC...xyz/edit'}
        """
        title = title.strip()
        if not title:
            raise DocsDataError("title no puede estar vacío.")
        service = self._get_service()
        try:
            doc = service.documents().create(body={"title": title}).execute(num_retries=1)
        except HttpError as exc:
            raise _wrap_http_error(exc) from exc
        document_id = doc["documentId"]
        if body_text:
            try:
                service.documents().batchUpdate(
                    documentId=document_id,
                    body={
                        "requests": [
                            {
                                "insertText": {
                                    "endOfSegmentLocation": {},
                                    "text": body_text,
                                }
                            }
                        ]
                    },
                ).execute(num_retries=1)
            except HttpError as exc:
                raise _wrap_http_error(exc) from exc
        self._logger.info("Documento '%s' creado (id=%s)", title, document_id)
        return {
            "id": document_id,
            "title": doc.get("title", title),
            "url": f"https://docs.google.com/document/d/{document_id}/edit",
        }

    # ------------------------------------------------------------------ #
    # Capacidad 3 — Agregar texto al final
    # ------------------------------------------------------------------ #

    def append_text(self, document_id: str, text: str) -> dict[str, Any]:
        """Agrega texto al final del cuerpo del documento.

        Args:
            document_id: ID del documento.
            text: texto a agregar (usa "\\n" para saltos de párrafo).

        Returns:
            Dict con: id, appended_chars.

        Ejemplo:
            >>> client.append_text("1AbC...xyz", "\\nNuevo párrafo al final.")
            {'id': '1AbC...xyz', 'appended_chars': 25}
        """
        document_id = _validate_document_id(document_id)
        if not text:
            raise DocsDataError("text no puede estar vacío.")
        service = self._get_service()
        try:
            service.documents().batchUpdate(
                documentId=document_id,
                body={
                    "requests": [
                        {"insertText": {"endOfSegmentLocation": {}, "text": text}}
                    ]
                },
            ).execute(num_retries=1)
        except HttpError as exc:
            raise _wrap_http_error(exc) from exc
        self._logger.info(
            "Agregados %d caracteres al documento %s", len(text), document_id
        )
        return {"id": document_id, "appended_chars": len(text)}

    # ------------------------------------------------------------------ #
    # Capacidad 4 — Buscar y reemplazar texto
    # ------------------------------------------------------------------ #

    def replace_text(
        self,
        document_id: str,
        find: str,
        replace: str,
        match_case: bool = True,
    ) -> dict[str, Any]:
        """Reemplaza todas las ocurrencias de un texto en el documento.

        Args:
            document_id: ID del documento.
            find: texto a buscar (literal, no expresión regular).
            replace: texto de reemplazo.
            match_case: si distingue mayúsculas/minúsculas (default True).

        Returns:
            Dict con: id, occurrences_changed.

        Ejemplo:
            >>> client.replace_text("1AbC...xyz", "{{CLIENTE}}", "ACME S.A.")
            {'id': '1AbC...xyz', 'occurrences_changed': 3}
        """
        document_id = _validate_document_id(document_id)
        if not find:
            raise DocsDataError("find no puede estar vacío.")
        service = self._get_service()
        try:
            result = service.documents().batchUpdate(
                documentId=document_id,
                body={
                    "requests": [
                        {
                            "replaceAllText": {
                                "containsText": {"text": find, "matchCase": match_case},
                                "replaceText": replace,
                            }
                        }
                    ]
                },
            ).execute(num_retries=1)
        except HttpError as exc:
            raise _wrap_http_error(exc) from exc
        replies = result.get("replies", [{}])
        occurrences = replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0)
        self._logger.info(
            "Reemplazadas %d ocurrencias de %r en %s", occurrences, find, document_id
        )
        return {"id": document_id, "occurrences_changed": occurrences}
