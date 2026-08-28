# Buscafotos

Le pides una foto por lo que se ve en ella —«antorcha», «niño sonriendo»,
«equipo celebrando»— y te la deja lista en una carpeta de tu computadora.

Funciona en dos pasos:

1. **Indexar** (una sola vez): mira cada foto y anota qué se ve en ella.
   Queda guardado en `indice.json`. Tarda, y cuesta unos centavos.
2. **Buscar** (cada vez que necesites fotos): busca en esas anotaciones y te
   copia las que mejor encajan. Es instantáneo y gratis.

---

## Por qué trabaja sobre una carpeta y no sobre la web

Pic-Time arma sus galerías con JavaScript: la página que llega al navegador
viene vacía y las fotos aparecen después, pedidas por un programa interno.
No hay una lista de fotos que se pueda leer desde fuera, y aunque se lograra
imitar esa petición, se rompería la próxima vez que Pic-Time cambie su sitio.

Por eso el programa lee de una carpeta tuya. Bajar la galería una vez usando
el botón que Pic-Time ya trae es más rápido, no se rompe nunca, y te deja las
fotos en resolución completa, que es lo que necesitas para diseñar.

---

## Preparar (una sola vez)

### 1. Bajar las galerías que te interesan

En la galería de Pic-Time, arriba a la derecha, la flecha hacia abajo →
**Download Full Gallery** → **Download to Computer**. Llega como uno o varios
archivos `.zip`.

Descomprímelos todos dentro de una misma carpeta, por ejemplo
`Descargas/Macabeadas`, dejando una subcarpeta por galería:

```
Descargas/Macabeadas/
    01 Macabeadas Grandes/
    05 Macabeadas Chicos/
    06 Macabeadas Chicos Premiación/
```

Los nombres de las subcarpetas son los que después puedes filtrar.

### 2. Tener Python

En Mac ya viene. Para comprobarlo, abre la aplicación **Terminal** y escribe:

```
python3 --version
```

Si responde con un número (3.9 o superior), listo. En Windows se baja de
[python.org](https://www.python.org/downloads/) marcando la casilla
**Add Python to PATH** durante la instalación.

Instala además Pillow, que achica las fotos antes de mandarlas a mirar (sale
más rápido y más barato):

```
python3 -m pip install pillow
```

### 3. Conseguir la llave de la API de Claude

Es lo que le permite al programa *mirar* las fotos. Se saca en
[console.anthropic.com](https://console.anthropic.com) → **API Keys** →
**Create Key**. Hay que cargarle saldo; con cinco dólares alcanza de sobra.

Guárdala en un archivo `clave.txt` dentro de esta carpeta:

```
echo "sk-ant-tu-llave-aqui" > buscafotos/clave.txt
```

Ese archivo está en `.gitignore`, así que no se sube a GitHub.

### 4. Decirle dónde están las fotos

Abre `buscafotos/ajustes.json` y pon la ruta de la carpeta del paso 1:

```json
{
  "carpeta_local": "~/Descargas/Macabeadas",
  "carpetas": ["chicos"],
  "destino": "~/Descargas/fotos-elegidas",
  "modelo": "claude-haiku-4-5-20251001",
  "cuantas": 5
}
```

`carpetas` deja fuera lo que no te interesa: con `["chicos"]` solo mira las
subcarpetas que tengan «chicos» en el nombre. Déjalo vacío (`[]`) para todas.

Para ver qué subcarpetas encontró:

```
python3 -m buscafotos carpetas
```

### 5. Indexar

```
python3 -m buscafotos indexar
```

Va imprimiendo cada foto que lee. Puedes cortarlo con Ctrl+C y retomarlo
después: no vuelve a mirar las que ya tiene.

Antes de lanzarlo entero conviene probar con pocas:

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

Las fotos aparecen en `~/Descargas/fotos-elegidas/<lo-que-buscaste>/` y la
carpeta se abre sola.

Para ver los resultados sin copiar nada:

```
python3 -m buscafotos buscar antorcha --solo-mirar
```

### Qué anota de cada foto

Además de la descripción, guarda cosas que sirven al diseñar, y por las que
también puedes buscar: cuánta gente sale, si son niños o adolescentes, si es
vertical u horizontal, y **dónde hay espacio despejado para poner un titular**.

---

## Cuánto cuesta

Solo cuesta indexar, y solo la primera vez. Con Haiku sale alrededor de
**un dólar por cada mil fotos**. Buscar no cuesta nada: el índice ya está en
tu computadora.

## Si añaden fotos nuevas

Descomprime las nuevas en la misma carpeta y vuelve a correr `indexar`. Solo
mira las que no tenía.

## Comprobar que todo funciona

```
python3 tests/test_buscafotos.py
```

Usa fotos de mentira y no gasta API.
