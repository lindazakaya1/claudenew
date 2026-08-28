"""Sonda: mira cómo está construida la galería de Pic-Time.

No descarga fotos. Solo lee la página y reporta su estructura, para poder
escribir después el lector de la galería. Usa únicamente la librería estándar.
"""

import gzip
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zlib

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def traer(url, cabeceras=None):
    pedido = urllib.request.Request(url)
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    pedido.add_header("Accept-Language", "es-ES,es;q=0.9,en;q=0.8")
    for clave, valor in (cabeceras or {}).items():
        pedido.add_header(clave, valor)
    with urllib.request.urlopen(pedido, timeout=45) as resp:
        crudo = resp.read()
        codificacion = resp.headers.get("Content-Encoding", "")
        if codificacion == "gzip":
            crudo = gzip.GzipFile(fileobj=io.BytesIO(crudo)).read()
        elif codificacion == "deflate":
            crudo = zlib.decompress(crudo, -zlib.MAX_WBITS)
        return resp.status, dict(resp.headers), resp.url, crudo


def titulo(seccion):
    print("\n" + "=" * 70)
    print(seccion)
    print("=" * 70)


def mirar_pagina(url):
    titulo(f"GET {url}")
    try:
        estado, cabeceras, url_final, cuerpo = traer(url)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {e.reason}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"fallo: {type(e).__name__}: {e}")
        return None

    texto = cuerpo.decode("utf-8", "replace")
    print(f"estado      : {estado}")
    print(f"url final   : {url_final}")
    print(f"content-type: {cabeceras.get('Content-Type')}")
    print(f"tamaño      : {len(cuerpo)} bytes")

    m = re.search(r"<title[^>]*>(.*?)</title>", texto, re.S | re.I)
    if m:
        print(f"title       : {m.group(1).strip()[:200]}")

    guiones = re.findall(r'<script[^>]+src="([^"]+)"', texto)
    if guiones:
        print(f"\nscripts externos ({len(guiones)}):")
        for g in guiones[:15]:
            print(f"  {g}")

    print("\nvariables globales asignadas en la página:")
    globales = sorted(set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", texto)))
    print("  " + (", ".join(globales[:40]) if globales else "(ninguna)"))

    interesantes = [
        "galleryId", "gallery_id", "projectId", "project_id", "sceneId",
        "photoId", "photos", "scenes", "collections", "albums", "portfolio",
        "cdn", "thumb", "/api/", "apiUrl", "storeId", "eventId", "slug",
    ]
    print("\npalabras clave presentes en el HTML:")
    for palabra in interesantes:
        cuantas = texto.count(palabra)
        if cuantas:
            print(f"  {palabra:<14} x{cuantas}")

    print("\nhosts que aparecen en el HTML:")
    hosts = sorted(set(re.findall(r"https?://([a-z0-9.\-]+)", texto, re.I)))
    for h in hosts[:30]:
        print(f"  {h}")

    print("\nposibles JSON incrustados (asignaciones a window.*):")
    hallados = 0
    for m in re.finditer(r"window\.([A-Za-z_$][\w$]*)\s*=\s*(\{.{0,600})", texto, re.S):
        hallados += 1
        print(f"  window.{m.group(1)} = {m.group(2)[:400]!r}")
        if hallados >= 6:
            break
    if not hallados:
        print("  (ninguna)")

    print("\nprimeros 2500 caracteres del HTML:")
    print(texto[:2500])
    return texto


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com"
    base = base.rstrip("/")

    html = mirar_pagina(f"{base}/portfolio")
    if html is None:
        mirar_pagina(base)

    titulo("Sondeo de posibles endpoints de datos")
    candidatos = [
        f"{base}/api/portfolio",
        f"{base}/api/gallery",
        f"{base}/portfolio?format=json",
        f"{base}/sitemap.xml",
        f"{base}/robots.txt",
    ]
    for url in candidatos:
        try:
            estado, cabeceras, url_final, cuerpo = traer(url)
            tipo = cabeceras.get("Content-Type", "?")
            print(f"\n{estado}  {url}  [{tipo}]  {len(cuerpo)} bytes")
            muestra = cuerpo.decode("utf-8", "replace")[:900]
            print(muestra)
        except urllib.error.HTTPError as e:
            print(f"\n{e.code}  {url}")
        except Exception as e:  # noqa: BLE001
            print(f"\nERR  {url}  {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
