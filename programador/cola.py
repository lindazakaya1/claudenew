"""Cola de publicaciones: crear, listar, detectar vencidas y archivar."""

import json
import re
import unicodedata
from datetime import datetime

from . import config

REDES_VALIDAS = ("instagram", "facebook")


def _slug(texto, largo=40):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto[:largo] or "publicacion"


def parsear_fecha(cuando):
    """Acepta '2026-08-21 10:00', '2026-08-21T10:00' o ISO con zona.

    Si no trae zona horaria, se asume la del config.json.
    """
    texto = str(cuando).strip().replace(" ", "T")
    fecha = datetime.fromisoformat(texto)
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=config.zona_horaria())
    return fecha


def crear(texto, cuando, imagen=None, imagen_url=None, redes=None, tipo="imagen"):
    """Guarda una publicación programada y devuelve (ruta, publicacion)."""
    if not imagen and not imagen_url:
        raise ValueError("Hace falta --imagen (archivo del repo) o --imagen-url")
    if imagen and imagen_url:
        raise ValueError("Usa --imagen o --imagen-url, no las dos")

    redes = [r.strip().lower() for r in (redes or config.cargar()["redes_por_defecto"])]
    desconocidas = [r for r in redes if r not in REDES_VALIDAS]
    if desconocidas:
        raise ValueError(f"Redes no soportadas: {', '.join(desconocidas)}")

    if imagen:
        ruta_foto = config.RAIZ / imagen
        if not ruta_foto.exists():
            raise ValueError(f"No encuentro el archivo {imagen} en el repo")

    fecha = parsear_fecha(cuando)
    publicacion = {
        "id": f"{fecha:%Y%m%dT%H%M}-{_slug(texto)}",
        "cuando": fecha.isoformat(),
        "texto": texto,
        "tipo": tipo,
        "redes": redes,
        "estado": "programado",
    }
    if imagen:
        publicacion["imagen"] = str(imagen)
    else:
        publicacion["imagen_url"] = imagen_url

    config.DIR_PROGRAMADOS.mkdir(parents=True, exist_ok=True)
    ruta = config.DIR_PROGRAMADOS / f"{publicacion['id']}.json"
    ruta.write_text(
        json.dumps(publicacion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return ruta, publicacion


def listar(directorio=None):
    """Devuelve [(ruta, publicacion)] ordenadas por fecha de publicación."""
    directorio = directorio or config.DIR_PROGRAMADOS
    if not directorio.exists():
        return []
    items = []
    for ruta in sorted(directorio.glob("*.json")):
        with ruta.open(encoding="utf-8") as f:
            items.append((ruta, json.load(f)))
    items.sort(key=lambda par: parsear_fecha(par[1]["cuando"]))
    return items


def pendientes(ahora=None):
    """Publicaciones cuya hora ya llegó y que siguen sin publicarse."""
    ahora = ahora or datetime.now(config.zona_horaria())
    return [
        (ruta, pub)
        for ruta, pub in listar()
        if pub.get("estado") == "programado" and parsear_fecha(pub["cuando"]) <= ahora
    ]


def url_de_imagen(publicacion):
    """URL pública de la imagen/video, venga de un archivo del repo o de fuera."""
    if publicacion.get("imagen_url"):
        return publicacion["imagen_url"]
    return config.url_publica_de_foto(publicacion["imagen"])


def archivar(ruta, publicacion, resultados):
    """Mueve la publicación a publicados/ dejando constancia de lo ocurrido."""
    publicacion["estado"] = "publicado"
    publicacion["publicado_en"] = datetime.now(config.zona_horaria()).isoformat()
    publicacion["resultados"] = resultados

    config.DIR_PUBLICADOS.mkdir(parents=True, exist_ok=True)
    destino = config.DIR_PUBLICADOS / ruta.name
    destino.write_text(
        json.dumps(publicacion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    ruta.unlink()
    return destino


def marcar_error(ruta, publicacion, mensaje):
    """Deja la publicación en la cola pero anota el fallo para poder revisarlo."""
    publicacion["ultimo_error"] = mensaje
    publicacion["intentos"] = publicacion.get("intentos", 0) + 1
    ruta.write_text(
        json.dumps(publicacion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
