"""Validacion local del conector docs: ejercita las 4 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_DOCS_* exportadas en el entorno, obtenidas
con get_refresh_token.py. No necesita ningun documento previo: crea uno
nuevo y trabaja sobre el.
"""

from ruvic_docs_connector import DocsClient, setup_logging

setup_logging("INFO")
client = DocsClient()

print("== 1. Crear un documento de prueba ==")
created = client.create_document(
    "Prueba conector Docs Ruvic",
    "Documento creado por validate_local.py.\nCliente: {{CLIENTE}}\n",
)
doc_id = created["id"]
print(f"  Creado: id={doc_id}")
print(f"  URL: {created['url']}")

print("== 2. Agregar texto al final ==")
result = client.append_text(doc_id, "Parrafo agregado al final.\n")
print(f"  {result}")

print("== 3. Buscar y reemplazar ==")
result = client.replace_text(doc_id, "{{CLIENTE}}", "ACME S.A.")
print(f"  {result}")

print("== 4. Leer el documento completo ==")
doc = client.read_document(doc_id)
print(f"  Titulo: {doc['title']}")
print(f"  Texto: {doc['body_text']!r}")
