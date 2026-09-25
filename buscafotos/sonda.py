"""Sonda: lee el portafolio de Pic-Time y muestra su estructura.

Ya se sabe cómo se arma la dirección; falta entender el formato, que no es
JSON con claves sino arreglos posicionales.
"""

import gzip
import io
import json
import re
import sys
import urllib.error
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
    print("\n" + "=" * 66 + "\n" + t + "\n" + "=" * 66, flush=True)


def arbol(nodo, ruta="", profundidad=0, limite=6, salidas=None):
    """Recorre los arreglos anidados e imprime dónde vive cada dato."""
    if salidas is None:
        salidas = []
    sangria = "  " * profundidad
    if isinstance(nodo, list):
        salidas.append(f"{sangria}{ruta}: lista de {len(nodo)}")
        if profundidad < limite:
            for i, hijo in enumerate(nodo):
                arbol(hijo, f"[{i}]", profundidad + 1, limite, salidas)
    elif isinstance(nodo, dict):
        salidas.append(f"{sangria}{ruta}: objeto con {len(nodo)} claves -> "
                       + ", ".join(list(nodo)[:12]))
    elif isinstance(nodo, str) and nodo:
        salidas.append(f"{sangria}{ruta}: TEXTO {nodo[:70]!r}")
    elif isinstance(nodo, (int, float)) and nodo:
        salidas.append(f"{sangria}{ruta}: {nodo}")
    return salidas


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    cdn = mapa[par["accountStorageId"]]["cdnDomain"]

    # La ruta de la cuenta: los primeros tres dígitos del id hacen de carpeta.
    cuenta = par["accountId"]
    trozo = f"{str(cuenta)[:3]}/{cuenta}"
    url = (f"{cdn}/pictures/accountdata/{trozo}/client/"
           f"{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")

    titulo("Portafolio")
    print("  " + url)
    estado, _, datos = traer(url)
    texto = datos.decode("utf-8", "replace")
    print(f"  {estado} · {len(datos)} bytes")

    portafolio = json.loads(texto)

    titulo("Textos que contiene (nombres de carpetas y rutas)")
    def textos(nodo, ruta=""):
        if isinstance(nodo, list):
            for i, h in enumerate(nodo):
                yield from textos(h, f"{ruta}[{i}]")
        elif isinstance(nodo, dict):
            for k, v in nodo.items():
                yield from textos(v, f"{ruta}.{k}")
        elif isinstance(nodo, str) and 1 < len(nodo) < 90 and not nodo.startswith("#"):
            yield ruta, nodo
    vistos = set()
    for ruta, valor in textos(portafolio):
        if valor in vistos or valor.startswith("_PT_"):
            continue
        vistos.add(valor)
        print(f"  {ruta} = {valor!r}")
        if len(vistos) > 120:
            print("  (recortado)")
            break

    titulo("Forma del árbol")
    for linea in arbol(portafolio, "raiz", limite=5)[:90]:
        print("  " + linea)


if __name__ == "__main__":
    main()
