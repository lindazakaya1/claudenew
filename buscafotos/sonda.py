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
import urllib.request
import zlib

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def traer(url):
    if url.startswith("//"):
        url = "https:" + url
    pedido = urllib.request.Request(url)
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    with urllib.request.urlopen(pedido, timeout=60) as resp:
        crudo = resp.read()
        cod = resp.headers.get("Content-Encoding", "")
        if cod == "gzip":
            crudo = gzip.GzipFile(fileobj=io.BytesIO(crudo)).read()
        elif cod == "deflate":
            crudo = zlib.decompress(crudo, -zlib.MAX_WBITS)
        return resp.status, dict(resp.headers), crudo


def titulo(t):
    print("\n" + "=" * 66 + f"\n{t}\n" + "=" * 66, flush=True)


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(f"{base}/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")

    titulo("initParams")
    m = re.search(r"var initParams = (\{.*?\});", pagina, re.S)
    parametros = {}
    if m:
        parametros = json.loads(m.group(1))
        for clave, valor in parametros.items():
            if clave != "hostingInfo":
                print(f"  {clave} = {valor!r}")

    titulo("Mapa de almacenamiento")
    m = re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S)
    mapa = {}
    if m:
        for entrada in json.loads(m.group(1)):
            mapa[entrada["storageId"]] = entrada
            print(f"  {entrada['storageId']:>4}  {entrada.get('dataDomain')}  |  {entrada.get('cdnDomain')}")
    print(f"  almacenamiento de esta cuenta: {parametros.get('accountStorageId')}")

    titulo("Cómo arman las direcciones los scripts del sitio")
    guiones = re.findall(r'src="([^"]+(?:vue_client|artgallery_base|vue_fw)[^"]*)"', pagina)
    interes = re.compile(
        r"(portfolio[A-Za-z]*\s*[:=+]|pathToken|accountPathToken|/pictures/[a-z/]*|\.json|"
        r"getPortfolio|loadPortfolio|projectList|albumList)",
        re.I,
    )
    for guion in guiones:
        try:
            _, _, datos = traer(guion)
        except Exception as e:  # noqa: BLE001
            print(f"\n--- {guion.split('/')[-1]}: no se pudo bajar ({e}) ---")
            continue
        codigo = datos.decode("utf-8", "replace")
        print(f"\n--- {guion.split('/')[-1]}  ({len(codigo)} caracteres) ---")
        mostrados = 0
        for coincidencia in interes.finditer(codigo):
            trozo = codigo[max(0, coincidencia.start() - 120): coincidencia.start() + 160]
            trozo = " ".join(trozo.split())
            print(f"  …{trozo}…")
            mostrados += 1
            if mostrados >= 45:
                print("  (recortado)")
                break

    titulo("Direcciones candidatas para el JSON del portafolio")
    almacenamiento = mapa.get(parametros.get("accountStorageId"), {})
    dominio_datos = almacenamiento.get("dataDomain", "")
    dominio_cdn = almacenamiento.get("cdnDomain", "")
    token = parametros.get("accountPathToken", "")
    pid = parametros.get("portfolioId", "")
    ts = parametros.get("portfolioTS", "")
    candidatas = []
    for dominio in filter(None, [dominio_cdn, dominio_datos]):
        candidatas += [
            f"{dominio}/pictures/accounts/{token}/portfolio/{pid}.json?ts={ts}",
            f"{dominio}/pictures/accounts/{token}/portfolios/{pid}.json?ts={ts}",
            f"{dominio}/accounts/{token}/portfolio/{pid}.json?ts={ts}",
            f"{dominio}/pictures/{token}/portfolio/{pid}.json?ts={ts}",
        ]
    for url in candidatas:
        try:
            estado, cabeceras, datos = traer(url)
            print(f"\n{estado}  {url}\n  [{cabeceras.get('Content-Type')}] {len(datos)} bytes")
            print("  " + datos.decode("utf-8", "replace")[:700].replace("\n", " "))
        except urllib.error.HTTPError as e:
            print(f"{e.code}  {url}")
        except Exception as e:  # noqa: BLE001
            print(f"ERR  {url}  {e}")


if __name__ == "__main__":
    main()
