"""Preparar una foto para mandársela a Claude.

Las fotos de una cámara pesan varios megas y son mucho más grandes de lo que
el modelo necesita para ver qué hay en ellas. Si está instalado Pillow se
achican antes de mandarlas, que sale más rápido y más barato.
"""

import io
from pathlib import Path

# Lado máximo en píxeles. Por encima de esto el modelo no gana precisión.
LADO_MAXIMO = 1024

# Tope de la API por imagen. Se deja margen porque base64 crece un tercio.
PESO_MAXIMO = 3_500_000


class ErrorImagen(Exception):
    """La foto no se pudo preparar."""


def _con_pillow(ruta):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None

    with Image.open(ruta) as imagen:
        # exif_transpose respeta la rotación que grabó la cámara; sin esto
        # las fotos verticales llegarían acostadas y el modelo las describiría
        # como horizontales.
        imagen = ImageOps.exif_transpose(imagen)
        imagen = imagen.convert("RGB")
        imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        buffer = io.BytesIO()
        imagen.save(buffer, format="JPEG", quality=80)
        return buffer.getvalue(), "image/jpeg"


TIPOS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def preparar(ruta):
    """Los bytes de la foto listos para mandar, y su tipo."""
    ruta = Path(ruta)
    achicada = _con_pillow(ruta)
    if achicada is not None:
        return achicada

    datos = ruta.read_bytes()
    if len(datos) > PESO_MAXIMO:
        raise ErrorImagen(
            f"{ruta.name} pesa {len(datos) // 1_000_000} MB y hay que achicarla "
            "antes de mandarla. Instala Pillow con:  python3 -m pip install pillow"
        )
    return datos, TIPOS.get(ruta.suffix.lower(), "image/jpeg")
