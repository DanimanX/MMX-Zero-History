# Android — APK, 16:9 y controles

## Qué es el APK

`MMXZeroHistory-android-arm64-v8a.apk` es un **host LLE sin código derivado
del ROM**. El binario enlaza `src/interpreter_only/dispatch_stub.c` (tablas AOT
vacías) y `src/gen_stubs.c` lo documenta desde el bring-up: sin cobertura AOT,
el intérprete ejecuta los bytes reales del cartucho. El ROM nunca viaja en el
APK; lo aporta el jugador.

Eso es distinto del *setup host* de escritorio (`SNESRECOMP_SETUP_HOST=ON`),
que se niega a bootear y solo abre el asistente de regeneración. El APK sí
arranca el juego, a costa de velocidad: todo corre en el intérprete.

## Flujo de arranque (v0.0.3)

```
RomSetupActivity (launcher)
  ├─ falta el ROM        → pantalla con instrucciones + selector SAF
  ├─ SHA-256 no coincide → lo dice, no arranca nada
  └─ ROM verificado      → MainActivity (SDL + motor)
                              └─ al volver, muestra native.log si se cortó
```

- **`RomSetupActivity`** es el launcher de la app. Antes la actividad del motor
  era la principal, así que abrir la app sin `mmx3.sfc` hacía que `main`
  devolviera 1 y todo se cerrara en silencio: ese es el "se abre y se cierra"
  de la 0.0.2.
- **`RomStore`** importa el dump con `ACTION_OPEN_DOCUMENT`, calcula el SHA-256
  y solo mueve el archivo a su lugar definitivo si coincide con
  `65b03268…f1d7`. Una cabecera de copiador de 512 bytes se descarta.
- **`AssetInstaller`** deja listo el directorio de trabajo antes de que exista
  el hilo nativo: escribe `cwd.txt` (el host lo lee y hace `chdir`),
  `config.ini` (con `Widescreen = 1`) y el catálogo de mods.

## 16:9

- La actividad del motor entra en modo inmersivo pegajoso
  (`WindowInsetsController` en API 30+, flags clásicos abajo) y dibuja bajo el
  recorte de pantalla (`layoutInDisplayCutoutMode = shortEdges`, API 28+).
- El campo se calcula desde el tamaño real del drawable y **se topa en 342 px**
  (`src/x3_display.c`, `MMX_MAX_FRAME_WIDTH`). Es la configuración que este
  port midió: 342×224 con relación de píxel 7:6. En un teléfono 19.5:9 el
  resultado es 16:9 centrado con barras, no un campo de 416 px que nadie
  validó. `tools/test_display_width.sh` fija ese contrato.
- Los controles táctiles se miden en unidades del lado corto
  (`X3Touch_SetAspect` en C, `TouchOverlay.rectFor` en Java), así que las teclas
  siguen cuadradas en cualquier aspecto. Los insets del notch y de la barra de
  gestos se aplican antes de dibujar y de hacer hit-test.

## Qué se juega (y qué no)

El APK ejecuta el cartucho del jugador tal cual: recompilado, verificado e
intacto. La historia nueva, los jefes, las cápsulas, el guion en chileno y la
banda sonora están diseñados en `docs/` y **no insertados** en el juego. Lo que
el proyecto aporta en pantalla es el nombre, el icono, la placa de arranque y
el campo 16:9. La pantalla de entrada lo dice explícitamente y muestra la
versión de la build y el ancho de campo elegido, leídos de `native.log`
(`[mmx] build=…`, `[mmx] video: 342x224 (widescreen=1, …)`).

Vía para cambiarlo sin tocar el cartucho: `snes_text_xlate`
(`snesrecomp/runner/src/snes_text_xlate.cpp`) aplica parches de ROM/RAM/VRAM en
memoria del invitado. No está inicializado por ningún puerto todavía; necesita
las tablas de glifos y las direcciones reales del ROM.

## Configuración y diagnóstico

Todo lo que el host escribe vive en el directorio de trabajo de la app
(`/storage/emulated/0/Android/data/cl.zerohistory.mmx/files`):

