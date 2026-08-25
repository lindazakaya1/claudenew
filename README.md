# Publicaciones programadas para Instagram

Programas una publicación con su hora y el sistema se encarga a esa hora exacta,
aunque tengas el celular apagado. Funciona en dos modos según cómo tengas la
cuenta de Instagram.

## Qué modo te toca

| Tu cuenta de Instagram | Qué es posible | Modo |
| --- | --- | --- |
| Privada (personal o profesional) | Solo aviso: te llega el texto y la foto y tú tocas publicar | `recordatorio` |
| Pública personal | Instagram ya lo programa solo desde su propia app — **no necesitas este repo** | — |
| Pública profesional (Creador o Empresa) | Publicación automática de verdad, sin tocar nada | `publicar` |

**Las cuentas privadas no pueden publicar automáticamente.** No es una limitación
de este código: la API de Meta no acepta cuentas privadas ni personales, y todas
las apps del mercado (Buffer, Later, Metricool) usan esa misma API. Existen
librerías no oficiales que simulan la app, pero violan los términos de Instagram
y arriesgan el bloqueo de la cuenta; aquí no se usan.

El modo se elige en `config.json` con la clave `modo`. Viene en `recordatorio`.

---

## Modo recordatorio (cuentas privadas)

A la hora programada te llega una notificación al celular con el texto listo
para copiar y la foto adjunta para descargar. Abres Instagram, pegas y publicas.

### 1. Instala ntfy en el celular

Busca **ntfy** en la App Store o Google Play. Es gratis y no pide registro.

### 2. Inventa un tópico secreto

El tópico es como un canal privado. **Cualquiera que adivine el nombre puede
leer tus avisos**, así que no uses `linda` ni `mis-posts`: usa algo largo y
aleatorio, por ejemplo `linda-ig-7f3a9c2b1e`.

En la app de ntfy: **+** → escribe tu tópico → **Subscribe**.

### 3. Guarda el tópico en GitHub

En el repo: **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**

- Name: `NTFY_TOPIC`
- Secret: el tópico que inventaste

### 4. Ajusta tu zona horaria

En `config.json`, la clave `zona_horaria`. Viene en `America/Bogota`.
Otras: `America/Mexico_City`, `America/Argentina/Buenos_Aires`, `Europe/Madrid`.

### 5. Listo

Programa tu primera publicación (ver abajo) y a la hora indicada suena el celular.

---

## Cómo programar una publicación

### Desde la web (sin terminal)

Pestaña **Actions** → *Programar una publicación* → **Run workflow**. Se abre un
formulario con el texto, la fecha y la foto. Funciona igual desde el celular.

Si la publicación lleva foto, súbela antes a la carpeta `fotos/` (botón
**Add file** → **Upload files**) y en el formulario escribe la ruta completa,
por ejemplo `fotos/playa.jpg`.

### Desde la terminal, con foto

```bash
python -m programador programar \
  --texto "Buenos días desde la playa ☀️ #verano" \
  --cuando "2026-08-21 10:00" \
  --imagen fotos/playa.jpg
```

### Desde la terminal, solo texto

```bash
python -m programador programar --texto "Feliz lunes" --cuando "2026-08-24 09:00"
```

### Ver la cola

```bash
python -m programador lista          # lo que está pendiente
python -m programador lista --todas  # incluye lo ya despachado
```

### Probar sin enviar nada

```bash
python -m programador ejecutar --simulacion
```

La hora se escribe en **tu** zona horaria, la de `config.json`. Cada publicación
queda como un archivo JSON en `programados/`; cuando se despacha pasa a
`publicados/`. Si algo falla, la publicación se queda en la cola con el motivo
anotado en `ultimo_error` y se reintenta en la siguiente pasada.

---

## Cómo se ejecuta solo

`.github/workflows/publicar.yml` revisa la cola **cada 30 minutos** en los
servidores de GitHub. No hace falta dejar la computadora encendida.

Programa las publicaciones **en punto o y media** (10:00, 10:30) y el aviso te
llegará muy cerca de la hora. Si programas a las 10:07, el aviso saldrá en la
pasada de las 10:30.

### Público o privado, y cuánto cuesta

| Repositorio | Ejecuciones | Tus fotos y textos |
| --- | --- | --- |
| Público | Gratis e ilimitadas, puedes revisar cada 10 min | **Los ve cualquiera en internet** |
| Privado | 2.000 minutos gratis al mes; cada 30 min gasta ~1.440 | Solo los ves tú |

GitHub factura **un minuto mínimo por ejecución**, aunque la pasada dure 20
segundos. Por eso cada 10 minutos (unos 4.300 minutos al mes) no cabe en el
plan gratuito de un repositorio privado, y cada 30 sí.

Si el repositorio es público y no te importa que las fotos se vean, puedes
cambiar el cron a `*/10 * * * *` en `publicar.yml`.

Dos cosas más que conviene saber:

- **Los cron de GitHub no son puntuales.** Cuando hay mucha carga pueden
  retrasarse entre 5 y 15 minutos más. Para un aviso de las 10:00 esto suele
  dar igual; si necesitas precisión al minuto, no es la herramienta.
- **GitHub apaga los workflows programados tras 60 días sin actividad** en el
  repo. Si dejas de usarlo un par de meses, hay que reactivarlo desde la pestaña
  Actions.

También puedes lanzarlo a mano: pestaña **Actions** → *Publicaciones
programadas* → **Run workflow**.

---

## Modo publicar (solo cuentas profesionales y públicas)

Si algún día pasas la cuenta a Creador o Empresa **y la haces pública**, cambia
`"modo": "publicar"` en `config.json` y añade estos secrets:

| Secret | Qué es |
| --- | --- |
| `META_ACCESS_TOKEN` | Token de acceso de larga duración de tu app de Meta |
| `IG_USER_ID` | Id de tu cuenta profesional de Instagram |
| `FB_PAGE_ID` | Id de la página de Facebook (solo si publicas también ahí) |

Se sacan en [developers.facebook.com](https://developers.facebook.com): creas una
app, añades el producto de Instagram y generas el token. Con cuenta de **Creador**
ya no hace falta tener una página de Facebook conectada.

En este modo las fotos se sirven desde `raw.githubusercontent.com`, así que
**el repositorio tiene que ser público** para que los servidores de Meta puedan
descargarlas. Si prefieres mantenerlo privado, usa `--imagen-url` con una foto
alojada en otro sitio.

Soporta fotos y reels (`--tipo reel`), y publicar en Instagram y Facebook a la
vez con `--redes instagram,facebook`.

---

## Pruebas

```bash
python -m unittest discover -s tests
```
