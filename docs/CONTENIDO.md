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

## 3. Lo que falta, y por qué

Insertar la historia, los jefes, las cápsulas, el guion y la música **dentro
del juego** requiere datos que sólo se obtienen del ROM:

1. **Glifos y tablas de texto**: X3 guarda el texto con una codificación
   propia sobre su fuente de tiles. Sin el dump no se puede deducir el mapa
   carácter → byte, y adivinarlo escribe basura legible por el juego.
2. **Direcciones de los bloques** (select de etapas, diálogos, nombres de
   jefe): hay que localizarlos en el dump, con su `source_hex` exacto, para
   que el parche esté guardado por contenido.
3. **Gráficos**: los tiles de jefes y escenarios están comprimidos con el
   esquema del juego; insertarlos requiere el compresor y espacio libre en el
   banco correcto.
4. **Música**: los temas tendrían que ser secuencias del driver de X3, no PCM.

El motor ya tiene el mecanismo para (2) y (3) sin tocar el cartucho
(`[[rom_patch]]`, `[[vram_patch]]`, más `snes_rom_patch_apply` para IPS/BPS en
variantes de contenido). Lo que falta es la derivación de direcciones, que es
trabajo por título y exige el dump del dueño.

Mientras tanto, el proyecto no finge: la app dice en pantalla qué cambia y
qué no, y este documento es la lista de lo que queda.

## Verificación

```console
python3 tools/test_content_patch.py    # 12 pruebas, sin ROM real
bash tools/test_display_width.sh
bash tools/test_touch_controls.sh
```

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
