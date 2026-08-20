# Publicaciones automáticas en Instagram y Facebook

Programas una publicación con una hora ("el 21 de agosto a las 10:00") y se
envía sola, sin que tengas que estar delante del computador. GitHub revisa la
cola cada 15 minutos y publica lo que ya venció.

## Cómo se usa (el día a día)

1. Metes la foto en la carpeta `fotos/`.
2. Programas la publicación:

```bash
python -m programador programar \
  --texto "Buenos días 🌞 #cafe" \
  --cuando "2026-08-21 10:00" \
  --imagen fotos/cafe.jpg \
  --redes instagram,facebook
```

3. Haces `git add . && git commit -m "Programar post" && git push`.
4. A las 10:00 se publica solo.

Otros comandos:

```bash
python -m programador lista               # ver lo que está en cola
python -m programador lista --todas       # incluir lo ya publicado
python -m programador publicar --simulacion   # ver qué se enviaría, sin enviar
```

Para un reel, usa `--tipo reel` y apunta `--imagen` a un archivo de video.
Si la foto ya está subida en otro lado, usa `--imagen-url https://...` en vez
de `--imagen`.

## Configuración inicial (una sola vez)

### 1. Cuentas

Instagram tiene que ser una cuenta **de empresa o de creador** (no personal) y
estar **conectada a una página de Facebook**. Se cambia desde la app de
Instagram: Configuración → Tipo de cuenta y herramientas. Sin esto la API de
Meta no deja publicar; es un requisito de ellos, no del programa.

### 2. App de Meta y token

1. Entra a https://developers.facebook.com/ y crea una app de tipo "Business".
2. Añádele el producto **Instagram Graph API**.
3. En el **Explorador de la API Graph**, elige tu app y tu página, y pide estos
   permisos: `instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
4. Genera el token y **conviértelo en token de larga duración** (los normales
   caducan en una hora). En la herramienta "Access Token Debugger" verás el
   botón para extenderlo a 60 días.
5. Apunta también:
   - **IG_USER_ID**: en el Explorador, consulta `me/accounts` y luego
     `{id-de-tu-pagina}?fields=instagram_business_account`.
   - **FB_PAGE_ID**: el id de tu página, sale en la misma consulta.

El token de 60 días hay que renovarlo cada dos meses. Ponte un recordatorio, o
pídeme que te añada un aviso automático cuando esté por caducar.

### 3. Guardar las claves en GitHub

En el repo: **Settings → Secrets and variables → Actions → New repository
secret**. Crea tres:

| Secret | Qué es |
| --- | --- |
| `META_ACCESS_TOKEN` | El token de larga duración |
| `IG_USER_ID` | Id de la cuenta de Instagram de empresa |
| `FB_PAGE_ID` | Id de la página de Facebook (solo si publicas también ahí) |

Nunca escribas el token dentro de un archivo del repo: en los Secrets queda
cifrado y no se ve en el código.

### 4. Ajustar `config.json`

```json
{
  "zona_horaria": "America/Bogota",
  "repo": "lindazakaya1/claudenew",
  "rama_fotos": "main",
  "redes_por_defecto": ["instagram"]
}
```

La `zona_horaria` es la que se usa cuando escribes "10:00" sin más. Cámbiala si
no estás en Colombia (por ejemplo `Europe/Madrid`, `America/Mexico_City`).

## Dos cosas importantes

- **La automatización solo corre desde la rama principal.** GitHub ignora las
  tareas programadas en otras ramas. Cuando fusiones esta rama a `main`, el
  reloj empieza a andar; hasta entonces puedes probar a mano desde la pestaña
  **Actions → Publicar en redes → Run workflow**.
- **El repositorio tiene que ser público** para que las fotos de `fotos/`
  funcionen. Instagram no acepta archivos subidos: exige una URL a la que sus
  servidores puedan entrar, y aquí usamos la URL directa de GitHub. Si prefieres
  el repo privado, sube las fotos a otro sitio y usa `--imagen-url`.

## Cómo está hecho por dentro

- `programados/` — cola: un archivo JSON por publicación pendiente.
- `publicados/` — historial, con el id que devolvió cada red.
- `programador/cola.py` — crear, listar, detectar vencidas, archivar.
- `programador/meta.py` — llamadas a la Graph API de Meta.
- `.github/workflows/publicar.yml` — el reloj: cada 15 minutos revisa la cola.

Si una publicación falla, se queda en la cola con el motivo anotado en
`ultimo_error` y se reintenta en la siguiente pasada.

## Pruebas

```bash
python -m unittest discover -s tests
```

## Si prefieres no usar código

Meta Business Suite (business.facebook.com) programa publicaciones de Instagram
y Facebook gratis desde el navegador, sin tokens ni nada de esto. Es más simple
si solo vas a programar de vez en cuando a mano. Este repo tiene sentido cuando
quieres programar muchas de golpe, llevar el historial en git, o encadenarlo con
otros procesos automáticos.
