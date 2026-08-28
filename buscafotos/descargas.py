"""Bajar archivos de internet a una carpeta de tu computadora."""

import gzip
import io
import re
import unicodedata
import urllib.error
import urllib.request
import zlib

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class ErrorDescarga(Exception):
    """No se pudo traer un archivo."""


def traer(url, cabeceras=None, timeout=60):
    """Los bytes de una dirección, ya descomprimidos."""
    if url.startswith("//"):
        url = "https:" + url
    pedido = urllib.request.Request(url)
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    for clave, valor in (cabeceras or {}).items():
        pedido.add_header(clave, valor)
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resp:
            crudo = resp.read()
            codificacion = resp.headers.get("Content-Encoding", "")
            if codificacion == "gzip":
                crudo = gzip.GzipFile(fileobj=io.BytesIO(crudo)).read()
            elif codificacion == "deflate":
                crudo = zlib.decompress(crudo, -zlib.MAX_WBITS)
            return crudo, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise ErrorDescarga(f"HTTP {e.code} al pedir {url}") from e
    except urllib.error.URLError as e:
        raise ErrorDescarga(f"sin conexión al pedir {url}: {e.reason}") from e


def nombre_seguro(texto, maximo=60):
    """Convierte cualquier texto en un nombre de archivo válido."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Za-z0-9]+", "-", texto).strip("-").lower()
    return (texto or "foto")[:maximo]


def guardar(url, carpeta, nombre):
    """Baja `url` y la guarda como `nombre` dentro de `carpeta`.

    Si ya existe un archivo con ese nombre, le añade un número en vez de
    pisarlo, para no perder una foto bajada antes.
    """
    datos, tipo = traer(url)
    extension = ".jpg"
    if "png" in tipo:
        extension = ".png"
    elif "webp" in tipo:
        extension = ".webp"

    destino = carpeta / f"{nombre}{extension}"
    contador = 2
    while destino.exists():
        destino = carpeta / f"{nombre}-{contador}{extension}"
        contador += 1

    destino.write_bytes(datos)
    return destino
