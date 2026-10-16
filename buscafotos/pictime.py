"""Leer una galería de Pic-Time directamente de la web.

Pic-Time no publica una forma de consultar sus galerías, así que esto se
dedujo observando cómo las pide su propio sitio. Las piezas:

* El portafolio (la lista de carpetas) vive en el CDN de la cuenta:
      /pictures/accountdata/{cuenta//1000}/{cuenta}/client/{portafolio}/portfolio.json.txt
  Viene como listas numeradas, sin nombres: cada carpeta es
      [id, nombre, ruta, portada, foco, proporción, ...]

* La página de una carpeta lleva un guion delante: /-{ruta}
  De sus initParams salen el id del proyecto, su almacenamiento y su token.

* Los datos de un proyecto viven en
      /pictures/{id//1e6}/{(id//1e3)%1000}/{id}/{token}
  sin ninguna carpeta intermedia, y dentro están gallery.json.txt con el
  listado y thumbres/ midres/ lowres/ con las fotos.

* En el listado, cada escena trae una lista `photos` de números: cinco por
  foto, y el primero de cada cinco es la diferencia contra `minId`.

Si Pic-Time cambia su sitio, esto puede dejar de funcionar. Cuando pase, el
mensaje de error dice en qué paso falló para no tener que adivinar.
"""

import gzip
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Cada foto ocupa cinco números seguidos en la lista de una escena.
CAMPOS_POR_FOTO = 5

# Tamaños que sirve Pic-Time, de menor a mayor.
TAMANOS = ("thumbres", "thumbs", "smallres", "lowres", "midres")


class ErrorGaleria(Exception):
    """No se pudo leer la galería."""


def _traer(url, que=""):
    if url.startswith("//"):
        url = "https:" + url
    url = urllib.parse.quote(url, safe=":/?&=%#+.,~_-")
    pedido = urllib.request.Request(url)
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resp:
            crudo = resp.read()
            cod = resp.headers.get("Content-Encoding", "")
            if cod == "gzip":
                crudo = gzip.GzipFile(fileobj=io.BytesIO(crudo)).read()
            elif cod == "deflate":
                crudo = zlib.decompress(crudo, -zlib.MAX_WBITS)
            return crudo
    except urllib.error.HTTPError as e:
        raise ErrorGaleria(f"{que or 'la galería'}: HTTP {e.code} al pedir {url}") from e
    except urllib.error.URLError as e:
        raise ErrorGaleria(f"{que or 'la galería'}: sin conexión ({e.reason})") from e


def _parametros(html, que):
    """Los initParams que Pic-Time deja en cada página."""
    m = re.search(r"initParams\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        raise ErrorGaleria(f"{que}: la página no trae initParams. "
                           "Puede que Pic-Time haya cambiado su sitio.")
    return json.loads(m.group(1))


def _almacenamientos(html):
    m = re.search(r"_pictimeStorageMapping\s*=\s*(\[.*?\]);", html, re.S)
    if not m:
        raise ErrorGaleria("no se encontró el mapa de almacenamiento")
    return {e["storageId"]: e for e in json.loads(m.group(1))}


def _ruta_de_cuenta(cuenta):
    return f"{cuenta // 1000}/{cuenta}"


def _ruta_de_proyecto(proyecto):
    alto = proyecto // 1_000_000
    medio = proyecto // 1000 - alto * 1000
    return f"{alto}/{medio}/{proyecto}"


def abrir(galeria):
    """Lee la portada de la galería y devuelve con qué trabajar después."""
    base = galeria.rstrip("/")
    html = _traer(base + "/portfolio", "el portafolio").decode("utf-8", "replace")
    par = _parametros(html, "el portafolio")
    return {"base": base, "parametros": par, "almacenamientos": _almacenamientos(html)}


