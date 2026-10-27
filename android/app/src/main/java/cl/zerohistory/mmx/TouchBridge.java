package cl.zerohistory.mmx;

/**
 * Puente entre la capa táctil (Java) y el módulo C probado
 * (src/platform/android/x3_touch_controls.c).
 *
 * Todas las funciones delegan en el tracker C, que es el que decide qué bits
 * quedan apretados. Java no mantiene estado de entrada propio a propósito: la
 * lógica de varios dedos ya está resuelta y probada de un solo lado.
 */
final class TouchBridge {
    private TouchBridge() {}

    static native void nativeDownTouch(long id, float nx, float ny, int bitsFromJava);
    static native void nativeMoveTouch(long id, float nx, float ny);
    static native void nativeUpTouch(long id);
    static native void nativeReleaseAll();

    /** Rebuild the C layout for the real surface (16:9, 19.5:9, 20:9, ...). */
    static native void nativeSetAspect(float aspect);

    /** Máscara de 12 bits vigente, para que el host la consuma por frame. */
    static native int nativeMask();

    static {
        System.loadLibrary("x3touch");
    }
}
