"""Los comandos que escribes en la terminal."""

import argparse
import subprocess
import sys
import time

from . import ajustes, descargas, indice, pictime, vision


def _abrir_carpeta(ruta):
    """Abre la carpeta en el explorador de archivos, si se puede."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(ruta)], check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", str(ruta)], check=False)
        else:
            subprocess.run(["xdg-open", str(ruta)], check=False)
    except Exception:  # noqa: BLE001
        pass


def _cmd_carpetas(args):
    """Lista las carpetas de la galería, para saber cuáles indexar."""
    datos = ajustes.cargar()
    carpetas = pictime.listar_carpetas(datos["galeria"])
    if not carpetas:
        print("No se encontró ninguna carpeta en la galería.")
        return 1
    print(f"{len(carpetas)} carpeta(s) en {datos['galeria']}:\n")
    for numero, carpeta in enumerate(carpetas, 1):
        cuantas = carpeta.get("cantidad")
        detalle = f"{cuantas} fotos" if cuantas else "cantidad desconocida"
        print(f"  {numero:>3}. {carpeta['nombre']}  ({detalle})")
    print(
        "\nPara indexar solo algunas, pon parte de su nombre en la clave "
        '"carpetas" de buscafotos/ajustes.json'
    )
    return 0


def _cmd_indexar(args):
    """Mira cada foto una vez y guarda qué se ve en ella."""
    datos = ajustes.cargar()
    filtros = args.carpeta or datos["carpetas"]

    carpetas = pictime.listar_carpetas(datos["galeria"])
    if filtros:
        buscados = [indice.normalizar(f) for f in filtros]
        carpetas = [
            c for c in carpetas
            if any(b in indice.normalizar(c["nombre"]) for b in buscados)
        ]
    if not carpetas:
        print("Ninguna carpeta coincide con el filtro. Prueba con: carpetas")
        return 1

    guardado = indice.cargar()
    guardado.setdefault("fotos", [])
    guardado["galeria"] = datos["galeria"]
    ya_vistas = {f["id"] for f in guardado["fotos"]}

    pendientes = []
    for carpeta in carpetas:
        print(f"Leyendo la carpeta «{carpeta['nombre']}»…", flush=True)
        for foto in pictime.listar_fotos(datos["galeria"], carpeta):
            if foto["id"] not in ya_vistas:
                pendientes.append(foto)

    if args.limite:
        pendientes = pendientes[: args.limite]

    if not pendientes:
        print("No hay fotos nuevas: el índice ya está al día.")
        return 0

    print(f"\n{len(pendientes)} foto(s) por mirar. Esto tarda un rato.\n")
    fallos = 0
    for numero, foto in enumerate(pendientes, 1):
        etiqueta = f"[{numero}/{len(pendientes)}] {foto['carpeta']}"
        try:
            imagen, tipo = descargas.traer(foto["url_mini"])
            ficha = vision.describir(imagen, tipo=tipo.split(";")[0] or "image/jpeg")
        except (descargas.ErrorDescarga, vision.ErrorVision) as e:
            fallos += 1
            print(f"{etiqueta}  ✗ {e}")
            # Un fallo suelto no debe tumbar una indexación de horas, pero si
            # fallan muchas seguidas algo está mal de verdad (llave vencida,
            # sin internet) y seguir solo gasta tiempo.
            if fallos >= 10 and fallos == numero:
                print("\nDemasiados fallos seguidos. Se detiene aquí.")
                break
            continue

        foto.update(ficha)
        guardado["fotos"].append(foto)
        print(f"{etiqueta}  {ficha['descripcion'][:70]}")

        # Se guarda cada tanto para no perder el trabajo si se corta a medias.
        if numero % 20 == 0:
            indice.guardar(guardado)

    indice.guardar(guardado)
    print(f"\nÍndice guardado: {len(guardado['fotos'])} fotos en total.")
    if fallos:
        print(f"({fallos} foto(s) no se pudieron leer; vuelve a correr indexar)")
    return 0


def _cmd_buscar(args):
    """Busca en el índice y baja las fotos que mejor encajan."""
    datos = ajustes.cargar()
    consulta = " ".join(args.consulta)
    cuantas = args.cuantas or datos["cuantas"]

    guardado = indice.cargar()
    if not guardado.get("fotos"):
        print("El índice está vacío. Corre primero:  python3 -m buscafotos indexar")
        return 1

    resultados = indice.buscar(consulta, cuantas=cuantas, datos=guardado)
    if not resultados:
        print(f"No encontré nada para «{consulta}».")
        print("Prueba con otras palabras, o con menos: «antorcha» en vez de")
        print("«una antorcha encendida de noche».")
        return 1

    destino = ajustes.carpeta_destino(datos) / descargas.nombre_seguro(consulta)
    destino.mkdir(parents=True, exist_ok=True)

    print(f"{len(resultados)} foto(s) para «{consulta}»:\n")
    for puesto, (punto, foto) in enumerate(resultados, 1):
        print(f"  {puesto}. [{punto:.0%}] {foto['descripcion'][:80]}")
        if args.solo_mirar:
            continue
        url = foto.get("url_grande") or foto["url_mini"]
        nombre = descargas.nombre_seguro(f"{puesto:02d}-{consulta}")
        try:
            archivo = descargas.guardar(url, destino, nombre)
            print(f"      → {archivo.name}")
        except descargas.ErrorDescarga as e:
            print(f"      ✗ no se pudo bajar: {e}")
        time.sleep(0.2)

    if not args.solo_mirar:
        print(f"\nGuardadas en: {destino}")
        _abrir_carpeta(destino)
    return 0


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="python3 -m buscafotos",
        description="Busca fotos por lo que se ve en ellas y las baja a tu computadora.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("carpetas", help="lista las carpetas de la galería")
    p.set_defaults(func=_cmd_carpetas)

    p = sub.add_parser("indexar", help="mira las fotos y anota qué se ve en cada una")
    p.add_argument("--carpeta", action="append", help="solo carpetas cuyo nombre contenga esto")
    p.add_argument("--limite", type=int, help="parar después de esta cantidad de fotos")
    p.set_defaults(func=_cmd_indexar)

    p = sub.add_parser("buscar", help="busca fotos y las baja")
    p.add_argument("consulta", nargs="+", help='qué buscas, por ejemplo: antorcha')
    p.add_argument("-n", "--cuantas", type=int, help="cuántas fotos bajar")
    p.add_argument("--solo-mirar", action="store_true", help="enseñar los resultados sin bajarlos")
    p.set_defaults(func=_cmd_buscar)

    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nCancelado.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
