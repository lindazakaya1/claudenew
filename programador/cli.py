"""Interfaz de línea de comandos del programador de publicaciones."""

import argparse
import sys
from datetime import datetime

from . import cola, config, meta


def _cmd_programar(args):
    ruta, pub = cola.crear(
        texto=args.texto,
        cuando=args.cuando,
        imagen=args.imagen,
        imagen_url=args.imagen_url,
        redes=args.redes.split(",") if args.redes else None,
        tipo=args.tipo,
    )
    fecha = cola.parsear_fecha(pub["cuando"])
    print(f"Programado para el {fecha:%d/%m/%Y a las %H:%M} ({fecha.tzname()})")
    print(f"Redes: {', '.join(pub['redes'])}")
    print(f"Archivo: {ruta.relative_to(config.RAIZ)}")
    return 0


def _cmd_lista(args):
    pendiente = cola.listar()
    if not pendiente:
        print("No hay publicaciones programadas.")
    else:
        print(f"{len(pendiente)} publicación(es) en cola:\n")
        for _, pub in pendiente:
            fecha = cola.parsear_fecha(pub["cuando"])
            resumen = pub["texto"].replace("\n", " ")[:50]
            print(f"  {fecha:%d/%m/%Y %H:%M}  [{', '.join(pub['redes'])}]  {resumen}")
            if pub.get("ultimo_error"):
                print(f"      último error: {pub['ultimo_error']}")

    if args.todas:
        publicadas = cola.listar(config.DIR_PUBLICADOS)
        print(f"\n{len(publicadas)} ya publicada(s):\n")
        for _, pub in publicadas:
            fecha = cola.parsear_fecha(pub["cuando"])
            print(f"  {fecha:%d/%m/%Y %H:%M}  {pub['texto'][:50]}")
    return 0


def _cmd_publicar(args):
    ahora = datetime.now(config.zona_horaria())
    vencidas = cola.pendientes(ahora)
    if not vencidas:
        print(f"[{ahora:%d/%m %H:%M}] Nada que publicar por ahora.")
        return 0

    credenciales = config.credenciales()
    if not args.simulacion and not credenciales["token"]:
        print("Falta el secret META_ACCESS_TOKEN", file=sys.stderr)
        return 1

    fallos = 0
    for ruta, pub in vencidas:
        url_media = cola.url_de_imagen(pub)
        etiqueta = f"{pub['texto'][:40]!r} -> {', '.join(pub['redes'])}"

        if args.simulacion:
            print(f"[simulación] Publicaría {etiqueta} con {url_media}")
            continue

        try:
            resultados = meta.publicar(pub, url_media, credenciales)
        except Exception as error:  # noqa: BLE001 - se anota y se sigue con las demás
            fallos += 1
            cola.marcar_error(ruta, pub, str(error))
            print(f"ERROR al publicar {etiqueta}: {error}", file=sys.stderr)
            continue

        cola.archivar(ruta, pub, resultados)
        print(f"Publicado {etiqueta} ({resultados})")

    return 1 if fallos else 0


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="programador",
        description="Programa publicaciones de Instagram y Facebook y las envía solas.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("programar", help="Añadir una publicación a la cola")
    p.add_argument("--texto", required=True, help="Texto o caption de la publicación")
    p.add_argument(
        "--cuando", required=True, help="Fecha y hora, por ejemplo '2026-08-21 10:00'"
    )
    p.add_argument("--imagen", help="Ruta dentro del repo, por ejemplo fotos/playa.jpg")
    p.add_argument("--imagen-url", dest="imagen_url", help="URL pública de la imagen")
    p.add_argument("--redes", help="instagram, facebook o ambas separadas por coma")
    p.add_argument(
        "--tipo", choices=["imagen", "reel"], default="imagen", help="Tipo de contenido"
    )
    p.set_defaults(func=_cmd_programar)

    p = sub.add_parser("lista", help="Ver las publicaciones programadas")
    p.add_argument("--todas", action="store_true", help="Incluir las ya publicadas")
    p.set_defaults(func=_cmd_lista)

    p = sub.add_parser("publicar", help="Publicar todo lo que ya venció")
    p.add_argument(
        "--simulacion",
        action="store_true",
        help="Mostrar qué se publicaría sin enviar nada",
    )
    p.set_defaults(func=_cmd_publicar)

    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
