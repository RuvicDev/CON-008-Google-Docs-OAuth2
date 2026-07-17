---
name: docs
description: >
  Usa la librería ruvic_docs_connector para leer, crear y editar
  documentos de Google Docs - leer el título y texto completo de un
  documento (read_document), crear un documento nuevo (create_document),
  agregar texto al final (append_text) y buscar/reemplazar texto en todo
  el documento (replace_text). Úsala cuando el usuario pida leer,
  resumir, crear, redactar o actualizar un documento de Google Docs,
  llenar una plantilla con marcadores tipo {{CAMPO}}, o agregar
  contenido a un documento existente.
triggers:
- google docs
- documento
- documentos
- docs
- acta
- plantilla
- redactar documento
- crear documento
---

# Conector Google Docs (ruvic_docs_connector)

Librería Python para leer, crear y editar documentos de Google Docs (cuenta personal o Google Workspace). Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Docs.git#subdirectory=lib`). Usa la API oficial de Docs con OAuth2 y un refresh token obtenido una única vez durante la configuración.

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `docs` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_DOCS_CLIENT_ID` | Client ID del cliente OAuth de Google Cloud |
| `RUVIC_DOCS_CLIENT_SECRET` | Client Secret del mismo cliente OAuth |
| `RUVIC_DOCS_REFRESH_TOKEN` | Refresh token obtenido al autorizar el acceso |
| `RUVIC_DOCS_REQUEST_TIMEOUT` | (opcional) timeout en segundos, default 30 |

Estas mismas variables se usan sin importar cuál de los 3 modos de autorización eligió el usuario en el formulario (Autorizar con Google, credenciales propias, o refresh token manual).

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**. El código generado **NUNCA** usa nombres con segmento de alias (`_DEFAULT_INSTANCIA_`, `_PRODUCCION_`, etc.) salvo que aparezcan en una sección autogenerada `## Variables en tu entorno` al final de este skill.

## Conexión (siempre igual)

```python
from ruvic_docs_connector import DocsClient

client = DocsClient()  # lee RUVIC_DOCS_* del entorno automáticamente
```

## Identificar el documento

El `document_id` es el que aparece en la URL del documento:
`https://docs.google.com/document/d/`**`ESTE_ID`**`/edit`. Si el usuario
pega la URL completa, extrae solo esa parte.

## Capacidad 1 — Leer un documento

```python
doc = client.read_document("1AbC...xyz")
print(doc["title"])
print(doc["body_text"])  # texto plano, incluye el contenido de tablas
```

## Capacidad 2 — Crear un documento nuevo

```python
created = client.create_document(
    "Acta de reunión — julio",
    body_text="Asistentes:\n- ...\n\nAcuerdos:\n- ...\n",  # opcional
)
print(created["url"])  # link directo para el usuario
```

El documento se crea en la raíz de "Mi unidad" de la cuenta autorizada.

## Capacidad 3 — Agregar texto al final

```python
result = client.append_text("1AbC...xyz", "\nPárrafo agregado al final.\n")
print(result["appended_chars"])
```

## Capacidad 4 — Buscar y reemplazar texto

```python
result = client.replace_text("1AbC...xyz", "{{CLIENTE}}", "ACME S.A.")
print(result["occurrences_changed"])
```

Reemplaza **todas** las ocurrencias (texto literal, no regex). Ideal para
llenar plantillas con marcadores tipo `{{CAMPO}}`. Usa `match_case=False`
para ignorar mayúsculas/minúsculas.

## Manejo de errores

```python
from ruvic_docs_connector import DocsAuthError, DocsDataError, DocsNetworkError

try:
    client.read_document("1AbC...xyz")
except DocsAuthError:
    print("Credenciales inválidas o refresh token vencido — revisa la configuración del conector")
except DocsNetworkError:
    print("Docs API no respondió — puede ser un límite de cuota temporal")
except DocsDataError as e:
    print(f"Error de datos: {e}")  # ej. el documento no existe o no es accesible
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_DOCS_*` (el constructor de `DocsClient` ya lo hace).
2. Nunca imprimas `RUVIC_DOCS_CLIENT_SECRET` ni `RUVIC_DOCS_REFRESH_TOKEN` en logs ni en la salida.
3. El conector solo puede acceder a documentos que estén **compartidos con la cuenta autorizada** (o de su propiedad). Si falla con "no existe o no es accesible", el usuario debe compartir el documento con esa cuenta (como Editor para poder escribir).
4. Para llenar plantillas, usa `replace_text` con marcadores únicos (`{{CLIENTE}}`, `{{FECHA}}`) — una llamada por marcador.
5. `read_document` devuelve texto plano sin formato — suficiente para leer, resumir o verificar contenido, pero no preserva estilos, imágenes ni comentarios.
6. El conector no elimina documentos, no cambia permisos ni accede a otros archivos de Drive.
