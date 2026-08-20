"""Carga de configuración y credenciales."""

import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONFIG = RAIZ / "config.json"
DIR_PROGRAMADOS = RAIZ / "programados"
DIR_PUBLICADOS = RAIZ / "publicados"
DIR_FOTOS = RAIZ / "fotos"

# Versión de la Graph API de Meta. Se puede subir sin tocar el código.
VERSION_API = os.environ.get("GRAPH_API_VERSION", "v21.0")


def cargar():
    """Devuelve el config.json como diccionario."""
    with RUTA_CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def zona_horaria():
    return ZoneInfo(cargar().get("zona_horaria", "UTC"))


def credenciales():
    """Lee las credenciales de Meta desde variables de entorno.

    En GitHub se configuran como Secrets del repositorio.
    """
    return {
        "token": os.environ.get("META_ACCESS_TOKEN", ""),
        "ig_user_id": os.environ.get("IG_USER_ID", ""),
        "fb_page_id": os.environ.get("FB_PAGE_ID", ""),
    }


def url_publica_de_foto(ruta_relativa):
    """Convierte 'fotos/playa.jpg' en una URL pública que Meta pueda descargar.

    Instagram no acepta archivos subidos directamente: exige una URL a la que
    sus servidores puedan entrar. Usamos raw.githubusercontent, que sirve los
    archivos del repo tal cual (el repo debe ser público).
    """
    cfg = cargar()
    repo = cfg["repo"]
    rama = cfg.get("rama_fotos", "main")
    ruta = str(ruta_relativa).lstrip("/")
    return f"https://raw.githubusercontent.com/{repo}/{rama}/{ruta}"
