"""Sonda: lee la función que arma las rutas de un proyecto en Pic-Time.

Ya está resuelto el troceo de los identificadores (ver `troceado`), pero la
carpeta base de los proyectos no es `projectdata`. Esta sonda saca el cuerpo
de getProjectUrls y las plantillas de las fotos, que es donde está escrito.
"""

import gzip
import io
import re
import sys
import urllib.parse
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def traer(url):
    if url.startswith("//"):
        url = "https:" + url
    url = urllib.parse.quote(url, safe=":/?&=%#+.,~_-")
    pedido = urllib.request.Request(url)
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    with urllib.request.urlopen(pedido, timeout=90) as resp:
        crudo = resp.read()
        cod = resp.headers.get("Content-Encoding", "")
        if cod == "gzip":
            crudo = gzip.GzipFile(fileobj=io.BytesIO(crudo)).read()
        elif cod == "deflate":
            crudo = zlib.decompress(crudo, -zlib.MAX_WBITS)
        return resp.status, dict(resp.headers), crudo


def titulo(t):
    print("\n" + "=" * 60 + "\n" + t + "\n" + "=" * 60, flush=True)


def desde(codigo, aguja, largo):
    i = codigo.find(aguja)
    return " ".join(codigo[i:i + largo].split()) if i >= 0 else None


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    guion = re.search(r'src="([^"]+artgallery_base[^"]*)"', pagina).group(1)
    _, _, datos = traer(guion)
    codigo = datos.decode("utf-8", "replace")

    titulo("getProjectUrls: cómo arma projectPath y publicPath")
    t = desde(codigo, 'galleryTS=="notready"', 2600)
    print("  " + (t or "(no encontrado)"))

    titulo("Plantillas de las fotos")
    vistos = set()
    for m in re.finditer(r"\w*ResolutionPhoto[\"']?\s*:\s*[\"'`][^\"'`]{0,150}[\"'`]", codigo):
        s = " ".join(m.group(0).split())
        if s not in vistos:
            vistos.add(s)
            print("  " + s)
        if len(vistos) >= 8:
            break
    if not vistos:
        for m in re.finditer(r".{80}ResolutionPhoto.{170}", codigo):
            print("  " + " ".join(m.group(0).split()))
            break


if __name__ == "__main__":
    main()
