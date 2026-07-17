"""Prueba de conexión estándar del conector docs.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_DOCS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida las credenciales OAuth de Docs (refresca el access token)
    usando las env vars RUVIC_DOCS_*."""
    try:
        from ruvic_docs_connector import (
            DocsAuthError,
            DocsClient,
            DocsDataError,
            DocsNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-docs-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "Docs.git#subdirectory=lib",
        )

    try:
        client = DocsClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except DocsAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except DocsNetworkError as exc:
        return False, f"Error de red: {exc}"
    except DocsDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (True, "Conexión exitosa: credenciales OAuth de Docs válidas")


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
