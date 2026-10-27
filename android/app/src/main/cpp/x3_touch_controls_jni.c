/* Puente JNI de la capa táctil.
 *
 * Traduce las llamadas de TouchBridge.java al tracker de
 * x3_touch_controls.c y publica una máscara de 12 bits que el host puede leer
 * una vez por frame con x3_touch_current_mask().
 *
 * El host todavía no la lee: el estado del pad es `static` en
 * snesrecomp/runner/src/desktop/host_main.c y no hay API de inyección.
 * Ver docs/ANDROID.md § "Estado real de esta versión".
 */
#include <jni.h>
#include <stdint.h>

#include "x3_touch_controls.h"

/* Una sola instancia: hay una sola pantalla táctil por proceso. */
static X3TouchLayout g_layout;
static X3TouchTracker g_tracker;
static int g_ready;

/* El layout se arma acá y no en Java para que la geometría tenga una única
 * fuente de verdad (el mismo .c que corren los tests de escritorio). */
static void ensure_ready(void) {
  if (g_ready) return;
  X3Touch_DefaultLayout(&g_layout);
  X3Touch_Reset(&g_tracker);
  g_ready = 1;
}

/* Consumido por el host una vez por frame. */
uint16_t x3_touch_current_mask(void) {
  return g_ready ? X3Touch_Active(&g_tracker) : 0;
}

/* Llamado por el host cuando un mando externo toma el control. */
void x3_touch_release_all(void) {
  if (!g_ready) return;
  X3Touch_Reset(&g_tracker);
}

JNIEXPORT void JNICALL
Java_cl_zerohistory_mmx_TouchBridge_nativeDownTouch(JNIEnv *env, jclass cls,
                                                    jlong id, jfloat nx,
                                                    jfloat ny, jint bits) {
  (void)env;
  (void)cls;
  (void)bits; /* el tracker recalcula: una sola fuente de verdad */
  ensure_ready();
  X3Touch_Down(&g_tracker, (int64_t)id, &g_layout, nx, ny);
}

JNIEXPORT void JNICALL
Java_cl_zerohistory_mmx_TouchBridge_nativeMoveTouch(JNIEnv *env, jclass cls,
                                                    jlong id, jfloat nx,
                                                    jfloat ny) {
  (void)env;
  (void)cls;
  (void)id;
  (void)nx;
  (void)ny;
  /* Deslizar no cambia el estado: la entrada se latchea al tocar y se suelta
   * al levantar el dedo. Un pulgar que se corre no debe cortar el salto. */
}

JNIEXPORT void JNICALL
Java_cl_zerohistory_mmx_TouchBridge_nativeUpTouch(JNIEnv *env, jclass cls,
                                                  jlong id) {
  (void)env;
  (void)cls;
  ensure_ready();
  X3Touch_Up(&g_tracker, (int64_t)id);
}

JNIEXPORT void JNICALL
Java_cl_zerohistory_mmx_TouchBridge_nativeReleaseAll(JNIEnv *env, jclass cls) {
  (void)env;
  (void)cls;
  x3_touch_release_all();
}

JNIEXPORT void JNICALL
Java_cl_zerohistory_mmx_TouchBridge_nativeSetAspect(JNIEnv *env, jclass cls,
                                                     jfloat aspect) {
  (void)env;
  (void)cls;
  ensure_ready();
  X3Touch_SetAspect(&g_layout, aspect);
}

JNIEXPORT jint JNICALL
Java_cl_zerohistory_mmx_TouchBridge_nativeMask(JNIEnv *env, jclass cls) {
  (void)env;
  (void)cls;
  return (jint)x3_touch_current_mask();
}
