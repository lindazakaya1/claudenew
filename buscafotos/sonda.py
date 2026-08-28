"""Sonda: arma la dirección del JSON del portafolio y lo baja.

No descarga fotos. Sirve para escribir el lector de la galería.
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


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")

    parametros = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    propio = mapa[parametros["accountStorageId"]]
    cdn = propio["cdnDomain"]
    datos_dom = propio["dataDomain"]
    token = parametros["accountPathToken"]
    pid = parametros["portfolioId"]
    ts = parametros["portfolioTS"]
    print(f"cdn={cdn}\ntoken={token}\nportfolioId={pid}\nts={ts}")

    titulo("Cómo se arma la ruta de la cuenta (accountdata)")
    guion = re.search(r'src="([^"]+artgallery_base[^"]*)"', pagina).group(1)
    _, _, datos = traer(guion)
    codigo = datos.decode("utf-8", "replace")
    vistos = set()
    for c in re.finditer(r".{170}accountdata.{170}", codigo):
        trozo = " ".join(c.group(0).split())
        if trozo in vistos:
            continue
        vistos.add(trozo)
        print("  " + trozo)
        if len(vistos) >= 6:
            break

    titulo("Probando direcciones del portafolio")
    bases = []
    for dominio in (cdn, datos_dom):
        for carpeta in ("accountdata", "accountdatapublic", "accounts"):
            for sufijo in ("", "pub", "/pub", "public"):
                bases.append(f"{dominio}/pictures/{carpeta}/{token}{sufijo}")
    encontrada = None
    for b in bases:
        url = f"{b}/client/{pid}/portfolio.json.txt?ts={ts}"
        try:
            estado, cabeceras, cuerpo = traer(url)
        except urllib.error.HTTPError as e:
            continue
        except Exception:  # noqa: BLE001
            continue
        print(f"\n¡ENCONTRADA!  {estado}  {url}")
        print(f"  [{cabeceras.get('Content-Type')}] {len(cuerpo)} bytes")
        encontrada = cuerpo
        break

    if encontrada is None:
        print("Ninguna funcionó. Bases probadas:")
        for b in bases:
            print("  " + b)
        return

    titulo("Contenido del portafolio")
    portafolio = json.loads(encontrada.decode("utf-8", "replace"))
    print("claves: " + ", ".join(portafolio.keys()))
    proyectos = portafolio.get("projects", [])
    print(f"\n{len(proyectos)} proyecto(s):")
    for p in proyectos:
        print("  " + json.dumps(p, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
