// Actividad principal del port Android.
//
// Extiende SDLActivity para reutilizar el host gráfico y de audio de SDL2, y
// agrega dos cosas que el host de escritorio no necesita:
//
//   1. La capa táctil (TouchOverlay).
//   2. Ocultar esa capa cuando se conecta un mando externo.
//
// IMPORTANTE: el binario nativo tiene que exponer una función de entrada
// (JNI o SDL hint) para que la máscara que produce TouchOverlay llegue al
// guest. Hoy el estado del pad del host es `static` en host_main.c; ver
// docs/ANDROID.md y docs/ESTADO.md. Hasta que ese punto de inyección exista,
// esta actividad compila pero los toques no llegan al juego.

package cl.zerohistory.mmx;

import android.os.Bundle;
import android.view.InputDevice;
import android.view.MotionEvent;
import android.view.View;

import org.libsdl.app.SDLActivity;

public class MainActivity extends SDLActivity {
    private TouchOverlay overlay;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        overlay = new TouchOverlay(this);
        addContentView(overlay, new android.view.ViewGroup.LayoutParams(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                android.view.ViewGroup.LayoutParams.MATCH_PARENT));
        updateOverlayVisibility();
    }

    /** Oculta los botones táctiles cuando hay un mando externo conectado. */
    private void updateOverlayVisibility() {
        if (overlay == null) return;
        boolean padConnected = false;
        for (int id : InputDevice.getDeviceIds()) {
            InputDevice dev = InputDevice.getDevice(id);
            if (dev == null) continue;
            int sources = dev.getSources();
            boolean gamepad =
                    (sources & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD;
            boolean joystick =
                    (sources & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK;
            if (gamepad || joystick) {
                padConnected = true;
                break;
            }
        }
        overlay.setVisibility(padConnected ? View.GONE : View.VISIBLE);
    }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent event) {
        if ((event.getSource() & InputDevice.SOURCE_JOYSTICK) != 0) {
            updateOverlayVisibility();
        }
        return super.dispatchGenericMotionEvent(event);
    }

    @Override
    public boolean dispatchKeyEvent(android.view.KeyEvent event) {
        updateOverlayVisibility();
        return super.dispatchKeyEvent(event);
    }

    @Override
    protected void onPause() {
        if (overlay != null) overlay.releaseAll();
        super.onPause();
    }
}
