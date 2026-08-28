"""Dónde está la galería, dónde se guardan las fotos y con qué modelo se leen."""

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ARCHIVO_AJUSTES = RAIZ / "ajustes.json"
ARCHIVO_INDICE = RAIZ / "indice.json"

POR_DEFECTO = {
    # Dirección de la galería, sin barra al final.
    "galeria": "https://macabeadaspty.pic-time.com",
    # Solo se indexan las carpetas cuyo nombre contenga alguno de estos textos.
    # Vacío = todas las carpetas. Sirve para dejar fuera las macabeadas de
    # grandes y quedarse solo con las de los chicos.
    "carpetas": [],
    # Carpeta de tu computadora donde caen las fotos que pides.
    "destino": "~/Descargas/fotos-macabeadas",
    # Modelo que mira las fotos. Haiku es el más barato y alcanza de sobra.
    "modelo": "claude-haiku-4-5-20251001",
    # Cuántas fotos baja cada búsqueda si no dices otra cosa.
    "cuantas": 5,
}


def cargar():
    """Los ajustes del archivo, completados con los valores por defecto."""
    datos = dict(POR_DEFECTO)
    if ARCHIVO_AJUSTES.exists():
        datos.update(json.loads(ARCHIVO_AJUSTES.read_text("utf-8")))
    datos["galeria"] = datos["galeria"].rstrip("/")
    return datos


def guardar(datos):
    ARCHIVO_AJUSTES.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )


def carpeta_destino(datos=None):
    datos = datos or cargar()
    ruta = Path(os.path.expanduser(datos["destino"]))
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def clave_api():
    """La llave de la API de Claude, necesaria solo para indexar."""
    clave = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not clave:
        archivo = RAIZ / "clave.txt"
        if archivo.exists():
            clave = archivo.read_text("utf-8").strip()
    return clave
