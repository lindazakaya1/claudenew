"""Sonda: resuelve cómo arma Pic-Time la dirección del JSON del portafolio.

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

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


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


def contexto(codigo, aguja, antes=1800, despues=400, maximo=2):
    """Trozos de código alrededor de una palabra, por posición, no por regex.

    Buscar por índice en vez de con una expresión regular evita que el motor
    se atragante con los 700 KB del script minificado.
    """
    salidas, desde, encontrados = [], 0, 0
    while encontrados < maximo:
        i = codigo.find(aguja, desde)
        if i < 0:
            break
        salidas.append(codigo[max(0, i - antes): i + despues])
        desde = i + len(aguja)
        encontrados += 1
    return salidas


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")

    parametros = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    propio = mapa[parametros["accountStorageId"]]

    titulo("Datos de la cuenta")
    for clave in ("accountStorageId", "accountPathToken", "portfolioId", "portfolioTS", "storeId"):
        print("  " + clave + " = " + repr(parametros.get(clave)))
    print("  cdnDomain  = " + propio["cdnDomain"])
    print("  dataDomain = " + propio["dataDomain"])

    guion = re.search(r'src="([^"]+artgallery_base[^"]*)"', pagina).group(1)
    _, _, datos = traer(guion)
    codigo = datos.decode("utf-8", "replace")
    print("  artgallery_base.js: " + str(len(codigo)) + " caracteres")

    titulo("Definición de ma() — convierte el id de cuenta en carpeta")
    for aguja in ("function ma(", "ma=function(", "function ma (", 'ma(b,"account")'):
        for trozo in contexto(codigo, aguja, antes=60, despues=700, maximo=1):
            print("\n  >> " + " ".join(trozo.split()))

    titulo("Probando la dirección del portafolio")
    cdn = propio["cdnDomain"]
    cuenta = parametros["accountId"] if "accountId" in parametros else 518023
    pid = parametros["portfolioId"]
    ts = parametros["portfolioTS"]

    def base36(n):
        alfabeto = "0123456789abcdefghijklmnopqrstuvwxyz"
        s = ""
        while n:
            n, resto = divmod(n, 36)
            s = alfabeto[resto] + s
        return s or "0"

    candidatos = [
        str(cuenta),
        "a" + str(cuenta),
        base36(cuenta),
        "a" + base36(cuenta),
        f"{cuenta % 100}/{cuenta}",
        f"{cuenta % 1000}/{cuenta}",
        f"{str(cuenta)[:3]}/{cuenta}",
        f"{str(cuenta)[-2:]}/{cuenta}",
        f"account{cuenta}",
        f"{cuenta}/account",
    ]
    for seg in candidatos:
        url = f"{cdn}/pictures/accountdata/{seg}/client/{pid}/portfolio.json.txt?ts={ts}"
        try:
            estado, cab, datos = traer(url)
        except urllib.error.HTTPError as e:
            print(f"  {e.code}  .../accountdata/{seg}/...")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"  ERR  {seg}: {e}")
            continue
        print(f"\n  ¡ENCONTRADA!  {estado}  {url}")
        texto = datos.decode("utf-8", "replace")
        print(f"  {len(datos)} bytes  [{cab.get('Content-Type')}]")
        try:
            portafolio = json.loads(texto)
            print("  claves: " + ", ".join(list(portafolio)[:20]))
            proyectos = portafolio.get("projects", [])
            print(f"\n  {len(proyectos)} proyecto(s):")
            for pr in proyectos:
                print("    " + json.dumps(pr, ensure_ascii=False)[:300])
        except Exception as e:  # noqa: BLE001
            print("  no es JSON: " + texto[:400])
        return
    print("\n  Ninguna funcionó.")


if __name__ == "__main__":
    main()