def listar_carpetas(galeria):
    """Las carpetas de la galería, en el orden en que las muestra el sitio."""
    sesion = abrir(galeria) if isinstance(galeria, str) else galeria
    par, mapa = sesion["parametros"], sesion["almacenamientos"]

    cdn = mapa[par["accountStorageId"]]["cdnDomain"]
    url = (f"{cdn}/pictures/accountdata/{_ruta_de_cuenta(par['accountId'])}"
           f"/client/{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")
    datos = json.loads(_traer(url, "la lista de carpetas").decode("utf-8", "replace"))

    try:
        proyectos = datos[1][3]
    except (IndexError, TypeError) as e:
        raise ErrorGaleria("la lista de carpetas no tiene la forma esperada") from e

    carpetas = []
    for entrada in proyectos:
        ficha = entrada[1]
        carpetas.append({"id": ficha[0], "nombre": ficha[1], "ruta": ficha[2]})
    return carpetas


def _datos_de_carpeta(sesion, carpeta):
    """El CDN y la ruta donde viven los datos de una carpeta."""
    base = sesion["base"]
    html = _traer(f"{base}/-{carpeta['ruta']}",
                  f"la carpeta «{carpeta['nombre']}»").decode("utf-8", "replace")
    par = _parametros(html, f"la carpeta «{carpeta['nombre']}»")
    for clave in ("projectId", "projectStorageId", "projectPathToken"):
        if clave not in par:
            raise ErrorGaleria(
                f"la carpeta «{carpeta['nombre']}» no trae {clave}. "
                "Puede que esté protegida con código de acceso.")
    almacen = sesion["almacenamientos"].get(par["projectStorageId"])
    if not almacen:
        raise ErrorGaleria(f"almacenamiento {par['projectStorageId']} desconocido")
    ruta = (f"{almacen['cdnDomain']}/pictures/{_ruta_de_proyecto(par['projectId'])}"
            f"/{par['projectPathToken']}")
    return ruta


def listar_fotos(galeria, carpeta, tamano="midres"):
    """Las fotos de una carpeta, con la dirección de cada una.

    `midres` es el tamaño más grande que la galería sirve sin pasar por su
    propio flujo de descarga, y alcanza tanto para que Claude vea qué hay en
    la foto como para maquetar. La resolución completa se baja desde
    Pic-Time, y para eso cada foto trae la dirección de su carpeta.
    """
    sesion = abrir(galeria) if isinstance(galeria, str) else galeria
    ruta = _datos_de_carpeta(sesion, carpeta)

    crudo = _traer(f"{ruta}/gallery.json.txt", f"las fotos de «{carpeta['nombre']}»")
    listado = json.loads(crudo.decode("utf-8", "replace"))
    minimo = listado.get("minId")
    if minimo is None:
        raise ErrorGaleria(f"«{carpeta['nombre']}»: el listado no trae minId")

    fotos, vistas = [], set()
    for escena in listado.get("scenes") or []:
        numeros = (escena or {}).get("photos") or []
        # Se recorre de cinco en cinco: el primero de cada ficha es el que
        # identifica la foto. Si la lista no divide exacto, se ignora la cola
        # en vez de inventar una foto con datos a medias.
        for i in range(0, len(numeros) - CAMPOS_POR_FOTO + 1, CAMPOS_POR_FOTO):
            identificador = minimo + numeros[i]
            if identificador in vistas:
                continue
            vistas.add(identificador)
            fotos.append({
                "id": f"{carpeta['ruta']}/{identificador}",
                "carpeta": carpeta["nombre"],
                "foto": identificador,
                "url": f"{ruta}/{tamano}/{identificador}.jpg",
                "url_thumb": f"{ruta}/thumbres/{identificador}.jpg",
                "pagina": f"{sesion['base']}/-{carpeta['ruta']}",
            })
    return fotos


def bajar(url):
    """Los bytes de una foto y su tipo."""
    datos = _traer(url, "la foto")
    return datos, "image/jpeg"
