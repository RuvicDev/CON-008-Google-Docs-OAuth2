# Conector Google Docs (CON-008)

Conector Ruvic para Google Docs (cuenta personal o Google Workspace).
Permite leer el texto completo de un documento, crear documentos nuevos,
agregar texto al final y buscar/reemplazar texto (ideal para llenar
plantillas), usando OAuth2 con un refresh token obtenido una única vez
durante la configuración.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Docs.git#subdirectory=lib
```

Python 3.10+. Dependencias: `google-auth` y `google-api-python-client`.

## Obtener credenciales

El formulario del conector ofrece 3 formas de autorizar (mismo patrón que los conectores `gmail`, `sheets` y `drive_oauth`):

### Opción recomendada: "Autorizar con Google"

Guarda la instancia y pulsa **Autorizar** — usa la app OAuth propia de la plataforma Ruvic, no requiere que tú crees nada en Google Cloud Console.

### Opción "Usar credenciales propias" o pruebas locales

Si ya configuraste otro conector de Google (Gmail, Sheets, Drive) para
esta misma cuenta, puedes **reutilizar el mismo proyecto, pantalla de
consentimiento y cliente OAuth** — solo falta habilitar la Docs API.

1. Crea (o reutiliza) un proyecto en [Google Cloud Console](https://console.cloud.google.com/).
2. Habilita la **Google Docs API** (buscar "Google Docs API" → Habilitar).
3. Configura la pantalla de consentimiento OAuth si no existe ya, con tu correo en "Usuarios de prueba".
4. Crea (o reutiliza) un cliente OAuth:
   - Para "Usar credenciales propias" en Ruvic: tipo **Aplicación web**, con URI de redirección `{WEB_URL}/api/v1/connectors/oauth/callback`.
   - Para pruebas locales con `get_refresh_token.py`: tipo **Aplicación de escritorio**.
5. Copia el **Client ID** y **Client Secret**.

Para pruebas locales, obtén el refresh token una sola vez:

```bash
pip install google-auth-oauthlib
python get_refresh_token.py --client-id TU_CLIENT_ID --client-secret TU_CLIENT_SECRET
```

> **Importante:** mientras la app de OAuth esté en estado "Testing" en
> Google Cloud, el refresh token puede expirar a los 7 días de
> inactividad. Para uso productivo continuo, publica la app o usa el
> modo "Autorizar con Google".

## Variables de entorno (`RUVIC_DOCS_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_DOCS_CLIENT_ID` | Sí | Client ID del cliente OAuth |
| `RUVIC_DOCS_CLIENT_SECRET` | Sí | Client Secret del mismo cliente OAuth |
| `RUVIC_DOCS_REFRESH_TOKEN` | Sí | Refresh token obtenido al autorizar |
| `RUVIC_DOCS_REQUEST_TIMEOUT` | No (default `30`) | Timeout de solicitud en segundos |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_DOCS_CLIENT_ID=xxxxx.apps.googleusercontent.com
export RUVIC_DOCS_CLIENT_SECRET=xxxxx
export RUVIC_DOCS_REFRESH_TOKEN=xxxxx

python test_connection.py
python validate_local.py
```

`validate_local.py` no necesita ningún documento previo: crea uno nuevo
en el Drive de la cuenta autorizada, le agrega texto, reemplaza un
marcador de plantilla y lo vuelve a leer completo.

Prueba también los casos de error (refresh token revocado, documento
inexistente o no compartido con la cuenta) y verifica que los mensajes
sean claros.

## Notas de integración

- **OAuth2 de usuario**: mismo flujo que los conectores Gmail/Sheets/
  Drive-OAuth — 3 modos de autorización en el manifest que resuelven a
  las mismas 3 env vars.
- **Alcance mínimo**: solo `https://www.googleapis.com/auth/documents`
  (lectura y edición de documentos accesibles por la cuenta). No accede
  a otros archivos de Drive ni puede listar documentos por sí solo — el
  `document_id` lo debe aportar el usuario (de la URL del documento).
- **Detección de API deshabilitada**: si la Docs API no está habilitada
  en el proyecto de Cloud, el error indica la API exacta y el enlace
  directo de activación (caso `SERVICE_DISABLED`).
- **`ping()`/`test_connection()`** no requieren un documento específico:
  solo verifican que el refresh token sea válido refrescando el access
  token directamente contra Google OAuth.
- Los errores HTTP 401/403 de la API se clasifican como `DocsAuthError`;
  404 como `DocsDataError`; 429 y 5xx como `DocsNetworkError`
  (reintentable).

## Limitaciones conocidas

- Solo puede acceder a documentos **compartidos con la cuenta
  autorizada** (o de su propiedad) — no puede descubrir ni listar
  documentos por sí solo.
- `read_document` devuelve **texto plano**: no preserva estilos,
  imágenes, encabezados/pies de página ni comentarios (el contenido de
  tablas sí se incluye, en orden de aparición).
- `replace_text` busca texto **literal** (no expresiones regulares) y
  reemplaza todas las ocurrencias — no hay reemplazo selectivo por
  posición.
- No elimina documentos, no cambia permisos, no mueve archivos entre
  carpetas ni exporta a otros formatos (para descargar como PDF usa el
  conector `drive_oauth`).
- En modo "Usar credenciales propias" o "Refresh token manual" con una
  app OAuth en estado *Testing*, el refresh token puede expirar a los
  7 días sin uso.
