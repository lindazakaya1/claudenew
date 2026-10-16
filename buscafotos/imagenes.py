"""Preparar una foto para mandársela a Claude.

Una foto puede venir de un archivo de tu computadora o de la galería en la
web. En los dos casos sale de aquí como bytes listos para mandar. Si está
instalado Pillow se achican antes, que sale más rápido y más barato.
"""

import io
from pathlib import Path

from . import pictime

# Lado máximo en píxeles. Por encima de esto el modelo no gana precisión.
LADO_MAXIMO = 1024

# Tope de la API por imagen. Se deja margen porque base64 crece un tercio.
PESO_MAXIMO = 3_500_000

TIPOS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class ErrorImagen(Exception):
    """La foto no se pudo preparar."""


def _achicar(datos):
    """Los bytes achicados, o None si Pillow no está instalado."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None

    with Image.open(io.BytesIO(datos)) as imagen:
        # exif_transpose respeta la rotación que grabó la cámara; sin esto
        # las fotos verticales llegarían acostadas y el modelo las
        # describiría como horizontales.
        imagen = ImageOps.exif_transpose(imagen)
        imagen = imagen.convert("RGB")
        imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        buffer = io.BytesIO()
        imagen.save(buffer, format="JPEG", quality=80)
        return buffer.getvalue()


def preparar(foto):
    """Los bytes de una foto listos para mandar, y su tipo."""
    if foto.get("archivo"):
        ruta = Path(foto["archivo"])
        datos = ruta.read_bytes()
        tipo = TIPOS.get(ruta.suffix.lower(), "image/jpeg")
        nombre = ruta.name
    else:
        try:
            datos, tipo = pictime.bajar(foto["url"])
        except pictime.ErrorGaleria as e:
            raise ErrorImagen(str(e)) from e
        nombre = foto.get("id", "la foto")

    achicada = _achicar(datos)
    if achicada is not None:
        return achicada, "image/jpeg"

    if len(datos) > PESO_MAXIMO:
        raise ErrorImagen(
            f"{nombre} pesa {len(datos) // 1_000_000} MB y hay que achicarla "
            "antes de mandarla. Instala Pillow con:  python3 -m pip install pillow"
        )
    return datos, tipo
