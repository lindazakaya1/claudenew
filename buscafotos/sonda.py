"""Sonda: mira cómo está construida la galería de Pic-Time.

No descarga fotos. Solo lee la página y reporta su estructura, para poder
escribir después el lector de la galería. Usa únicamente la librería estándar.
"""

import gzip
import io
import re
import sys
import urllib.error
import urllib.request
import zlib

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def traer(url):
    pedido = urllib.request.Request(url)
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    pedido.add_header("Accept-Language", "es-ES,es;q=0.9,en;q=0.8")
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
    print("=" * 70, flush=True)


def analizar(url):
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
    print(f"estado {estado} | {len(cuerpo)} bytes | {cabeceras.get('Content-Type')}")
    print(f"url final: {url_final}")

    titulo("Enlaces (href) de la página")
    for enlace in sorted(set(re.findall(r'href="([^"#]+)"', texto))):
        if not enlace.endswith((".css", ".ico", ".woff", ".woff2")):
            print(f"  {enlace}")

    titulo("Variables var/const con datos")
    for m in re.finditer(r"\b(?:var|const|let)\s+(_?[A-Za-z_$][\w$]*)\s*=\s*(.{0,900})", texto, re.S):
        valor = m.group(2).strip()
        if valor[:1] in "[{" or len(valor) > 120:
            print(f"\n--- {m.group(1)} ---")
            print(valor[:900])

    titulo("Bloques JSON con listas de objetos")
    vistos = set()
    for m in re.finditer(r'\[\s*\{"[^"]{2,30}":.{0,1500}', texto, re.S):
        trozo = m.group(0)
        clave = trozo[:80]
        if clave in vistos:
            continue
        vistos.add(clave)
        print(f"\n--- lista en posición {m.start()} ---")
        print(trozo[:1500])

    titulo("Imágenes referenciadas (únicas)")
    imagenes = set(re.findall(r'(?:src="|url\(\'?|")((?:https?:)?//[^"\'\s)]+\.(?:jpe?g|png|webp)[^"\'\s)]*)', texto, re.I))
    for img in sorted(imagenes)[:40]:
        print(f"  {img}")
    print(f"  ... {len(imagenes)} imágenes únicas en total")

    titulo("HTML completo")
    print(texto)
    return texto


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    analizar(f"{base}/portfolio")


if __name__ == "__main__":
    main()
