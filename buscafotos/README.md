# Buscafotos

Le pides una foto por lo que se ve en ella —«antorcha», «niño sonriendo»,
«equipo celebrando»— y te la deja lista en una carpeta de tu computadora.

Lee tu galería de Pic-Time **directamente de la web**. No tienes que bajar
nada a mano.

Funciona en dos pasos:

1. **Indexar** (una vez): mira cada foto y anota qué se ve en ella. Queda
   guardado en `indice.json`. Tarda, y cuesta unos centavos.
2. **Buscar** (siempre): busca en esas anotaciones y te trae las que mejor
   encajan. Es instantáneo y gratis.

---

## Lo que hay en tu galería

Las 78 carpetas de `macabeadaspty.pic-time.com` están en dos bloques: las
primeras 56 son `MN 2026` (las Macabeadas Nacionales) y las últimas 22 son
`VIII Macabeadas Juveniles`. Esas 22 son las tuyas y suman **26.147 fotos**.

Por eso `ajustes.json` viene con `"carpetas": ["Juveniles"]`: así ni mira
las de los grandes.

---

## Preparar (una sola vez)

### 1. Tener Python

En Mac ya viene. Para comprobarlo, abre la aplicación **Terminal**:

```
python3 --version
```

Si responde con un número (3.9 o superior), listo. En Windows se baja de
[python.org](https://www.python.org/downloads/) marcando **Add Python to
PATH** durante la instalación.

Instala también Pillow, que achica las fotos antes de mandarlas a mirar:

```
python3 -m pip install pillow
```

### 2. Conseguir la llave de la API de Claude

Es lo que le permite al programa *mirar* las fotos. Se saca en
[console.anthropic.com](https://console.anthropic.com) → **API Keys** →
**Create Key**. Hay que cargarle saldo.

Guárdala en un archivo `clave.txt` dentro de esta carpeta:

```
echo "sk-ant-tu-llave-aqui" > buscafotos/clave.txt
```

Ese archivo está en `.gitignore`, así que no se sube a GitHub.

### 3. Ver qué carpetas hay

```
python3 -m buscafotos carpetas
```

Las marcadas con `*` son las que se van a indexar.

---

## Empieza por una sola carpeta

**No indexes las 26.147 fotos de una.** Serían unas 7 horas y unos 26
dólares. Prueba primero con una carpeta chica, mira si las búsquedas te
sirven, y de ahí decides.

```
python3 -m buscafotos indexar --carpeta Equipos
```

Esa tiene 320 fotos: unos 20 minutos y unos 30 centavos. Otras pequeñas:

| Carpeta | Fotos | Costo aprox. |
| --- | ---: | ---: |
| Natacion | 184 | $0.18 |
| Bolos | 232 | $0.23 |
| Equipos | 320 | $0.32 |
| Padel | 417 | $0.42 |
| Sabado 10 | 451 | $0.45 |

Y para probar con muy pocas antes de comprometerte:

```
python3 -m buscafotos indexar --carpeta Equipos --limite 20
```

Puedes cortar con Ctrl+C y retomar: no vuelve a mirar las que ya tiene.

Cuando te convenza, quita el `--carpeta` y deja que recorra las 22. Puede
correr toda la noche.

---

## Usarlo

```
python3 -m buscafotos buscar antorcha
python3 -m buscafotos buscar niño sonriendo
python3 -m buscafotos buscar equipo celebrando -n 10
```

Las fotos aparecen en `~/Descargas/fotos-elegidas/<lo-que-buscaste>/` y la
carpeta se abre sola.

Para ver los resultados sin traer nada:

```
python3 -m buscafotos buscar antorcha --solo-mirar
```

### Qué anota de cada foto

Además de la descripción, guarda cosas que sirven al diseñar y por las que
también puedes buscar: cuánta gente sale, si son niños o adolescentes, si
es vertical u horizontal, y **dónde hay espacio despejado para un titular**.

Las etiquetas incluyen sinónimos a propósito —si hay una antorcha también
dice «fuego» y «llama»— para que la encuentres con la palabra que te salga.

### Sobre el tamaño de las fotos

Pic-Time sirve las fotos en varios tamaños y el programa usa el más grande
disponible, que en tu galería es `lowres` (unos 73 KB). Alcanza para
elegir y para maquetar en pequeño. **Para la resolución completa, bájala de
Pic-Time**: cada foto del índice guarda la dirección de su carpeta.

---

## Ajustes

Todo se cambia en `buscafotos/ajustes.json`:

| Clave | Para qué sirve |
| --- | --- |
| `origen` | `web` lee Pic-Time; `carpeta` lee tu disco |
| `galeria` | Dirección de la galería |
| `carpeta_local` | Carpeta del disco, si usas `origen: carpeta` |
| `carpetas` | Qué carpetas indexar (vacío = todas) |
| `destino` | Dónde te deja las fotos |
| `modelo` | Qué modelo mira las fotos |
| `cuantas` | Cuántas trae cada búsqueda |

---

## Si algún día deja de funcionar

Pic-Time no publica una forma oficial de consultar sus galerías: esto se
dedujo observando cómo las pide su propio sitio. Si lo cambian, el lector
puede romperse.

Cuando pase, el error dice en qué paso falló. Para ver dónde exactamente,
en GitHub: pestaña **Actions** → **Probar el buscador contra la galería** →
**Run workflow**.

Y mientras tanto puedes seguir trabajando: pon `"origen": "carpeta"` en
`ajustes.json`, baja las galerías con el botón de Pic-Time, y el buscador
las indexa desde tu disco igual que antes.

---

## Comprobar que todo funciona

```
python3 -m unittest discover -s tests
```

No toca internet ni gasta API.
