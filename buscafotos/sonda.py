"""Sonda: encuentra por qué dirección se piden las fotos de una carpeta.

No descarga fotos. Es una herramienta de investigación, temporal.
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


def troceado(numero):
    """Pic-Time usa los tres primeros dígitos del id como carpeta."""
    return f"{str(numero)[:3]}/{numero}"


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    cdn_cuenta = mapa[par["accountStorageId"]]["cdnDomain"]

    url = (f"{cdn_cuenta}/pictures/accountdata/{troceado(par['accountId'])}/client/"
           f"{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")
    _, _, datos = traer(url)
    proyectos = json.loads(datos.decode("utf-8", "replace"))[1][3]

    juveniles = [p[1] for p in proyectos if "Juveniles" in p[1][1]]
    print(f"{len(proyectos)} carpetas en total, {len(juveniles)} juveniles")

    muestra = juveniles[0]
    ruta = muestra[2]
    titulo(f"Buscando la pagina de «{muestra[1]}»  (id {muestra[0]})")

    formas = [
        f"/{ruta}",
        f"/-{ruta}",
        f"/client/{ruta}",
        f"/art/{ruta}",
        f"/-_projects_{muestra[0]}",
        f"/client/{muestra[0]}",
        f"/gallery/{ruta}",
    ]
    buena = None
    for forma in formas:
        try:
            estado, _, c = traer(base + forma)
        except urllib.error.HTTPError as e:
            print(f"  {e.code:>3}  {forma}")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"  ERR  {forma}: {e}")
            continue
        html = c.decode("utf-8", "replace")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        nombre_pagina = m.group(1).strip()[:50] if m else "(sin titulo)"
        marca = "   <== ESTA" if len(html) > 5000 else ""
        print(f"  {estado:>3}  {forma:<42} {len(html):>7} car.  {nombre_pagina}{marca}")
        if len(html) > 5000 and buena is None:
            buena = (forma, html)

    if not buena:
        titulo("Ninguna forma dio una pagina real")
        print("  Respuesta de la primera, para ver que dice:")
        _, _, c = traer(base + formas[0])
        print(c.decode("utf-8", "replace")[:1500])
        return

    forma, html = buena
    titulo(f"Variables de {forma}")
    for m in re.finditer(r"\b(?:var|const|let)\s+(_?[A-Za-z_$][\w$]*)\s*=\s*([^;\n]{0,500})", html):
        nombre, valor = m.group(1), m.group(2).strip()
        if len(valor) > 15 or valor[:1] in "[{":
            print(f"  {nombre} = {valor[:420]}")


if __name__ == "__main__":
    main()
