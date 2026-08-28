"""Leer fotos de una carpeta de tu computadora en vez de la web.

Sirve cuando bajaste las galerías de Pic-Time como ZIP y las descomprimiste:
el indexado funciona igual, y buscar copia los archivos en vez de bajarlos.
"""

import os
from pathlib import Path

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


def raiz(datos):
    return Path(os.path.expanduser(datos.get("carpeta_local", ""))).resolve()


def listar_carpetas(datos):
    """Cada subcarpeta con fotos cuenta como una carpeta de la galería."""
    base = raiz(datos)
    if not base.is_dir():
        return []

    encontradas = []
    for directorio, _, archivos in os.walk(base):
        fotos = [a for a in archivos if Path(a).suffix.lower() in EXTENSIONES]
        if not fotos:
            continue
        ruta = Path(directorio)
        nombre = str(ruta.relative_to(base)) if ruta != base else base.name
        encontradas.append({"nombre": nombre, "ruta": str(ruta), "cantidad": len(fotos)})
    encontradas.sort(key=lambda c: c["nombre"])
    return encontradas


def listar_fotos(datos, carpeta):
    """Las fotos de una carpeta, con el mismo formato que las de la web."""
    base = raiz(datos)
    ruta = Path(carpeta["ruta"])
    fotos = []
    for archivo in sorted(ruta.iterdir()):
        if archivo.suffix.lower() not in EXTENSIONES or not archivo.is_file():
            continue
        fotos.append(
            {
                # La ruta relativa identifica la foto de forma estable aunque
                # muevas la carpeta entera a otro sitio.
                "id": str(archivo.relative_to(base)),
                "carpeta": carpeta["nombre"],
                "archivo": str(archivo),
                "url_mini": None,
                "url_grande": None,
            }
        )
    return fotos
