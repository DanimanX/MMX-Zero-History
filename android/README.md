# Android — andamiaje

Este directorio es el proyecto Android de **MMX Zero History**. Es un
**andamiaje**: la estructura está, compila conceptualmente, pero **no se ha
ejecutado en un dispositivo ni en CI**. Ver
[`docs/ANDROID.md`](../docs/ANDROID.md) y [`docs/ESTADO.md`](../docs/ESTADO.md).

## Piezas

- `app/src/main/java/cl/zerohistory/mmx/MainActivity.java` — actividad SDL;
  oculta la capa táctil cuando hay un mando conectado.
- `app/src/main/java/cl/zerohistory/mmx/TouchOverlay.java` — dibujo del pad y
  reenvío de toques, dedo por dedo.
- `app/src/main/java/cl/zerohistory/mmx/TouchBridge.java` — puente JNI.
- `app/src/main/cpp/x3_touch_controls_jni.c` — implementación JNI; toda la
  lógica delega en el módulo C probado.
- La geometría y el multi-touch viven en
  `../src/platform/android/x3_touch_controls.c`, que **sí** está probado:
  `bash tools/test_touch_controls.sh`.

## Lo que falta para que sea jugable

1. Un punto de inyección de entrada en el host de `snesrecomp`. Hoy el estado
   del pad es `static` en `runner/src/desktop/host_main.c`; hay que exponer una
   función tipo `snesrecomp_desktop_set_pad_mask(uint16_t)` y llamarla desde
   `x3_touch_current_mask()`.
2. Copiar `libMegaManX3SNESRecomp.so` (producido por CMake para `arm64-v8a`) a
   `app/src/main/jniLibs/arm64-v8a/`.
3. Vendorizar SDL2 para Android y enlazarlo al módulo `:sdl2` (el
   `app/build.gradle` ya tiene el `implementation` comentado).
4. Firma del APK en CI con un keystore del entorno, nunca del repositorio.

## Generar el wrapper de Gradle

El repositorio no incluye `gradle/wrapper/gradle-wrapper.jar` para no
commitear un binario opaco. Se genera una vez:

```bash
cd android && gradle wrapper --gradle-version 8.7
```
