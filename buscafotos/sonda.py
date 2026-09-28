"""Sonda: baja la lista de fotos de una carpeta y muestra su estructura.

Pic-Time trocea los identificadores para repartirlos en carpetas, y lo hace
distinto según de qué sean. Tomado de su propio código:

    function ma(b,d){
      var h=parseInt(b/1E6), p=parseInt(b/1E3-h*1E3);
      switch(d){
        case "account": return `${parseInt(b/1E3)}/${b}`;  // 518/518023
        default:        return `${h}/${p}/${b}`;           // 50/350/50350259
      }
    }
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
    print("\n" + "=" * 60 + "\n" + t + "\n" + "=" * 60, flush=True)


def troceado(numero, tipo="project"):
    numero = int(numero)
    if tipo == "account":
        return f"{numero // 1000}/{numero}"
    alto = numero // 1_000_000
    medio = numero // 1000 - alto * 1000
    return f"{alto}/{medio}/{numero}"


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://macabeadaspty.pic-time.com").rstrip("/")
    _, _, cuerpo = traer(base + "/portfolio")
    pagina = cuerpo.decode("utf-8", "replace")
    par = json.loads(re.search(r"var initParams = (\{.*?\});", pagina, re.S).group(1))
    mapa = {e["storageId"]: e for e in json.loads(
        re.search(r"_pictimeStorageMapping = (\[.*?\]);", pagina, re.S).group(1))}

    url = (f"{mapa[par['accountStorageId']]['cdnDomain']}/pictures/accountdata/"
           f"{troceado(par['accountId'], 'account')}/client/"
           f"{par['portfolioId']}/portfolio.json.txt?ts={par['portfolioTS']}")
    _, _, datos = traer(url)
    proyectos = json.loads(datos.decode("utf-8", "replace"))[1][3]
    juveniles = [p[1] for p in proyectos if "Juveniles" in p[1][1]]

    muestra = juveniles[0]
    titulo(f"Carpeta «{muestra[1]}»")
    _, _, c = traer(f"{base}/-{muestra[2]}")
    par2 = json.loads(re.search(r"initParams = (\{.*?\});", c.decode("utf-8", "replace"), re.S).group(1))
    pid = par2["projectId"]
    alm = par2["projectStorageId"]
    token = par2.get("projectPathToken", "")
    cdn = mapa[alm]["cdnDomain"]
    publico = f"/pictures/projectdata/{troceado(pid)}"
    print(f"  projectId={pid}  storageId={alm}  ruta={publico}")

    titulo("Bajando el listado de fotos")
    for ruta in (publico, f"{publico}/{token}"):
        for archivo in ("gallery.json.txt", "publicphotos.json.txt"):
            u = f"{cdn}{ruta}/{archivo}"
            try:
                estado, cab, d = traer(u)
            except urllib.error.HTTPError as e:
                print(f"  {e.code}  {ruta}/{archivo}")
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  ERR  {ruta}/{archivo}: {e}")
                continue

            print(f"\n  SIRVE  {estado}  {u}")
            print(f"  {len(d)} bytes  [{cab.get('Content-Type')}]")
            texto = d.decode("utf-8", "replace")
            try:
                g = json.loads(texto)
            except Exception:  # noqa: BLE001
                print("  (no es JSON)\n  " + texto[:600])
                continue

            titulo("Estructura del listado")

            def forma(nodo, ruta_n="raiz", nivel=0, tope=7):
                sangria = "  " * nivel
                if isinstance(nodo, list):
                    print(f"  {sangria}{ruta_n}: lista de {len(nodo)}")
                    if nivel < tope:
                        for i, hijo in enumerate(nodo[:4]):
                            forma(hijo, f"[{i}]", nivel + 1, tope)
                        if len(nodo) > 4:
                            print(f"  {sangria}  … {len(nodo) - 4} más")
                elif isinstance(nodo, dict):
                    print(f"  {sangria}{ruta_n}: objeto -> " + ", ".join(list(nodo)[:10]))
                elif isinstance(nodo, str) and nodo:
                    print(f"  {sangria}{ruta_n}: TEXTO {nodo[:60]!r}")
                elif isinstance(nodo, (int, float)) and nodo:
                    print(f"  {sangria}{ruta_n}: {nodo}")

            forma(g)
            return
    print("\n  Ninguna funcionó.")


if __name__ == "__main__":
    main()
