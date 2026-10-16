"""Sonda final: abre una carpeta de la galería con un navegador de verdad
y anota todas las direcciones que pide.

Las sondas anteriores dedujeron las direcciones leyendo el código del sitio,
y así se resolvieron el portafolio y las carpetas. Para las fotos esa vía se
agotó: la ruta sale de un campo (`relativePath`) que no se calcula, viene
guardado. En vez de seguir adivinando, aquí se deja que el propio JavaScript
de Pic-Time pida lo que tenga que pedir y se mira qué pidió.
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
    print("\n" + "=" * 62 + "\n" + t + "\n" + "=" * 62, flush=True)


def carpeta_juvenil(base):
    """La ruta de la primera carpeta de las Macabeadas Juveniles."""
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
    return next(p[1] for p in proyectos if "Juveniles" in p[1][1])


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    carpeta = carpeta_juvenil(base)
    destino = f"{base}/-{carpeta[2]}"
    titulo(f"Abriendo «{carpeta[1]}» con el navegador")
    print("  " + destino)

    from playwright.sync_api import sync_playwright

    pedidos = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(args=["--no-sandbox"])
        pestana = navegador.new_page(user_agent=UA)
        pestana.on("request", lambda r: pedidos.append(r.url))
        pestana.goto(destino, wait_until="networkidle", timeout=90000)
        # Un empujón de scroll: las galerías cargan las miniaturas al verlas.
        for _ in range(3):
            pestana.mouse.wheel(0, 3000)
            pestana.wait_for_timeout(1500)
        navegador.close()

    print(f"\n  {len(pedidos)} peticiones en total")

    def unicos(filtro, tope):
        vistos = []
        for u in pedidos:
            if filtro(u) and u not in vistos:
                vistos.append(u)
            if len(vistos) >= tope:
                break
        return vistos

    titulo("Datos de la galería (.json / .txt)")
    for u in unicos(lambda u: (".json" in u or ".txt" in u) and "scripts" not in u, 12):
        print("  " + u[:220])

    titulo("Fotos (thumbs / midres / lowres / smallres)")
    for u in unicos(lambda u: any(r in u for r in ("/thumbs/", "/midres/", "/lowres/", "/smallres/", "/thumbres/")), 8):
        print("  " + u[:220])

    titulo("Cualquier imagen de un CDN")
    for u in unicos(lambda u: re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I) and "scripts" not in u and "skins" not in u, 10):
        print("  " + u[:220])


if __name__ == "__main__":
    main()
