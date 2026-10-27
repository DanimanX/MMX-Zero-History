# Android — APK, 16:9 y controles

## Qué es el APK

`MMXZeroHistory-android-arm64-v8a.apk` es un **host LLE sin código derivado
del ROM**. El binario enlaza `src/interpreter_only/dispatch_stub.c` (tablas AOT
vacías) y `src/gen_stubs.c` lo documenta desde el bring-up: sin cobertura AOT,
el intérprete ejecuta los bytes reales del cartucho. El ROM nunca viaja en el
APK; lo aporta el jugador.

Eso es distinto del *setup host* de escritorio (`SNESRECOMP_SETUP_HOST=ON`),
que se niega a bootear y solo abre el asistente de regeneración. El APK sí
arranca el juego, a costa de velocidad: todo corre en el intérprete, sin los
cuerpos AOT que aceleran la build de escritorio.

## Instalar

1. Instalá el APK (Android 7.0+, arm64-v8a).
2. Copiá tu `mmx3.sfc` a:

   ```console
   adb push mmx3.sfc /sdcard/Android/data/cl.zerohistory.mmx/files/mmx3.sfc
   ```

   El host hace `chdir` a ese directorio al arrancar y busca `mmx3.sfc` ahí
   (`FindRomBesideExe`, `MMX_ROM_FILE`).

3. Abrí la app. `AssetInstaller` copia el catálogo de mods desde `assets/mods`
   al mismo directorio, así que el paquete Widescreen existe cuando el motor
   resuelve la selección por defecto.

## 16:9

- La actividad entra en modo inmersivo pegajoso (`WindowInsetsController` en
  API 30+, flags clásicos abajo) y dibuja bajo el recorte de pantalla
  (`layoutInDisplayCutoutMode = shortEdges`, API 28+).
- `sensorLandscape` + `resizeableActivity` aceptan 16:9, 19.5:9 y 20:9. El
  motor calcula el ancho de campo desde el drawable y lo limita a 342 px, así
  que en pantallas más altas la imagen se centra con barras laterales en vez
  de estirarse.
- La capa táctil mide sus teclas en unidades del lado corto
  (`X3Touch_SetAspect` en C, `TouchOverlay.rectFor` en Java): las teclas siguen
  cuadradas en cualquier aspecto. Los insets seguros del notch y de la barra
  de gestos se aplican antes de dibujar y de hacer hit-test.
- El paquete `megaman-x3.enhancement.widescreen` viene con
  `default_enabled = true` desde la 0.0.2.

## Controles

- **Mando externo**: funciona hoy. SDL lo detecta y `MainActivity` oculta la
  capa táctil cuando hay un `SOURCE_GAMEPAD` o `SOURCE_JOYSTICK` conectado.
- **Capa táctil**: se dibuja, calcula la máscara de 12 bits y multi-touch
  (latcheo al deslizar, dos dedos en el mismo botón, tabla de dedos), pero
  **todavía no llega al guest**. El estado del pad es `static` en
  `snesrecomp/runner/src/desktop/host_main.c` y no hay API de inyección. El
  puente JNI expone `x3_touch_current_mask()`; falta que el host la consuma.
  Mientras tanto, para jugar en el teléfono hace falta un mando Bluetooth.

## Estructura

```
android/
  settings.gradle            proyectos incluidos
  build.gradle               configuración raíz (AGP 8.5.2)
  app/
    build.gradle             empaqueta el .so, assets, firma
    src/main/AndroidManifest.xml
    src/main/java/cl/zerohistory/mmx/MainActivity.java
    src/main/java/cl/zerohistory/mmx/TouchOverlay.java
    src/main/java/cl/zerohistory/mmx/AssetInstaller.java
    src/main/cpp/               capa táctil + JNI (libx3touch.so)
    src/main/assets/            catálogo de mods (generado); el ROM no se commitea
    src/main/res/               splash 16:9, icono adaptativo
```

## Cómo se construye

Requisitos: Android SDK 34, NDK r27 (`27.0.12077973`), CMake 3.22, Ninja,
JDK 17 y Gradle 8.7+.

```bash
export ANDROID_SDK_ROOT=$HOME/Android/Sdk
export ANDROID_NDK_HOME=$ANDROID_SDK_ROOT/ndk/27.0.12077973
export JAVA_HOME=/ruta/a/jdk-17
bash tools/build_android.sh arm64-v8a
```

El script:

1. configura CMake con el toolchain del NDK, `MMX_LLE_ONLY=ON` y SDL3;
2. compila `libMegaManX3SNESRecomp.so` (el juego, con SDL3 estático dentro);
3. copia el `.so` a `android/app/src/main/jniLibs/<abi>/`;
4. copia las clases Java de SDL desde el árbol de SDL3;
5. copia `mods/preloaded/packages` a `assets/mods`;
6. firma y corre `gradle assembleRelease`.

Salida: `dist/MMXZeroHistory-android-<abi>.apk`.

La firma se toma de `MMX_KEYSTORE` + `MMX_KEYSTORE_PASSWORD` +
`MMX_KEY_PASSWORD`; si no existen, el script genera una clave efímera fuera
del repositorio. Para publicar actualizaciones encima de una instalación
previa hay que reusar la misma clave.

## Estado real

- El APK **se compila, se firma y se verifica su empaquetado** en esta máquina
  (SDK 34 / NDK r27): `aapt dump badging` reporta `versionCode 2`,
  `versionName 0.0.2`, `native-code: arm64-v8a`; `apksigner` valida la firma; y
  el APK contiene `libMegaManX3SNESRecomp.so`, `assets/mods/...` y la placa de
  arranque.
- **No se ejecutó en un dispositivo**: no hay teléfono ni emulador en el
  entorno de desarrollo. La primera corrida real queda pendiente y es lo que
  hay que mirar antes de prometer jugabilidad.
- El envío de toques al guest sigue pendiente (ver arriba).
- El job `Android` de CI corre el mismo `tools/build_android.sh`; `Release`
  lo usa para adjuntar el APK a la etiqueta.
