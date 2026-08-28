"""Sonda: averigua de dónde saca la galería de Pic-Time sus datos.

No descarga fotos. Imprime solo lo justo para poder escribir el lector de la
galería, porque el registro de GitHub Actions tiene un tope de tamaño.
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

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def traer(url):
    if url.startswith("//"):
        url = "https:" + url
    # Las direcciones de los scripts traen espacios en el parámetro Ts
    # (?Ts=8/26/2026 2:39:41 PM) y urllib se niega a pedirlas tal cual.
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


PATRONES = {
    "galleryDTO": r""".{60}galleryDTO.{200}""",
    "baseCdnUrl": r""".{80}[Bb]aseCdnUrl.{160}""",
    "publicUrl": r""".{80}publicUrl["'\]:,].{140}""",
    "plantilla portafolio": r"""[a-zA-Z]+:\s*[^,;]{0,40}["'`][^"'`]{0,120}portfolio[^"'`]{0,120}["'`]""",
    "getProjectUrls": r"""getProjectUrls\s*[=:]\s*function[^)]{0,80}\)\{.{0,400}""",
    "getUrls": r"""getUrls\s*[=:].{0,300}""",
}


def revisar_script(url):
    corto = url.split("/")[-1].split("?")[0]
    try:
        _, _, datos = traer(url)
    except Exception as e:  # noqa: BLE001
        print("\n--- " + corto + ": no bajó (" + str(e) + ") ---")
        return
    codigo = datos.decode("utf-8", "replace")
    print("\n--- " + corto + "  (" + str(len(codigo)) + " caracteres) ---")
    for nombre, patron in PATRONES.items():
        vistos = set()
        for coincidencia in re.finditer(patron, codigo):
            trozo = " ".join(coincidencia.group(0).split())
            if trozo in vistos:
                continue
            vistos.add(trozo)
            print("  [" + nombre + "] " + trozo[:200])
            if len(vistos) >= 8:
                break


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")

    titulo("initParams")
    parametros = {}
    m = re.search(r"var initParams = (\{.*?\});", pagina, re.S)
    if m:
        parametros = json.loads(m.group(1))
        for clave, valor in parametros.items():
            if clave != "hostingInfo":
                print("  " + clave + " = " + repr(valor))

    titulo("Almacenamiento de esta cuenta")
    mapa = {}
    m = re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S)
    if m:
        for entrada in json.loads(m.group(1)):
            mapa[entrada["storageId"]] = entrada
    propio = mapa.get(parametros.get("accountStorageId"), {})
    print("  dataDomain: " + str(propio.get("dataDomain")))
    print("  cdnDomain : " + str(propio.get("cdnDomain")))

    titulo("Enlaces de la página")
    for enlace in sorted(set(re.findall(r'href="([^"#]+)"', pagina))):
        if not enlace.endswith((".css", ".ico", ".woff", ".woff2")):
            print("  " + enlace)

    titulo("Rutas de datos dentro de los scripts del sitio")
    guiones = re.findall(
        r'src="([^"]+(?:vue_client|artgallery_base|serverServices)[^"]*)"', pagina
    )
    for guion in guiones:
        revisar_script(guion)


if __name__ == "__main__":
    main()
