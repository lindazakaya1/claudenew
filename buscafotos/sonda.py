"""Sonda: lee cómo Pic-Time arma projectPath.

Las plantillas de foto son "[projectBaseCdnUrl][projectPath]/thumbs/[fileName]",
así que lo único que falta es projectPath. Se busca dónde la función lo
devuelve y se lee el código de antes, que es la misma técnica que sirvió
para resolver la ruta de la cuenta.
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


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    guion = re.search(r'src="([^"]+artgallery_base[^"]*)"', pagina).group(1)
    _, _, datos = traer(guion)
    codigo = datos.decode("utf-8", "replace")

    # Se busca por posición, no con expresiones regulares: el archivo pesa
    # cientos de miles de caracteres y así no hay sorpresas de coincidencia.
    titulo("Antes de donde se devuelve projectPath")
    i = codigo.find("projectPath:")
    if i < 0:
        print("  (projectPath: no aparece)")
    else:
        print("  " + " ".join(codigo[max(0, i - 2000): i + 300].split()))

    titulo("Rutas literales que contienen 'project'")
    vistos = set()
    for m in re.finditer(r"/pictures/[A-Za-z]*project[A-Za-z]*", codigo):
        s = m.group(0)
        if s not in vistos:
            vistos.add(s)
            print("  " + s)

    titulo("Plantillas con backtick que mencionan pictures")
    vistos = set()
    for m in re.finditer(r"`/pictures/[^`]{0,90}`", codigo):
        s = m.group(0)
        if s not in vistos:
            vistos.add(s)
            print("  " + s)
        if len(vistos) >= 14:
            break


if __name__ == "__main__":
    main()
