"""De dónde salen las fotos: de la web o de una carpeta de tu computadora.

Las dos fuentes entregan lo mismo —carpetas y fotos con el mismo formato—
así que al resto del programa le da igual cuál se esté usando.
"""

from . import carpeta_local, pictime


class ErrorFuente(Exception):
    """No se pudo leer de donde vienen las fotos."""


def _es_web(datos):
    return datos.get("origen", "web") == "web"


def descripcion(datos):
    """Una línea que dice de dónde se está leyendo, para los mensajes."""
    if _es_web(datos):
        return datos["galeria"]
    return str(carpeta_local.raiz(datos))


def listar_carpetas(datos):
    """Las carpetas disponibles, ya filtradas por los ajustes."""
    if _es_web(datos):
        try:
            carpetas = pictime.listar_carpetas(datos["galeria"])
        except pictime.ErrorGaleria as e:
            raise ErrorFuente(str(e)) from e
    else:
        carpetas = carpeta_local.listar_carpetas(datos)
    return carpetas


def listar_fotos(datos, carpeta):
    """Las fotos de una carpeta."""
    if _es_web(datos):
        try:
            return pictime.listar_fotos(datos["galeria"], carpeta)
        except pictime.ErrorGaleria as e:
            raise ErrorFuente(str(e)) from e
    return carpeta_local.listar_fotos(datos, carpeta)
