"""Interfaz de línea de comandos del programador de publicaciones."""

import argparse
import sys
from datetime import datetime

from . import cola, config, meta, recordatorio


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
    accion = "Te avisaré" if config.modo() == "recordatorio" else "Se publicará"
    print(f"{accion} el {fecha:%d/%m/%Y a las %H:%M} ({fecha.tzname()})")
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
        hechas = cola.listar(config.DIR_PUBLICADOS)
        print(f"\n{len(hechas)} ya despachada(s):\n")
        for _, pub in hechas:
            fecha = cola.parsear_fecha(pub["cuando"])
            print(f"  {fecha:%d/%m/%Y %H:%M}  {pub['texto'][:50]}")
    return 0


def _despachar(pub, credenciales):
    """Ejecuta una publicación según el modo configurado."""
    if config.modo() == "recordatorio":
        return recordatorio.avisar(
            pub,
            credenciales["ntfy_topic"],
            ruta_foto=cola.ruta_local_de_imagen(pub),
            enlace=pub.get("imagen_url"),
        )

    url_media = cola.url_de_imagen(pub)
    if not url_media:
        raise ValueError("La publicación no tiene imagen y el modo es publicar")
    return meta.publicar(pub, url_media, credenciales)


def _cmd_ejecutar(args):
    ahora = datetime.now(config.zona_horaria())
    vencidas = cola.pendientes(ahora)
    modo = config.modo()

    if not vencidas:
        print(f"[{ahora:%d/%m %H:%M}] Nada pendiente por ahora.")
        return 0

    credenciales = config.credenciales()
    if not args.simulacion:
        falta = (
            "NTFY_TOPIC" if modo == "recordatorio" and not credenciales["ntfy_topic"]
            else "META_ACCESS_TOKEN" if modo == "publicar" and not credenciales["token"]
            else None
        )
        if falta:
            print(f"Falta el secret {falta}", file=sys.stderr)
            return 1

    fallos = 0
    for ruta, pub in vencidas:
        etiqueta = f"{pub['texto'][:40]!r} -> {', '.join(pub['redes'])}"

        if args.simulacion:
            verbo = "Avisaría de" if modo == "recordatorio" else "Publicaría"
            print(f"[simulación] {verbo} {etiqueta}")
            continue

        try:
            resultados = _despachar(pub, credenciales)
        except Exception as error:  # noqa: BLE001 - se anota y se sigue con las demás
            fallos += 1
            cola.marcar_error(ruta, pub, str(error))
            print(f"ERROR con {etiqueta}: {error}", file=sys.stderr)
            continue

        cola.archivar(ruta, pub, resultados)
        verbo = "Recordatorio enviado" if modo == "recordatorio" else "Publicado"
        print(f"{verbo}: {etiqueta} ({resultados})")

    return 1 if fallos else 0


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="programador",
        description="Programa publicaciones de Instagram y te avisa (o las sube) a la hora exacta.",
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
    p.add_argument("--todas", action="store_true", help="Incluir las ya despachadas")
    p.set_defaults(func=_cmd_lista)

    p = sub.add_parser(
        "ejecutar",
        aliases=["publicar"],
        help="Despachar todo lo que ya venció (avisar o publicar según el modo)",
    )
    p.add_argument(
        "--simulacion",
        action="store_true",
        help="Mostrar qué se haría sin enviar nada",
    )
    p.set_defaults(func=_cmd_ejecutar)

    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
