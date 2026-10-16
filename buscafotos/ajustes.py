"""De dónde salen las fotos, dónde se guardan y con qué modelo se leen."""

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ARCHIVO_AJUSTES = RAIZ / "ajustes.json"
ARCHIVO_INDICE = RAIZ / "indice.json"

POR_DEFECTO = {
    # "web" lee la galería de Pic-Time directamente.
    # "carpeta" lee una carpeta de tu computadora, por si algún día
    # Pic-Time cambia su sitio y el modo web deja de funcionar.
    "origen": "web",
    # Dirección de la galería, para el modo web.
    "galeria": "https://macabeadaspty.pic-time.com",
    # Carpeta de tu computadora, para el modo carpeta.
    "carpeta_local": "~/Descargas/Macabeadas",
    # Solo se indexan las carpetas cuyo nombre contenga alguno de estos
    # textos. Vacío = todas. "Juveniles" deja fuera las de los grandes.
    "carpetas": ["Juveniles"],
    # Dónde te deja las fotos que pides.
    "destino": "~/Descargas/fotos-elegidas",
    # Modelo que mira las fotos. Haiku es el más barato y alcanza de sobra.
    "modelo": "claude-haiku-4-5-20251001",
    # Cuántas fotos trae cada búsqueda si no dices otra cosa.
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
