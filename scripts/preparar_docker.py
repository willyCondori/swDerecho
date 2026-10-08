"""Genera el entorno local de Compose sin sobrescribir claves existentes."""
from pathlib import Path
import re
import secrets

raiz = Path(__file__).resolve().parent.parent
destino = raiz / '.env.docker'
if destino.exists():
    print('.env.docker ya existe; se conserva sin cambios.')
else:
    local = raiz / 'backend' / '.env'
    datos = local.read_text(encoding='utf-8-sig') if local.exists() else ''
    clave = re.search(r'^ENCRYPTION_KEY\s*=\s*[\'\"]?([a-fA-F0-9]{64})[\'\"]?\s*$', datos, re.MULTILINE)
    version = re.search(r'^EMBEDDING_MODEL_VERSION\s*=\s*[\'\"]?([\w.-]+)', datos, re.MULTILINE)
    contenido = (raiz / '.env.docker.example').read_text(encoding='utf-8')
    contenido = contenido.replace('CAMBIAR_POR_64_CARACTERES_HEXADECIMALES', clave.group(1) if clave else secrets.token_hex(32))
    contenido = contenido.replace('SECRET_KEY=CAMBIAR', 'SECRET_KEY=' + secrets.token_hex(48))
    contenido = contenido.replace('DB_PASSWORD=CAMBIAR', 'DB_PASSWORD=' + secrets.token_hex(24))
    if version:
        contenido = contenido.replace('EMBEDDING_MODEL_VERSION=sw-derecho-embeddings-v1', 'EMBEDDING_MODEL_VERSION=' + version.group(1))
    with destino.open('x', encoding='utf-8') as archivo:
        archivo.write(contenido)
    print('.env.docker creado. Las claves no se muestran ni se guardan en Git.')
    if clave:
        print('Se conservó la clave de cifrado local para permitir importar los datos existentes.')
modelo = raiz / 'backend' / 'modelos' / 'sw-derecho-embeddings-v1-final'
if not (modelo / 'modules.json').is_file():
    print('Falta el modelo afinado: copia su carpeta completa a backend/modelos/sw-derecho-embeddings-v1-final.')
