"""Sonda: lista las carpetas del portafolio y busca las fotos de una de ellas."""

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


def parametros_de(pagina):
    return json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))


def troceado(numero):
    """Pic-Time usa los tres primeros dígitos del id como carpeta."""
    return f"{str(numero)[:3]}/{numero}"


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = parametros_de(pagina)
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    cdn_cuenta = mapa[par["accountStorageId"]]["cdnDomain"]

    url = (f"{cdn_cuenta}/pictures/accountdata/{troceado(par['accountId'])}/client/"
           f"{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")
    _, _, datos = traer(url)
    portafolio = json.loads(datos.decode("utf-8", "replace"))
    proyectos = portafolio[1][3]

    titulo(f"Las {len(proyectos)} carpetas de la galería")
    for i, p in enumerate(proyectos):
        c = p[1]
        print(f"  {i:>3}. {c[0]}  {c[1]}   ->  {c[2]}")

    # Se toma una carpeta de las juveniles para ver cómo se piden sus fotos.
    # Su página no trae initParams: es otro tipo de página y usa otras variables.
    muestra = next(p[1] for p in proyectos if "Juveniles" in p[1][1])
    titulo(f"Página de la carpeta «{muestra[1]}»  ->  /{muestra[2]}")
    _, _, cuerpo2 = traer(f"{base}/{muestra[2]}")
    pagina2 = cuerpo2.decode("utf-8", "replace")
    print(f"  {len(pagina2)} caracteres")

    print("\n  Variables declaradas en la página:")
    for m in re.finditer(r"\b(?:var|const|let)\s+(_?[A-Za-z_$][\w$]*)\s*=\s*([^;\n]{0,400})", pagina2):
        nombre, valor = m.group(1), m.group(2).strip()
        if len(valor) > 20 or valor[:1] in "[{\"'":
            print(f"    {nombre} = {valor[:320]}")

    print("\n  Números largos que podrían ser el id del proyecto:")
    print("    " + ", ".join(sorted(set(re.findall(r"\b5\d{7}\b", pagina2)))[:15]))

    print("\n  Rutas de datos que aparecen:")
    for r in sorted(set(re.findall(r"/pictures/[a-z]+data/[\w/]+", pagina2)))[:10]:
        print("    " + r)


if __name__ == "__main__":
    main()
