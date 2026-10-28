# Contenido del proyecto: qué se aplica y dónde

Este documento separa tres cosas que es fácil confundir:

1. lo que el motor **aplica de verdad** sobre el ROM del jugador;
2. el contenido que la app **muestra** y no toca el cartucho;
3. lo que sigue **sin implementar**, con la razón técnica de por qué.

## 1. Lo que se aplica al ROM

Ruta completa, en el orden real:

```
diseño      content/zerohistory.toml        tabla declarativa (formato snes_text_xlate)
carga       src/x3_content.c                snes_text_xlate_init_c(tabla, "es")
verificación el runner compara `source_hex` con los bytes del ROM cargado
aplicación  snes_text_xlate_on_frame_c()    escribe en la copia EN MEMORIA
reporte     "[mmx] contenido: N/M parche(s) de ROM aplicados" en native.log
```

El archivo del jugador **nunca se modifica**. El parche vive en la imagen que
el motor carga después de verificar la identidad del dump, igual que un
parche de traducción: si el `source_hex` no coincide, el parche no se aplica
y el log lo dice. Eso es deliberado — un ROM distinto no queda a medio
parchear y el dump original sirve para volver a empezar.

Para quien quiera la copia en disco (emuladores, diff, archivo):

```console
python3 tools/x3_content_patch.py --check mmx3.sfc     # informa, no escribe
python3 tools/x3_content_patch.py --apply mmx3.sfc     # <rom>.zerohistory.sfc
```

`--apply` escribe una copia nueva con el checksum SNES recalculado. El
original queda intacto; el script falla entero si algún parche no corresponde.

### Parches incluidos

- **Identidad interna del cartucho** (`0x7FC0`, 21 bytes): `MEGAMAN X3` +
  relleno → `MMX ZERO HISTORY` + relleno. Es el nombre que muestran los
  exploradores de ROM, los gestores de guardados y las herramientas de
  volcado. El juego no lo dibuja.

Es el único campo del cartucho cuya posición se puede afirmar **sin tener el
dump delante**, porque la especificación LoROM la fija. Todo lo demás depende
de direcciones que sólo se derivan del ROM real.

### Cómo agregar un parche

```toml
[[rom_patch]]
address = 0x123456
source_hex = "..."   # bytes exactos del cartucho original
es_hex     = "..."   # reemplazo, mismo tamaño
```

Reglas que el motor exige y los tests verifican:

- `source_hex` y el reemplazo deben medir lo mismo: un parche no cambia el
  tamaño de la imagen.
- El nombre del idioma es la clave menos el sufijo `_hex` (`es_hex`). Un
  `target_es_hex` se guarda bajo el idioma `target_es`, que nadie consulta:
  el parche nunca se aplicaría. Ese error ya ocurrió una vez y está fijado
  con un test.
- `address` es offset lineal del archivo, no una dirección de CPU.
- Para VRAM usa `[[vram_patch]]` (palabra de VRAM) y agrega `guard_address` /
  `guard_hex` si el payload se comparte entre pantallas.

## 2. Lo que la app muestra

- **Pantalla de entrada**: estado del ROM, versión de la build, campo que
  eligió el motor y cuántos parches se aplicaron (leído de `native.log`).
- **Historia y jefes**: la Bóveda Ω, los ocho mavericks con su arma, el anillo
  de debilidades y las reglas de las cápsulas errantes. Vive en
  `LoreActivity.java`, es texto de la app y no entra al cartucho.

## 3. El guion: overlay narrativo

Desde la 0.0.6 la historia, el guion, los textos de cápsula y los nombres de
jefes **sí entran al juego**. No van por `[[rom_patch]]` porque son miles de
bytes y cambiarían de tamaño; van por un camino propio que aprovecha el propio
formato del cartucho.

### Por qué se puede

Mega Man X3 guarda su guion como **texto ASCII plano**, con `0x80 0x80` como
salto de línea y comandos de un byte entre páginas:

```
1CC2B6  49 6e 20 74 68 65 20 79 65 61 72 20 32 31 58 58 2c  In the year 21XX,
```

Eso es una suerte enorme: no hay tabla de glifos que adivinar para el texto
latino. Cada página es un tramo de bytes imprimibles con un largo fijo, y el
motor dibuja lo que encuentra ahí. Reemplazar esa página por la nuestra no
mueve un solo puntero.

