"""Copiar las fotos encontradas a la carpeta de resultados."""

import re
import shutil
import unicodedata
from pathlib import Path


def nombre_seguro(texto, maximo=60):
    """Convierte cualquier texto en un nombre de archivo válido."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Za-z0-9]+", "-", texto).strip("-").lower()
    return (texto or "foto")[:maximo]


def copiar(origen, carpeta, nombre):
    """Copia una foto a `carpeta` con el nombre dado, sin pisar nada.

    Si ya hay un archivo con ese nombre le añade un número, para no borrar
    el resultado de una búsqueda anterior.
    """
    origen = Path(origen)
    destino = carpeta / f"{nombre}{origen.suffix.lower()}"
    contador = 2
    while destino.exists():
        destino = carpeta / f"{nombre}-{contador}{origen.suffix.lower()}"
        contador += 1

    # copy2 conserva la fecha del archivo original, útil para ordenar después.
    shutil.copy2(origen, destino)
    return destino
