## Contenido aplicado al ROM (de verdad, y verificado)

Hasta la 0.0.4 el contenido estaba sólo documentado. Ahora hay una ruta real
desde el diseño hasta los bytes del juego, y se puede comprobar.

### Qué se aplica

[`content/zerohistory.toml`](content/zerohistory.toml) es una tabla de parches
en el formato del motor (`snes_text_xlate`). Al arrancar, después de verificar
la identidad del dump, el motor la aplica **sobre la copia en memoria** de tu
ROM:

```
[mmx] contenido: tabla content/zerohistory.toml, idioma es, 1 parche(s) de ROM, 0 de VRAM
[mmx] contenido: 1/1 parche(s) de ROM aplicados
```

- **Guardado por contenido**: cada parche declara `source_hex`; si los bytes
  del destino no son los del cartucho original, no se escribe nada y el log lo
  informa. Un dump ajeno no queda a medio parchear.
- **El archivo del jugador no se toca.** El parche vive en la imagen cargada,
  igual que un parche de traducción.
- **Parche incluido**: identidad interna del cartucho (cabecera LoROM,
  `0x7FC0`, 21 bytes) → `MMX ZERO HISTORY`. Es el único campo cuya posición
  fija la especificación del formato; se ve en exploradores de ROM y gestores
  de guardados.

### Herramientas

```console
python3 tools/x3_content_patch.py --check mmx3.sfc   # qué haría, sin escribir
python3 tools/x3_content_patch.py --apply mmx3.sfc   # copia parcheada + checksum
python3 tools/test_content_patch.py                  # 12 pruebas, sin ROM real
```

`--apply` escribe `<rom>.zerohistory.sfc` con el checksum SNES recalculado y no
toca el original. Si un parche no corresponde al archivo, sale con error y no
escribe nada.

### Contenido en la app

Nuevo botón **Historia y jefes**: la Bóveda Ω, los ocho mavericks con su arma,
el anillo de debilidades y las reglas de las cápsulas. Es texto de la app
(`LoreActivity`), no del cartucho, y así se dice en la propia pantalla.

### Lo que sigue sin insertarse

Guion, jefes, mapas y música dentro del juego necesitan glifos y direcciones
derivadas del dump real (mapa carácter → byte de la fuente de X3, bloques de
texto, tiles comprimidos). Adivinarlos escribiría basura: el mecanismo está
listo, los datos no. `docs/CONTENIDO.md` explica el formato, las reglas y el
trabajo pendiente.

## Arreglos y detalles

- La prueba de contenido en CI corre con las demás
  (`python3 tools/test_content_patch.py`).
- Los tres `.zip` de escritorio y el APK incluyen `content/`: sin la tabla el
  motor no aplica ningún parche.
- `versionCode 5`, `versionName 0.0.5`.
