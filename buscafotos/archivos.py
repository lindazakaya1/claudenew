"""Dejar las fotos encontradas en la carpeta de resultados."""

import re
import shutil
import unicodedata
from pathlib import Path

from . import pictime


class ErrorEntrega(Exception):
    """La foto no se pudo dejar en la carpeta."""


def nombre_seguro(texto, maximo=60):
    """Convierte cualquier texto en un nombre de archivo válido."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Za-z0-9]+", "-", texto).strip("-").lower()
    return (texto or "foto")[:maximo]


def _sin_pisar(carpeta, nombre, extension):
    """Un nombre libre, para no borrar el resultado de otra búsqueda."""
    destino = carpeta / f"{nombre}{extension}"
    contador = 2
    while destino.exists():
        destino = carpeta / f"{nombre}-{contador}{extension}"
        contador += 1
    return destino


def entregar(foto, carpeta, nombre):
    """Deja una foto en `carpeta`: la copia del disco o la baja de la web."""
    if foto.get("archivo"):
        origen = Path(foto["archivo"])
        destino = _sin_pisar(carpeta, nombre, origen.suffix.lower())
        try:
            # copy2 conserva la fecha original, útil para ordenar después.
            shutil.copy2(origen, destino)
        except OSError as e:
            raise ErrorEntrega(f"no se pudo copiar: {e}") from e
        return destino

    try:
        datos, _ = pictime.bajar(foto["url"])
    except pictime.ErrorGaleria as e:
        raise ErrorEntrega(str(e)) from e
    destino = _sin_pisar(carpeta, nombre, ".jpg")
    destino.write_bytes(datos)
    return destino
