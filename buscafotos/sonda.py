"""Sonda: lista las carpetas del portafolio y busca las fotos de una de ellas."""

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


def parametros_de(pagina):
    return json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))


def troceado(numero):
    """Pic-Time usa los tres primeros dígitos del id como carpeta."""
    return f"{str(numero)[:3]}/{numero}"


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = parametros_de(pagina)
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    cdn_cuenta = mapa[par["accountStorageId"]]["cdnDomain"]

    url = (f"{cdn_cuenta}/pictures/accountdata/{troceado(par['accountId'])}/client/"
           f"{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")
    _, _, datos = traer(url)
    portafolio = json.loads(datos.decode("utf-8", "replace"))
    proyectos = portafolio[1][3]

    titulo(f"Las {len(proyectos)} carpetas de la galería")
    for i, p in enumerate(proyectos):
        c = p[1]
        print(f"  {i:>3}. {c[0]}  {c[1]}   ->  {c[2]}")

    # Se toma una carpeta para descubrir cómo se piden sus fotos.
    muestra = proyectos[0][1]
    titulo(f"Página de la carpeta «{muestra[1]}»")
    _, _, cuerpo2 = traer(f"{base}/{muestra[2]}")
    pagina2 = cuerpo2.decode("utf-8", "replace")
    par2 = parametros_de(pagina2)
    for k, v in par2.items():
        if k != "hostingInfo" and not isinstance(v, (dict, list)):
            print(f"  {k} = {v!r}")

    titulo("Probando la dirección de las fotos")
    pid = par2.get("projectId") or muestra[0]
    alm = par2.get("projectStorageId", par2.get("storageId", par["accountStorageId"]))
    token = par2.get("projectPathToken", par2.get("pathToken", ""))
    ts = par2.get("galleryTS", par2.get("timeStamp", par2.get("projectTS", "")))
    cdn_proy = mapa.get(alm, mapa[par["accountStorageId"]])["cdnDomain"]
    print(f"  projectId={pid} storageId={alm} pathToken={token!r} ts={ts!r}")

    rutas = [
        f"/pictures/projectdata/{troceado(pid)}",
        f"/pictures/projectdata/{troceado(pid)}/{token}" if token else None,
        f"/pictures/projects/{troceado(pid)}",
    ]
    for ruta in filter(None, rutas):
        for nombre in ("gallery.json.txt", "publicphotos.json.txt"):
            u = f"{cdn_proy}{ruta}/{nombre}" + (f"?ts={ts}" if ts else "")
            try:
                estado, cab, d = traer(u)
            except urllib.error.HTTPError as e:
                print(f"  {e.code}  {ruta}/{nombre}")
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  ERR  {ruta}/{nombre}: {e}")
                continue
            print(f"\n  ¡ENCONTRADA!  {estado}  {u}")
            print(f"  {len(d)} bytes  [{cab.get('Content-Type')}]")
            print("  " + d.decode("utf-8", "replace")[:1200])
            return
    print("\n  Ninguna funcionó.")


if __name__ == "__main__":
    main()
