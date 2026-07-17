"""Utilidad de configuración (no forma parte de la librería en runtime):
obtiene un refresh_token de Docs vía el flujo OAuth2 "installed app".

Se ejecuta UNA SOLA VEZ, de forma local e interactiva, para autorizar el
conector contra una cuenta de Google (personal o un usuario individual
de Workspace). Abre el navegador, el usuario inicia sesión y concede los
permisos, y el script imprime el refresh_token que se pega en el
formulario de Ruvic (o se usa como RUVIC_DOCS_REFRESH_TOKEN para pruebas
locales).

Requiere:
    pip install google-auth-oauthlib

Uso:
    python get_refresh_token.py --client-id ID --client-secret SECRET

O, si ya tienes el archivo client_secret.json descargado de Google Cloud
Console (tipo "Aplicación de escritorio"):

    python get_refresh_token.py --client-secrets-file client_secret.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/documents"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id", help="OAuth Client ID (tipo Desktop app)")
    parser.add_argument("--client-secret", help="OAuth Client Secret")
    parser.add_argument(
        "--client-secrets-file",
        help="Ruta al client_secret.json descargado de Google Cloud Console "
        "(alternativa a --client-id/--client-secret)",
    )
    args = parser.parse_args()

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "Falta la dependencia google-auth-oauthlib. Instala con:\n"
            "    pip install google-auth-oauthlib",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if args.client_secrets_file:
        secrets_path = Path(args.client_secrets_file)
    elif args.client_id and args.client_secret:
        client_config = {
            "installed": {
                "client_id": args.client_id,
                "client_secret": args.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(client_config, tmp)
        tmp.close()
        secrets_path = Path(tmp.name)
    else:
        parser.error(
            "Debes pasar --client-secrets-file, o --client-id y --client-secret."
        )
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    print("Se abrirá el navegador para iniciar sesión y autorizar el acceso...")
    credentials = flow.run_local_server(port=0)

    print("\n=== Copia estos valores en el formulario de Ruvic ===")
    print(f"client_id     = {credentials.client_id}")
    print(f"client_secret = {credentials.client_secret}")
    print(f"refresh_token = {credentials.refresh_token}")
    print("\nCuenta autorizada por esta sesión: revisa que sea la correcta.")


if __name__ == "__main__":
    main()
