# Buscafotos

Le pides una foto por lo que se ve en ella —«antorcha», «niño sonriendo»,
«equipo celebrando»— y te la baja a tu computadora.

Funciona en dos pasos:

1. **Indexar** (una sola vez): mira cada foto de la galería y anota qué se ve
   en ella. Queda guardado en `indice.json`.
2. **Buscar** (cada vez que necesites fotos): busca en esas anotaciones y baja
   las que mejor encajan.

El paso 1 tarda y cuesta unos centavos. El paso 2 es instantáneo y gratis.

---

## Preparar (una sola vez)

### 1. Tener Python

En Mac ya viene. Para comprobarlo, abre la aplicación **Terminal** y escribe:

```
python3 --version
```

Si responde con un número (3.9 o superior), listo. En Windows se descarga de
[python.org](https://www.python.org/downloads/) marcando la casilla
«Add Python to PATH» durante la instalación.

No hay que instalar nada más: el programa usa solo lo que Python ya trae.

### 2. Conseguir la llave de la API de Claude

Es lo que le permite al programa *mirar* las fotos. Se saca en
[console.anthropic.com](https://console.anthropic.com) → **API Keys** →
**Create Key**. Hay que cargarle saldo (con cinco dólares alcanza de sobra).

Guarda la llave en un archivo llamado `clave.txt` dentro de esta carpeta:

```
echo "sk-ant-tu-llave-aqui" > buscafotos/clave.txt
```

Ese archivo está en `.gitignore`, así que no se sube a GitHub.

### 3. Elegir qué carpetas indexar

Para ver qué carpetas tiene la galería:

```
python3 -m buscafotos carpetas
```

Si solo te interesan algunas (por ejemplo las de los chicos y no las de los
grandes), abre `buscafotos/ajustes.json` y pon parte del nombre:

```json
{
  "carpetas": ["chicos", "juvenil"]
}
```

### 4. Indexar

```
python3 -m buscafotos indexar
```

Va imprimiendo cada foto que va leyendo. Se puede cortar con Ctrl+C y retomar
después: no vuelve a mirar las que ya tiene.

Para probar con pocas antes de lanzarlo entero:

```
python3 -m buscafotos indexar --limite 20
```

---

## Usarlo

```
python3 -m buscafotos buscar antorcha
python3 -m buscafotos buscar niño sonriendo
python3 -m buscafotos buscar equipo celebrando -n 10
```

Las fotos caen en `~/Descargas/fotos-macabeadas/<lo-que-buscaste>/` y la
carpeta se abre sola.

Para ver los resultados sin bajarlos:

```
python3 -m buscafotos buscar antorcha --solo-mirar
```

---

## Ajustes

Todo se cambia en `buscafotos/ajustes.json`:

| Clave | Para qué sirve |
| --- | --- |
| `galeria` | Dirección de la galería |
| `carpetas` | Qué carpetas indexar (vacío = todas) |
| `destino` | Dónde caen las fotos en tu computadora |
| `modelo` | Qué modelo mira las fotos |
| `cuantas` | Cuántas fotos baja cada búsqueda |

---

## Cuánto cuesta

Solo cuesta indexar, y solo la primera vez. Con el modelo Haiku sale alrededor
de **un dólar por cada mil fotos**. Buscar no cuesta nada, porque busca en el
índice que ya está en tu computadora.

## Si añaden fotos nuevas a la galería

Vuelve a correr `indexar`. Solo mira las que no tenía.