### Cómo se empaqueta

```
content/story_es.txt        guion en chileno, una línea por renglón
tools/build_story.py        lee el dump, mide las páginas, empaqueta
src/x3_story_data.c         generado: nuestro texto + direcciones + largos
src/x3_story.c              aplica sobre la imagen cargada, tras verificar SHA-256
```

Tres invariantes, cada una verificada por un test:

1. **Misma longitud de página.** El reemplazo mide exactamente lo que el tramo
   original. Ningún puntero ni comando de control se mueve.
2. **Sólo bytes de texto.** ASCII imprimible y `0x80`. Un solo byte de control
   pisado rompería la página, así que el generador no puede emitirlo y el test
   lo rechaza.
3. **Ancho acotado a 22 columnas.** El motor **no envuelve** texto: una línea
   más larga se corta. La tercera línea de la caja va centrada, y ahí 28
   columnas ya pierden el último glifo — medido en el motor real con reglas de
   ancho, no supuesto. 22 es el máximo seguro en ambas posiciones.

### Qué cubre

- **Intro** (20 páginas): la Bóveda Ω, el Eco de Wily, la foto de W-00.
- **Acto I** (24 páginas): las ocho revisiones, Cero-Ω en la azotea.
- **Cápsulas** (8 grupos): los ocho fragmentos de memoria, leídos por Salas.
- **Acto II/III** (26 + 87 páginas): la revelación y el cierre del archivo.
- **Tablas**: cast, los ocho jefes con POWER/SPEED, las ocho armas, el
  marcador de jefe de etapa, y los rótulos del título y las opciones.

### Qué NO cubre

Los sprites, los mapas, la música del SPC y la lógica de los jefes siguen
siendo los del cartucho. La historia nueva se cuenta con los personajes y los
escenarios que X3 ya tiene. Dibujar a Cóndor Cobalto y programar su IA sigue
siendo el trabajo largo de más abajo.

### Regenerar

Hace falta el dump, porque los largos de página se miden sobre él:

```console
python3 tools/build_story.py --rom mmx3.sfc          # reescribe el generado
python3 tools/build_story.py --rom mmx3.sfc --check  # sólo informa
```

El generado **se versiona**: contiene únicamente nuestro texto, las
direcciones y los largos — ningún byte del guion original. Eso permite
compilar y testear el proyecto sin el dump.

### Lo que queda por derivar del dump

1. **Gráficos**: los tiles de jefes y escenarios están comprimidos con el
   esquema del juego; insertarlos requiere el compresor y espacio libre en el
   banco correcto.
2. **Música**: los temas tendrían que ser secuencias del driver de X3, no PCM.
3. **Lógica de jefe**: rutinas de IA y colisión en 65816, con las tablas de
   daño y el anillo de debilidades.

Mientras tanto, el proyecto no finge: la app dice en pantalla qué cambia y
qué no, y este documento es la lista de lo que queda.

## Verificación

```console
python3 tools/test_content_patch.py    # 12 pruebas, sin ROM real
bash tools/test_story_guard.sh         # política de identidad del overlay
bash tools/test_story_apply.sh         # escribe con el dump bueno, nada con otro
python3 tools/test_story_layout.py     # forma del generado, sin dump
bash tools/test_display_width.sh
bash tools/test_touch_controls.sh
```

`test_story_apply.sh` enlaza `src/x3_story.c` y el generado contra un cartucho
simulado de 2 MiB y comprueba las dos ramas: con otro digest no se escribe ni
un byte, con el digest correcto se escriben todas las páginas y nada fuera de
ellas.

`test_content_patch.py` construye imágenes sintéticas de 2 MiB con la cabecera
LoROM, así que prueba el motor sin distribuir datos del cartucho: aplicación,
idempotencia, rechazo de un ROM ajeno, fallo cerrado con un parche imposible,
checksum, y el contrato de claves de la tabla.

En el emulador Android se comprueba de punta a punta con un dump sintético que
lleva la cabecera real:

```console
adb shell cat /sdcard/Android/data/cl.zerohistory.mmx/files/native.log | grep contenido
# [mmx] contenido: tabla content/zerohistory.toml, idioma es, 1 parche(s) de ROM, 0 de VRAM
# [mmx] contenido: 1/1 parche(s) de ROM aplicados
```
