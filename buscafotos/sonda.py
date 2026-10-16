"""Sonda: descifra el listado de fotos (gallery.json.txt).

Es JSON con nombres. Guarda los números de foto como diferencias contra
`minId` para que el archivo pese menos, así que hay que sumarlos.
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
    print("\n" + "=" * 62 + "\n" + t + "\n" + "=" * 62, flush=True)


def resumir(valor, nivel=0):
    if isinstance(valor, list):
        return f"lista de {len(valor)}"
    if isinstance(valor, dict):
        return "objeto -> " + ", ".join(list(valor)[:14])
    return repr(valor)[:90]


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

    titulo(f"«{carpeta[1]}»")
    _, _, d = traer(f"{ruta}/gallery.json.txt")
    g = json.loads(d.decode("utf-8", "replace"))

    print("  Claves del listado:")
    for clave, valor in g.items():
        print(f"    {clave} = {resumir(valor)}")

    titulo("La primera escena")
    escenas = g.get("scenes") or []
    if escenas:
        for clave, valor in (escenas[0] or {}).items():
            print(f"  {clave} = {resumir(valor)}")

    titulo("Listas de números dentro de las escenas")
    minimo = g.get("minId", 0)
    print(f"  minId = {minimo}")
    for i, escena in enumerate(escenas[:2]):
        for clave, valor in (escena or {}).items():
            if isinstance(valor, list) and valor and all(isinstance(x, int) for x in valor):
                print(f"  escena[{i}].{clave}: {len(valor)} números, "
                      f"primeros {valor[:5]}  ->  sumando minId: "
                      f"{[minimo + x for x in valor[:3]]}")

    titulo("Comprobando que las fotos bajan")
    probados = 0
    for escena in escenas:
        for clave, valor in (escena or {}).items():
            if not (isinstance(valor, list) and valor and all(isinstance(x, int) for x in valor)):
                continue
            for x in valor[:2]:
                for candidato in (minimo + x, x):
                    u = f"{ruta}/thumbres/{candidato}.jpg"
                    try:
                        estado, cab, datos_f = traer(u)
                        print(f"  OK {estado}  thumbres/{candidato}.jpg  "
                              f"{len(datos_f)} bytes  [{cab.get('Content-Type')}]  (de {clave})")
                    except urllib.error.HTTPError as e:
                        print(f"  {e.code}  thumbres/{candidato}.jpg  (de {clave})")
                    probados += 1
                    if probados >= 10:
                        return
        if probados >= 10:
            break


if __name__ == "__main__":
    main()
