"""Cliente de lectura de Genesis. La sincronización nunca recibe hechos de casos."""
import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://apigenesis.tsj.bo/api/v1"


class TSJApi:
    def __init__(self):
        if not settings.TSJ_API_KEY:
            raise ValueError("Configura TSJ_API_KEY para consultar Genesis del TSJ.")
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json", "apikey": settings.TSJ_API_KEY,
            "username": settings.TSJ_API_USERNAME, "origin": "https://genesis.tsj.bo",
            "User-Agent": "SW-Derecho/1.0 (consulta de jurisprudencia pública)",
        })
        self.session.mount("https://", HTTPAdapter(max_retries=Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )))

    def buscar(self, pagina, palabras="penal"):
        respuesta = self.session.post(f"{BASE_URL}/resoluciones/busqueda_avanzada", json={
            "searchData": {
                "todasEstasPalabras": palabras, "estaPalabraOFraseExacta": None,
                "cualquieraEstasPalabras": None, "ningunaEstasPalabras": None,
            },
            "filter": {
                "idMateria": "1", "idSala": None, "gestion": None,
                "idTipoResolucion": None, "idMagistrado": None, "idDepartamento": None,
                "idTipoProceso": None, "idFormaResolucion": None,
            },
            "paginate": {"page": pagina, "limit": 50},
        }, timeout=(10, 30))
        respuesta.raise_for_status()
        datos = respuesta.json()["data"]
        if not isinstance(datos.get("data"), list) or not isinstance(datos.get("meta"), dict):
            raise ValueError("Respuesta de búsqueda del TSJ inválida.")
        return datos

    def detalle(self, fuente_id):
        fuente_id = str(fuente_id)
        if not fuente_id.isdigit():
            raise ValueError("Identificador del TSJ inválido.")
        respuesta = self.session.get(f"{BASE_URL}/resoluciones/{fuente_id}", timeout=(10, 30))
        respuesta.raise_for_status()
        datos = respuesta.json()["data"]
        if not isinstance(datos, dict) or str(datos.get("id")) != fuente_id:
            raise ValueError("El detalle del TSJ no coincide con la resolución solicitada.")
        return datos

    def close(self):
        self.session.close()