| archivo | qué es |
|---|---|
| `mmx3.sfc` | el dump del jugador (2 MiB sin cabecera) |
| `config.ini` | se copia de `assets/config.default.ini` si no existe |
| `keybinds.ini`, `saves/` | generados por el motor |
| `native.log` | stdout/stderr del proceso nativo (Android no tiene stderr) |
| `native.prev.log` | la corrida anterior, para no perder la evidencia |
| `mods/preloaded/…` | catálogo de mods extraído del APK |

Para sacarlos de un teléfono:

```console
adb pull /sdcard/Android/data/cl.zerohistory.mmx/files/native.log
```

## Controles

- **Mando externo**: funciona hoy. SDL lo detecta y `MainActivity` oculta la
  capa táctil cuando hay un `SOURCE_GAMEPAD` o `SOURCE_JOYSTICK` conectado.
- **Capa táctil**: se dibuja, calcula la máscara de 12 bits y multi-touch
  (latcheo al deslizar, dos dedos en el mismo botón, tabla de dedos), pero
  **todavía no llega al guest**. El estado del pad es `static` en
  `snesrecomp/runner/src/desktop/host_main.c` y no hay API de inyección. El
  puente JNI expone `x3_touch_current_mask()`; falta que el host la consuma.

## Estructura

```
android/
  app/build.gradle             empaqueta el .so, assets, firma, versionCode
  src/main/AndroidManifest.xml
  src/main/java/cl/zerohistory/mmx/MainActivity.java      SDL + motor
  src/main/java/cl/zerohistory/mmx/RomSetupActivity.java  launcher
  src/main/java/cl/zerohistory/mmx/RomStore.java          import + SHA-256
  src/main/java/cl/zerohistory/mmx/AssetInstaller.java    cwd, config, mods
  src/main/java/cl/zerohistory/mmx/TouchOverlay.java
  src/main/cpp/                capa táctil + JNI (libx3touch.so)
  src/main/assets/             config.default.ini, catálogo de mods (generado)
  src/main/res/                splash 16:9, icono adaptativo, temas
```

## Cómo se construye

Requisitos: Android SDK 34, NDK r27 (`27.0.12077973`), CMake 3.22, Ninja,
JDK 17 y Gradle 8.7+.

```bash
export ANDROID_SDK_ROOT=$HOME/Android/Sdk
export ANDROID_NDK_HOME=$ANDROID_SDK_ROOT/ndk/27.0.12077973
export JAVA_HOME=/ruta/a/jdk-17
bash tools/build_android.sh arm64-v8a    # teléfonos
bash tools/build_android.sh x86_64       # emuladores
```

El script configura CMake con `MMX_LLE_ONLY=ON` y SDL3, compila
`libMegaManX3SNESRecomp.so`, lo copia a `jniLibs/`, trae las clases Java de
SDL, copia el catálogo de mods a `assets/mods`, genera/usa un keystore y corre
`gradle assembleRelease`. Salida: `dist/MMXZeroHistory-android-<abi>.apk`.

## Estado real (v0.0.4)

Verificado en un emulador Android 14 (x86_64, KVM):

- la app abre y **queda abierta** en la pantalla de entrada;
- el selector de archivos del sistema importa un `mmx3.sfc`, y un archivo con
  SHA-256 distinto se rechaza sin dejar restos (`mmx3.sfc.incoming` se borra);
- con un dump presente el motor arranca: `SDL init ok`, `renderer
  initialized: sdl`, `first frame simulated` y heartbeat a 60 fps;
- el ancho de campo con `Widescreen = 1` es 342 (16:9), no 256.

Sin verificar, y por qué:

- **Una partida real**: no hay dump en el repositorio. Con un archivo aleatorio
  el guest termina en un bucle de `BRK` y el proceso muere; eso es el ROM, no
  la app.
- **El catálogo de mods en Android**: el host resuelve `mods/preloaded`
  relativo al ejecutable (`/system/bin`, de solo lectura) cuando no se le pasa
  `--config`; con `--config` el proceso muere dentro de
  `snes_mod_runtime_commit_c` (probado en el emulador). Por eso el 16:9 viaja
  en `config.ini` y el catálogo se extrae pero no se usa. Es un bug del host
  que hay que arreglar río arriba, no en este repositorio.
- **Rendimiento**: todo corre en el intérprete LLE. En un teléfono real hay que
  medirlo; el emulador x86_64 con KVM no es representativo de un ARM.
