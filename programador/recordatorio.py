"""Avisos push al celular a la hora programada, usando ntfy.sh.

Para cuentas privadas de Instagram no existe publicación automática legítima:
la API de Meta no las admite. Lo más cercano es este modo recordatorio, que a
la hora exacta te manda una notificación con el texto listo para copiar y la
foto adjunta para descargar. Solo queda abrir Instagram y pegar.
"""

from email.header import Header
from pathlib import Path

import requests

SERVIDOR = "https://ntfy.sh"
TIEMPO_ESPERA = 60


class ErrorRecordatorio(RuntimeError):
    """No se pudo enviar la notificación."""


def _cabecera(valor):
    """Codifica en RFC 2047 si el texto trae acentos o emojis.

    Las cabeceras HTTP son ASCII; ntfy sabe descifrar este formato y muestra
    el texto original en el celular.
    """
    if valor.isascii():
        return valor
    return Header(valor, "utf-8").encode()


def _nombre_seguro(nombre):
    """ntfy espera un nombre de archivo en ASCII simple."""
    limpio = "".join(c if c.isascii() and (c.isalnum() or c in "._-") else "_" for c in nombre)
    return limpio or "adjunto"


def enviar(topico, titulo, mensaje, adjunto=None, etiquetas="camera"):
    """Envía la notificación. Devuelve el id que asigna ntfy."""
    if not topico:
        raise ErrorRecordatorio("Falta el secret NTFY_TOPIC")

    cabeceras = {
        "X-Title": _cabecera(titulo),
        "X-Tags": etiquetas,
        "X-Priority": "high",
    }

    if adjunto:
        ruta = Path(adjunto)
        if not ruta.exists():
            raise ErrorRecordatorio(f"No encuentro el archivo {adjunto}")
        # Con adjunto, el cuerpo es el archivo y el texto viaja en la cabecera.
        cabeceras["X-Message"] = _cabecera(mensaje)
        cabeceras["X-Filename"] = _nombre_seguro(ruta.name)
        cuerpo = ruta.read_bytes()
    else:
        cuerpo = mensaje.encode("utf-8")

    try:
        respuesta = requests.put(
            f"{SERVIDOR}/{topico}",
            data=cuerpo,
            headers=cabeceras,
            timeout=TIEMPO_ESPERA,
        )
    except requests.RequestException as error:
        raise ErrorRecordatorio(f"No se pudo contactar a ntfy: {error}") from error

    if respuesta.status_code >= 400:
        raise ErrorRecordatorio(
            f"ntfy respondió {respuesta.status_code}: {respuesta.text[:200]}"
        )
    return respuesta.json().get("id", "")


def avisar(publicacion, topico, ruta_foto=None, enlace=None):
    """Manda el recordatorio de una publicación programada."""
    redes = " y ".join(r.capitalize() for r in publicacion["redes"])
    mensaje = publicacion["texto"]
    if enlace and not ruta_foto:
        # La foto vive fuera del repo: no se puede adjuntar, va como enlace.
        mensaje = f"{mensaje}\n\nFoto: {enlace}"

    id_ntfy = enviar(
        topico,
        titulo=f"Hora de publicar en {redes}",
        mensaje=mensaje,
        adjunto=ruta_foto,
    )
    return {"recordatorio": id_ntfy}
