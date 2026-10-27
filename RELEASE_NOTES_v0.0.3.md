## Android: la app ya no se cierra al abrir

La 0.0.2 instalaba y cerraba en el acto. La causa era concreta: la actividad
principal era la del motor, el host no encontraba el ROM, `main` devolvía 1 y
Android mataba la tarea sin dejar rastro en pantalla ni en `logcat`.

- **Pantalla de entrada nueva** (`RomSetupActivity`). Si falta el ROM lo dice y
  ofrece **Elegir mi mmx3.sfc** con el selector del sistema; si el SHA-256 no
  coincide lo explica en vez de arrancar con datos basura.
- **Importador con verificación** (`RomStore`): copia a un archivo temporal,
  calcula el SHA-256, descarta una cabecera de copiador SMC de 512 bytes y solo
  entonces reemplaza el `mmx3.sfc` definitivo.
- **Diagnóstico visible**: el motor escribe `native.log` (y `native.prev.log`
  con la corrida anterior) en la carpeta de la app, y al volver de una corrida
  cortada la pantalla de entrada muestra el final del registro.
- **Directorio de trabajo correcto**: el proceso nativo arranca en `/`, así
  que `config.ini`, `keybinds.ini`, `saves/` y el log caían donde nadie los
  buscaba. Ahora la app le indica la carpeta antes de arrancar el motor.

## 16:9 en Android

- `config.ini` por defecto con `Widescreen = 1`, copiado desde los assets solo
  si el jugador todavía no tiene uno.
- El campo se topa en **342×224** (`MMX_MAX_FRAME_WIDTH`): es la configuración
  medida por este port. Una pantalla 19.5:9 o 20:9 agrega barras laterales en
  vez de estirar el campo a 416 px sin validar.
- Nuevo `tools/test_display_width.sh`: 342 con cualquier ventana de 16:9 o más
  ancha, 256 (4:3 auténtico) cuando la ventana no da para el campo ancho.

## APK

- `MMXZeroHistory-android-arm64-v8a.apk` para teléfonos.
- `MMXZeroHistory-android-x86_64.apk` para emuladores.
- `versionCode 3`, `versionName 0.0.3`, firmado, con `assets/config.default.ini`
  y el catálogo de mods.

Verificado en un emulador Android 14 (x86_64): la app abre y queda abierta, el
importador rechaza un dump con SHA-256 equivocado, y con un archivo presente el
motor llega a `first frame simulated`. **No hay partida real verificada**: este
repositorio no incluye el ROM y una captura de la etapa 1 necesita tu dump
(`tools/capture_android.sh`).

## Escritorio

- Los tres `.zip` (Linux, Windows, macOS) siguen publicándose igual.
- El límite de 342 px también aplica al escritorio, así que un monitor
  ultrawide muestra 16:9 centrado en vez de un campo más ancho sin validar.

## Limitaciones conocidas

- El envío de toques al guest sigue pendiente: la capa táctil dibuja y calcula
  la máscara, pero el estado del pad es privado del host. Con mando Bluetooth
  sí se juega.
- El catálogo de mods no se carga en Android: el host lo resuelve relativo a
  `/system/bin`. El 16:9 viaja por `config.ini`, no por el paquete.
