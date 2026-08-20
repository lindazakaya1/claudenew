"""Publicación en Instagram y Facebook a través de la Graph API de Meta."""

import time

import requests

from .config import VERSION_API

BASE = f"https://graph.facebook.com/{VERSION_API}"
TIEMPO_ESPERA = 60


class ErrorMeta(RuntimeError):
    """La Graph API respondió con un error."""


def _pedir(metodo, ruta, **parametros):
    respuesta = requests.request(
        metodo, f"{BASE}/{ruta}", data=parametros, timeout=TIEMPO_ESPERA
    )
    try:
        cuerpo = respuesta.json()
    except ValueError:
        raise ErrorMeta(f"Respuesta no válida de Meta ({respuesta.status_code})")
    if "error" in cuerpo:
        error = cuerpo["error"]
        raise ErrorMeta(
            f"{error.get('type', 'Error')}: {error.get('message', 'sin detalle')}"
        )
    return cuerpo


def _esperar_procesado(creation_id, token, intentos=20, pausa=15):
    """Los reels tardan en subirse; hay que esperar a que Meta los procese."""
    for _ in range(intentos):
        estado = _pedir(
            "GET", creation_id, fields="status_code", access_token=token
        ).get("status_code")
        if estado == "FINISHED":
            return
        if estado == "ERROR":
            raise ErrorMeta("Meta no pudo procesar el video")
        time.sleep(pausa)
    raise ErrorMeta("El video sigue procesándose después de esperar demasiado")


def publicar_instagram(ig_user_id, token, url_media, texto, tipo="imagen"):
    """Sube y publica en Instagram. Devuelve el id del post creado."""
    if tipo == "reel":
        contenedor = _pedir(
            "POST",
            f"{ig_user_id}/media",
            media_type="REELS",
            video_url=url_media,
            caption=texto,
            access_token=token,
        )
        _esperar_procesado(contenedor["id"], token)
    else:
        contenedor = _pedir(
            "POST",
            f"{ig_user_id}/media",
            image_url=url_media,
            caption=texto,
            access_token=token,
        )

    publicado = _pedir(
        "POST",
        f"{ig_user_id}/media_publish",
        creation_id=contenedor["id"],
        access_token=token,
    )
    return publicado["id"]


def publicar_facebook(page_id, token, url_media, texto):
    """Publica una foto en la página de Facebook. Devuelve el id del post."""
    publicado = _pedir(
        "POST", f"{page_id}/photos", url=url_media, caption=texto, access_token=token
    )
    return publicado.get("post_id") or publicado["id"]


def publicar(publicacion, url_media, credenciales):
    """Publica en todas las redes pedidas. Devuelve {red: id_del_post}."""
    resultados = {}
    for red in publicacion["redes"]:
        if red == "instagram":
            if not credenciales["ig_user_id"]:
                raise ErrorMeta("Falta el secret IG_USER_ID")
            resultados["instagram"] = publicar_instagram(
                credenciales["ig_user_id"],
                credenciales["token"],
                url_media,
                publicacion["texto"],
                publicacion.get("tipo", "imagen"),
            )
        elif red == "facebook":
            if not credenciales["fb_page_id"]:
                raise ErrorMeta("Falta el secret FB_PAGE_ID")
            resultados["facebook"] = publicar_facebook(
                credenciales["fb_page_id"],
                credenciales["token"],
                url_media,
                publicacion["texto"],
            )
    return resultados
