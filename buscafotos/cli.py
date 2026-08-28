"""Los comandos que escribes en la terminal."""

import argparse
import subprocess
import sys

from . import ajustes, archivos, carpeta_local, imagenes, indice, vision


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


def _carpetas_elegidas(datos, filtros):
    """Las carpetas de fotos que hay que mirar, ya filtradas."""
    carpetas = carpeta_local.listar_carpetas(datos)
    filtros = filtros or datos["carpetas"]
    if filtros:
        buscados = [indice.normalizar(f) for f in filtros]
        carpetas = [
            c for c in carpetas
            if any(b in indice.normalizar(c["nombre"]) for b in buscados)
        ]
    return carpetas


def _cmd_carpetas(args):
    """Lista las carpetas con fotos, para saber cuáles indexar."""
    datos = ajustes.cargar()
    base = carpeta_local.raiz(datos)
    if not base.is_dir():
        print(f"No existe la carpeta {base}")
        print('Pon la ruta correcta en la clave "carpeta_local" de buscafotos/ajustes.json')
        return 1

    carpetas = carpeta_local.listar_carpetas(datos)
    if not carpetas:
        print(f"No hay fotos dentro de {base}")
        return 1

    total = sum(c["cantidad"] for c in carpetas)
    print(f"{len(carpetas)} carpeta(s) con {total} foto(s) en {base}:\n")
    for numero, carpeta in enumerate(carpetas, 1):
        print(f"  {numero:>3}. {carpeta['nombre']}  ({carpeta['cantidad']} fotos)")
    print(
        '\nPara indexar solo algunas, pon parte de su nombre en la clave '
        '"carpetas" de buscafotos/ajustes.json'
    )
    return 0


def _cmd_indexar(args):
    """Mira cada foto una vez y guarda qué se ve en ella."""
    datos = ajustes.cargar()
    carpetas = _carpetas_elegidas(datos, args.carpeta)
    if not carpetas:
        print("Ninguna carpeta coincide. Mira cuáles hay con:  python3 -m buscafotos carpetas")
        return 1

    guardado = indice.cargar()
    guardado.setdefault("fotos", [])
    guardado["origen"] = str(carpeta_local.raiz(datos))
    ya_vistas = {f["id"] for f in guardado["fotos"]}

    pendientes = []
    for carpeta in carpetas:
        for foto in carpeta_local.listar_fotos(datos, carpeta):
            if foto["id"] not in ya_vistas:
                pendientes.append(foto)

    if args.limite:
        pendientes = pendientes[: args.limite]

    if not pendientes:
        print("No hay fotos nuevas: el índice ya está al día.")
        return 0

    print(f"{len(pendientes)} foto(s) por mirar. Esto tarda un rato.\n")
    fallos_seguidos = 0
    fallos = 0
    for numero, foto in enumerate(pendientes, 1):
        etiqueta = f"[{numero}/{len(pendientes)}]"
        try:
            contenido, tipo = imagenes.preparar(foto["archivo"])
            ficha = vision.describir(contenido, tipo=tipo, modelo=datos["modelo"])
        except (imagenes.ErrorImagen, vision.ErrorVision) as e:
            fallos += 1
            fallos_seguidos += 1
            print(f"{etiqueta}  ✗ {e}")
            # Un fallo suelto no debe tumbar una indexación de horas, pero
            # diez seguidos significan que algo está roto de verdad (la llave
            # venció, se cayó internet) y seguir solo gasta tiempo.
            if fallos_seguidos >= 10:
                print("\nDiez fallos seguidos. Se detiene aquí.")
                break
            continue

        fallos_seguidos = 0
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
    """Busca en el índice y copia las fotos que mejor encajan."""
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
        print("Prueba con menos palabras: «antorcha» en vez de «una antorcha encendida».")
        return 1

    print(f"{len(resultados)} foto(s) para «{consulta}»:\n")
    destino = None
    if not args.solo_mirar:
        destino = ajustes.carpeta_destino(datos) / archivos.nombre_seguro(consulta)
        destino.mkdir(parents=True, exist_ok=True)

    for puesto, (punto, foto) in enumerate(resultados, 1):
        print(f"  {puesto}. [{punto:.0%}] {foto['descripcion'][:80]}")
        print(f"      {foto['carpeta']} · {foto['id']}")
        if destino is None:
            continue
        nombre = archivos.nombre_seguro(f"{puesto:02d}-{consulta}")
        try:
            copia = archivos.copiar(foto["archivo"], destino, nombre)
            print(f"      → {copia.name}")
        except OSError as e:
            print(f"      ✗ no se pudo copiar: {e}")

    if destino is not None:
        print(f"\nGuardadas en: {destino}")
        _abrir_carpeta(destino)
    return 0


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="python3 -m buscafotos",
        description="Busca fotos por lo que se ve en ellas y te las deja listas.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("carpetas", help="lista las carpetas con fotos")
    p.set_defaults(func=_cmd_carpetas)

    p = sub.add_parser("indexar", help="mira las fotos y anota qué se ve en cada una")
    p.add_argument("--carpeta", action="append", help="solo carpetas cuyo nombre contenga esto")
    p.add_argument("--limite", type=int, help="parar después de esta cantidad de fotos")
    p.set_defaults(func=_cmd_indexar)

    p = sub.add_parser("buscar", help="busca fotos y las copia a tu carpeta de trabajo")
    p.add_argument("consulta", nargs="+", help="qué buscas, por ejemplo: antorcha")
    p.add_argument("-n", "--cuantas", type=int, help="cuántas fotos quieres")
    p.add_argument("--solo-mirar", action="store_true", help="enseñar los resultados sin copiarlos")
    p.set_defaults(func=_cmd_buscar)

    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nCancelado. Lo indexado hasta ahora quedó guardado.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
