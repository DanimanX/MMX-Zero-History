# Android — controles táctiles y mando externo

## Lo que hay hoy en el motor

El host de escritorio de `snesrecomp` **ya trae soporte de mando** por
`SDL_GameController`: Xbox, DualShock/DualSense y 8BitDo funcionan sin
configuración, con zona muerta y gestos de rewind/launcher configurables
(`snesrecomp/runner/src/desktop/config.h`, `[Controller]`).

El runner también tiene rutas `__ANDROID__` (directorio de trabajo en el
almacenamiento externo de la app, backend de render SDL en vez de OpenGL de
escritorio). Lo que **no** trae es una capa táctil.

## Diseño de los controles táctiles

- **D-pad** en la esquina inferior izquierda, cuatro botones discretos (no un
  stick virtual: X3 se juega con D-pad y un stick analógico mapeado a
  direcciones digitales se siente mal en plataformas).
- **Cuatro botones SNES** en rombo abajo a la derecha: Y arriba, B derecha,
  A abajo, X izquierda, igual que el layout de SNES.
- **L y R** como hombros arriba de los botones.
- **start** centrado arriba de la zona de juego, chico, para no tocarlo por
  accidente.
- **Zona muerta y opacidad** configurables; **espejado** izquierda/derecha
  para jugadores zurdos.
- **Auto-ocultar**: cuando se conecta un mando externo, la capa táctil se
  oculta sola (el mando externo es estrictamente mejor). Se puede forzar el
  contrario desde ajustes.
- **Multi-touch real**: agarrar dirección y saltar al mismo tiempo es el caso
  normal, no la excepción. Cada dedo se sigue por `SDL_FingerID` y se mapea al
  botón que estaba bajo ese dedo en el momento del toque.

## Estructura

```
android/
  settings.gradle            proyectos incluidos
  build.gradle               configuración raíz
  gradle.properties
  app/
    build.gradle             empaqueta el binario nativo + assets
    src/main/AndroidManifest.xml
    src/main/java/cl/zerohistory/mmx/MainActivity.java
    src/main/java/cl/zerohistory/mmx/TouchOverlay.java   (implementación)
    src/main/cpp/x3_touch_controls.c                     (contrato de entrada)
    src/main/assets/         ROM del usuario, no incluida
```

## Cómo se construye

Requisitos: Android SDK con NDK r27, CMake 3.20+, y el mismo árbol de
submódulos que el build de escritorio.

```bash
export ANDROID_NDK_HOME=$HOME/Android/Sdk/ndk/27.0.12077973
cmake -S . -B build-android -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 \
  -DSNESRECOMP_SDL_BACKEND=SDL2
cmake --build build-android --target MegaManX3SNESRecomp
cd android && ./gradlew assembleDebug
```

El `.so` que produce CMake se copia a `android/app/src/main/jniLibs/arm64-v8a/`.

## Estado real de esta versión

**El camino Android está especificado y andamiado, no verificado.** En la
máquina donde se preparó esta versión 0.0.1 no hay Android SDK ni NDK, así que:

- `android/` existe con la estructura de proyecto y el manifiesto;
- `src/main/cpp/x3_touch_controls.c` define el contrato de entrada (qué botón,
  qué dedo, qué zona) y la geometría por defecto, compilable en el host de
  escritorio para pruebas;
- la actividad Java y la capa táctil están escritas, pero **nunca se
  ejecutaron en un dispositivo**;
- el job de CI de Android es **manual** (`workflow_dispatch`) y está marcado
  como experimental: no bloquea la construcción de escritorio.

La capa táctil necesita además un punto de inyección de entrada en el host de
`snesrecomp`, que hoy no existe como API pública (el estado del pad es
`static` en `host_main.c`). Ese es el primer trabajo pendiente, y está
documentado en [`ESTADO.md`](ESTADO.md) con el archivo y la función exactos.

## Mando externo

Como el motor ya soporta gamepads por SDL, la versión de escritorio
(Linux/Windows/macOS) tiene soporte real hoy. En Android el mando externo entra
por el mismo `SDL_GameController`, siempre que la actividad reenvíe los
eventos de `KeyEvent`/`MotionEvent` a SDL, que es exactamente lo que hace
`MainActivity.java` en este andamiaje.
