## 16:9 en todas las versiones

- **16:9 activo por defecto** en Linux, Windows, macOS y Android. El motor
  renderiza 342×224 píxeles reales y completa las columnas nuevas con los
  tiles auténticos de BG1/BG2; el HUD del jugador se ancla a la izquierda y el
  del jefe a la derecha. Se puede volver a 4:3 desde el launcher
  (Mods → Widescreen).
- **APK de Android** (`MMXZeroHistory-android-arm64-v8a.apk`, Android 7.0+).
  Es un host LLE **sin código derivado del ROM**: el jugador copia su
  `mmx3.sfc` a `Android/data/cl.zerohistory.mmx/files/` y la app lo carga al
  arrancar. Incluye el catálogo de mods y mando externo por
  `SDL_GameController`.
  La capa táctil se dibuja y produce la máscara de 12 bits, pero **el punto de
  inyección al guest sigue pendiente** (el estado del pad es privado del host):
  por ahora se juega con un mando Bluetooth.
- **Android de borde a borde**: modo inmersivo pegajoso,
  `layoutInDisplayCutoutMode = shortEdges` y `sensorLandscape`. En pantallas
  19.5:9 o 20:9 la imagen sigue siendo 16:9 centrada, no estirada.
- **Controles táctiles cuadrados en cualquier aspecto**: la geometría se mide
  en unidades del lado corto (16:9, 19.5:9, 20:9 y 4:3), con insets seguros
  para el notch y la barra de gestos.
- **Assets rediseñados en 16:9**: banner, mapa de etapas, cápsulas, línea de
  tiempo y arte de Android a 1920×1080; placa de arranque e icono de launcher
  nuevos, generados por `tools/make_brand_art.py`.

## Correcciones de la línea base

- Corrige un bug de progresión en widescreen que podía hacer caer a X por el
  piso en una transición de escalera o atravesar la pared equivocada durante
  una secuencia scripteada.
- Corrige corrupción de pila durante la pelea con el jefe de Doppler, que
  podía causar slowdown severo, audio acelerado, corrupción visual o softlock
  cuando el jefe atacaba.
- Actualiza el runtime fijado de `snesrecomp` a la última revisión probada de
  `main`.

## Instalación

- **Escritorio**: descomprimí el zip completo y ejecutá
  `MegaManX3SNESRecomp`. El ejecutable es un *setup host*: la primera vez te
  pide tu ROM y recompila. El catálogo de mods viaja en `mods/`.
- **Android**: instalá el APK y copiá tu `mmx3.sfc` al directorio de archivos
  de la app (ver arriba).
- Se requiere un dump verificado de Mega Man X3 (USA). No se incluye.

## Notas de firma

El APK se firma con una clave de release. Si el repositorio define
`MMX_KEYSTORE_BASE64`, `MMX_KEYSTORE_PASSWORD` y `MMX_KEY_PASSWORD`, CI usa esa
clave estable; si no, genera una efímera para esa corrida. Una clave distinta
obliga a desinstalar la versión anterior antes de actualizar.
