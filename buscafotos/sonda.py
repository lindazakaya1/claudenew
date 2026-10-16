"""Sonda: lee el listado de fotos de una carpeta y comprueba que bajan.

La ruta de un proyecto quedó resuelta observando qué pide el navegador:

    /pictures/{id//1e6}/{(id//1e3)%1e3}/{id}/{pathToken}

sin ninguna carpeta intermedia. Dentro están gallery.json.txt con el
listado y thumbres/ midres/ lowres/ con las fotos.
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
    print("\n" + "=" * 62 + "\n" + t + "\n" + "=" * 62, flush=True)


def ruta_de_proyecto(identificador, token):
    alto = identificador // 1_000_000
    medio = identificador // 1000 - alto * 1000
    return f"/pictures/{alto}/{medio}/{identificador}/{token}"


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    cuenta = par["accountId"]
    url = (f"{mapa[par['accountStorageId']]['cdnDomain']}/pictures/accountdata/"
           f"{cuenta // 1000}/{cuenta}/client/{par['portfolioId']}"
           f"/portfolio.json.txt?ts={par['portfolioTS']}")
    _, _, datos = traer(url)
    proyectos = json.loads(datos.decode("utf-8", "replace"))[1][3]
    carpeta = next(p[1] for p in proyectos if "Juveniles" in p[1][1])

    titulo(f"Carpeta «{carpeta[1]}»")
    _, _, c = traer(f"{base}/-{carpeta[2]}")
    par2 = json.loads(re.search(r"initParams = (\{.*?\});", c.decode("utf-8", "replace"), re.S).group(1))
    pid, alm = par2["projectId"], par2["projectStorageId"]
    token = par2["projectPathToken"]
    cdn = mapa[alm]["cdnDomain"]
    ruta = ruta_de_proyecto(pid, token)
    print(f"  {cdn}{ruta}")

    estado, cab, d = traer(f"{cdn}{ruta}/gallery.json.txt")
    print(f"  gallery.json.txt -> {estado}, {len(d)} bytes")
    galeria = json.loads(d.decode("utf-8", "replace"))

    titulo("Forma del listado")

    def forma(nodo, nombre="raiz", nivel=0, tope=6):
        sangria = "  " * nivel
        if isinstance(nodo, list):
            print(f"  {sangria}{nombre}: lista de {len(nodo)}")
            if nivel < tope:
                for i, hijo in enumerate(nodo[:3]):
                    forma(hijo, f"[{i}]", nivel + 1, tope)
        elif isinstance(nodo, dict):
            print(f"  {sangria}{nombre}: objeto -> " + ", ".join(list(nodo)[:10]))
        elif isinstance(nodo, str) and nodo:
            print(f"  {sangria}{nombre}: TEXTO {nodo[:50]!r}")
        elif isinstance(nodo, (int, float)) and nodo:
            print(f"  {sangria}{nombre}: {nodo}")

    forma(galeria)

    # Los nombres de archivo de las fotos son números largos; se recogen
    # todos los que aparezcan en el listado y se comprueba que bajan.
    titulo("Identificadores de foto encontrados")
    encontrados = []

    def recoger(nodo):
        if isinstance(nodo, list):
            for hijo in nodo:
                recoger(hijo)
        elif isinstance(nodo, int) and 10_000_000_000 <= nodo <= 99_999_999_999:
            encontrados.append(nodo)

    recoger(galeria)
    unicos = list(dict.fromkeys(encontrados))
    print(f"  {len(unicos)} identificadores (de {len(encontrados)} apariciones)")
    print("  primeros: " + ", ".join(str(x) for x in unicos[:8]))

    titulo("Comprobando que las fotos bajan")
    for ident in unicos[:3]:
        for tamano in ("thumbres", "midres"):
            u = f"{cdn}{ruta}/{tamano}/{ident}.jpg"
            try:
                estado, cab, d = traer(u)
                print(f"  {estado}  {tamano}/{ident}.jpg  {len(d)} bytes  [{cab.get('Content-Type')}]")
            except urllib.error.HTTPError as e:
                print(f"  {e.code}  {tamano}/{ident}.jpg")


if __name__ == "__main__":
    main()
