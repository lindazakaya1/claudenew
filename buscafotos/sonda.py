"""Sonda: confirma cuántos campos ocupa cada foto en el listado.

La lista `photos` de cada escena son fichas seguidas, no identificadores
sueltos. El primer campo de cada ficha es la diferencia contra `minId`.
Esta sonda prueba varios anchos de ficha y se queda con el que haga que
todas las miniaturas bajen.
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


def traer(url, solo_estado=False):
    if url.startswith("//"):
        url = "https:" + url
    url = urllib.parse.quote(url, safe=":/?&=%#+.,~_-")
    pedido = urllib.request.Request(url, method="HEAD" if solo_estado else "GET")
    pedido.add_header("User-Agent", UA)
    pedido.add_header("Accept", "*/*")
    with urllib.request.urlopen(pedido, timeout=60) as resp:
        if solo_estado:
            return resp.status, dict(resp.headers), b""
        crudo = resp.read()
        cod = resp.headers.get("Content-Encoding", "")
        if cod == "gzip":
            crudo = gzip.GzipFile(fileobj=io.BytesIO(crudo)).read()
        elif cod == "deflate":
            crudo = zlib.decompress(crudo, -zlib.MAX_WBITS)
        return resp.status, dict(resp.headers), crudo


def titulo(t):
    print("\n" + "=" * 62 + "\n" + t + "\n" + "=" * 62, flush=True)


def baja(url):
    try:
        estado, _, _ = traer(url, solo_estado=True)
        return estado == 200
    except Exception:  # noqa: BLE001
        return False


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

    _, _, c = traer(f"{base}/-{carpeta[2]}")
    par2 = json.loads(re.search(r"initParams = (\{.*?\});", c.decode("utf-8", "replace"), re.S).group(1))
    pid, token = par2["projectId"], par2["projectPathToken"]
    cdn = mapa[par2["projectStorageId"]]["cdnDomain"]
    alto = pid // 1_000_000
    medio = pid // 1000 - alto * 1000
    ruta = f"{cdn}/pictures/{alto}/{medio}/{pid}/{token}"

    _, _, d = traer(f"{ruta}/gallery.json.txt")
    g = json.loads(d.decode("utf-8", "replace"))
    minimo = g["minId"]
    escenas = [e for e in g.get("scenes", []) if e.get("photos")]

    titulo(f"«{carpeta[1]}» — {len(escenas)} escena(s)")
    for e in escenas:
        print(f"  {e.get('name') or '(sin nombre)'}: {len(e['photos'])} números")

    titulo("Probando anchos de ficha")
    fotos = escenas[0]["photos"]
    mejor = None
    for ancho in (4, 5, 6, 7, 8, 1):
        if len(fotos) % ancho:
            print(f"  ancho {ancho}: no divide ({len(fotos)} números) — descartado")
            continue
        ids = [minimo + fotos[i] for i in range(0, len(fotos), ancho)]
        # Se prueban cinco repartidas a lo largo de la lista, no las primeras:
        # un ancho equivocado suele acertar al principio y fallar más adelante.
        paso = max(1, len(ids) // 5)
        muestras = ids[::paso][:5]
        aciertos = sum(1 for x in muestras if baja(f"{ruta}/thumbres/{x}.jpg"))
        print(f"  ancho {ancho}: {len(ids)} fotos, {aciertos}/{len(muestras)} miniaturas OK")
        if aciertos == len(muestras) and mejor is None:
            mejor = (ancho, ids)

    if not mejor:
        titulo("Ningún ancho funcionó")
        print("  primeros 30 números: " + str(fotos[:30]))
        return

    ancho, ids = mejor
    titulo(f"Ancho correcto: {ancho} campos por foto")
    print(f"  {len(ids)} fotos en esta escena")
    print("  primeros ids: " + ", ".join(str(x) for x in ids[:6]))
    total = sum(len(e["photos"]) // ancho for e in escenas)
    print(f"  total en la carpeta: {total} fotos")
    print(f"\n  Ejemplo de miniatura: {ruta}/thumbres/{ids[0]}.jpg")
    print(f"  Ejemplo de mediana:   {ruta}/midres/{ids[0]}.jpg")


if __name__ == "__main__":
    main()
