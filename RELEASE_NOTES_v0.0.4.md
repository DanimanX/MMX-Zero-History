## Por qué se juega el Mega Man X3 original

No es un fallo de la app ni de la instalación: es lo que este repositorio
contiene hoy.

El APK es una **recompilación** del cartucho. Ejecuta los bytes de tu propio
dump y no modifica su contenido: la identidad del ROM se verifica y se exige
(`65b03268…f1d7`). La historia de la Bóveda Ω, los ocho mavericks, las cápsulas
errantes, el guion en chileno y la banda sonora están **diseñados y
documentados, no insertados** en el juego. Eso está dicho desde la 0.0.1 en el
README («Qué **no** es esto») y en `docs/ESTADO.md`; esta versión lo hace
visible dentro de la app para que nadie tenga que adivinarlo.

### Lo que sí cambia y se puede comprobar

- **Nombre, icono y placa de arranque** propios.
- **Campo 16:9** de 342×224 con HUD anclado a los lados, columnas nuevas de BG1
  y BG2 y ventanas de enemigos ensanchadas.
- **Pantalla de entrada** con importación verificada del ROM y diagnóstico: la
  versión de la build y el campo que el motor eligió (`build=0.0.4`,
  `video: 342x224 (widescreen=1, …)`), leídos de `native.log`.

Para confirmarlo en un teléfono:

```console
adb pull /sdcard/Android/data/cl.zerohistory.mmx/files/native.log
grep -E "^\[mmx\] (build|video)" native.log
```

Si `video:` dice `342x224 (widescreen=1 …)`, el 16:9 está activo y esa es la
build del proyecto. Si dice `256x224 (widescreen=0 …)`, revisá
`config.ini` (`[Graphics] Widescreen = 1`).

### Lo que falta para que el juego cambie de verdad

El motor fijado ya trae el mecanismo: `snes_text_xlate` aplica parches de ROM,
RAM y VRAM en memoria del invitado, con tabla de glifos y guardas de contenido,
sin tocar el dump. Ningún puerto de este repositorio lo inicializa todavía.
Hacerlo exige, en orden:

1. Derivar del ROM la tabla de glifos y las direcciones de los bloques de texto
   y de las pantallas que se quieran reemplazar.
2. Escribir la tabla de parches con `source`/`target` y guardas para no pisar
   pantallas que comparten tiles.
3. Enlazar `snes_text_xlate_init_c` en el host y empaquetar la tabla como
   recurso del mod.

Eso cubre guion y arte de pantallas; jefes y mapas nuevos siguen siendo el
trabajo de meses descrito en `docs/ESTADO.md`.

## Android: diagnóstico visible

- La pantalla de entrada muestra ahora, bajo el estado del ROM, la sección
  **«Qué cambia esta build y qué no»** y las dos líneas del motor
  (`build=`, `video:`).
- `src/x3_display.c` registra una vez por corrida el ancho de campo elegido y
  el tamaño del drawable; `src/main.c` registra la versión de la build.
- El límite de 342 px sigue cubierto por `tools/test_display_width.sh`.

## APK

- `MMXZeroHistory-android-arm64-v8a.apk` (teléfonos) y
  `MMXZeroHistory-android-x86_64.apk` (emuladores).
- `versionCode 4`, `versionName 0.0.4`, firmados.

## Límites conocidos, sin cambios

- El envío de toques al guest sigue pendiente: para jugar hace falta un mando
  Bluetooth.
- El catálogo de mods no se carga en Android (el host lo resuelve contra
  `/system/bin`); el 16:9 viaja por `config.ini`.
- Todo corre en intérprete LLE: falta medir el rendimiento en un ARM real.
