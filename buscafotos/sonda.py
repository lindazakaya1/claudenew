"""Sonda: saca la lista de fotos de una carpeta de la galería.

La página de una carpeta vive en /-{ruta} y trae sus propios initParams.
De ahí salen el id del proyecto, su almacenamiento y su token, que es lo
que hace falta para pedir el JSON con las fotos.
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
    print("\n" + "=" * 66 + "\n" + t + "\n" + "=" * 66, flush=True)


def troceado(numero):
    """Pic-Time usa los tres primeros dígitos del id como carpeta."""
    return f"{str(numero)[:3]}/{numero}"


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}
    cdn_cuenta = mapa[par["accountStorageId"]]["cdnDomain"]

    url = (f"{cdn_cuenta}/pictures/accountdata/{troceado(par['accountId'])}/client/"
           f"{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")
    _, _, datos = traer(url)
    proyectos = json.loads(datos.decode("utf-8", "replace"))[1][3]
    juveniles = [p[1] for p in proyectos if "Juveniles" in p[1][1]]

    muestra = juveniles[0]
    titulo(f"Carpeta «{muestra[1]}»  ->  /-{muestra[2]}")
    _, _, c = traer(f"{base}/-{muestra[2]}")
    html = c.decode("utf-8", "replace")
    par2 = json.loads(re.search(r"initParams = (\{.*?\});", html, re.S).group(1))

    print("  Parametros de la carpeta:")
    for clave, valor in sorted(par2.items()):
        if not isinstance(valor, (dict, list)):
            print(f"    {clave} = {valor!r}")

    titulo("Probando la direccion del JSON de fotos")
    pid = (par2.get("projectId") or par2.get("baseProjectId")
           or par2.get("prjId") or muestra[0])
    alm = par2.get("projectStorageId", par2.get("storageId"))
    token = par2.get("projectPathToken", par2.get("pathToken", ""))
    marcas = [par2.get(k) for k in ("galleryTS", "projectTS", "timeStamp", "ts") if par2.get(k)]
    print(f"  projectId={pid}  storageId={alm}  pathToken={token!r}  marcas={marcas}")

    dominios = []
    if alm is not None and alm in mapa:
        dominios.append(mapa[alm]["cdnDomain"])
    dominios += [cdn_cuenta, mapa[0]["cdnDomain"]]

    rutas = [f"/pictures/projectdata/{troceado(pid)}"]
    if token:
        rutas.append(f"/pictures/projectdata/{troceado(pid)}/{token}")
    archivos = ["gallery.json.txt", "publicphotos.json.txt", "photos.json.txt"]

    for dominio in dict.fromkeys(dominios):
        for ruta in rutas:
            for archivo in archivos:
                for marca in (marcas + [None]):
                    u = f"{dominio}{ruta}/{archivo}" + (f"?ts={marca}" if marca else "")
                    try:
                        estado, cab, d = traer(u)
                    except urllib.error.HTTPError as e:
                        if e.code != 404:
                            print(f"  {e.code}  {u[:110]}")
                        continue
                    except Exception:  # noqa: BLE001
                        continue
                    print(f"\n  ENCONTRADA  {estado}  {u}")
                    print(f"  {len(d)} bytes  [{cab.get('Content-Type')}]")
                    texto = d.decode("utf-8", "replace")
                    print("\n  Primeros 1500 caracteres:")
                    print("  " + texto[:1500])
                    try:
                        datos_g = json.loads(texto)
                        if isinstance(datos_g, list):
                            print(f"\n  Estructura: lista de {len(datos_g)}")
                    except Exception:  # noqa: BLE001
                        pass
                    return
    print("\n  Ninguna funciono. Todas dieron 404.")


if __name__ == "__main__":
    main()
