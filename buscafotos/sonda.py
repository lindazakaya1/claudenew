"""Sonda: encuentra cómo Pic-Time trocea el id de un proyecto en una ruta.

Imprime poco a propósito: el registro de GitHub Actions se recorta por el
final y lo importante tiene que caber.
"""

import gzip
import io
import json
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


def alrededor(codigo, aguja, antes, despues, maximo=2):
    salidas, desde = [], 0
    while len(salidas) < maximo:
        i = codigo.find(aguja, desde)
        if i < 0:
            break
        salidas.append(" ".join(codigo[max(0, i - antes): i + despues].split()))
        desde = i + len(aguja)
    return salidas


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    guion = re.search(r'src="([^"]+artgallery_base[^"]*)"', pagina).group(1)
    _, _, datos = traer(guion)
    codigo = datos.decode("utf-8", "replace")

    titulo("Dónde se llama con 'project'")
    for t in alrededor(codigo, '"project")', 260, 60, maximo=3):
        print("  >> " + t)

    titulo("Dónde se llama con 'account'")
    for t in alrededor(codigo, '"account")', 200, 60, maximo=1):
        print("  >> " + t)

    # El nombre de la función sale de la llamada: ...ma(b,"account")...
    m = re.search(r"(\w+)\(\w+,\s*\"account\"\)", codigo)
    nombre = m.group(1) if m else None
    titulo(f"Definición de la función troceadora: {nombre}")
    if nombre:
        for aguja in (f"function {nombre}(", f"{nombre}=function("):
            for t in alrededor(codigo, aguja, 0, 700, maximo=1):
                print("  >> " + t)

    titulo("Rutas con projectdata en el código")
    vistos = set()
    for m in re.finditer(r"[\"'`][^\"'`]{0,50}project(?:data|s)/[^\"'`]{0,90}[\"'`]", codigo):
        t = m.group(0)
        if t not in vistos:
            vistos.add(t)
            print("  " + t)
        if len(vistos) >= 12:
            break


if __name__ == "__main__":
    main()
