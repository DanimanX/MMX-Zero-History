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

import android.os.Build;
import android.os.Bundle;
import android.view.InputDevice;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;

import org.libsdl.app.SDLActivity;

public class MainActivity extends SDLActivity {
    private TouchOverlay overlay;

    /** SDL3 se enlaza estáticamente dentro del .so del juego (ver
     *  tools/build_android.sh), así que la única librería que hay que cargar
     *  es la nuestra. El JNI de SDL viaja con ella. */
    @Override
    protected String[] getLibraries() {
        return new String[] { "MegaManX3SNESRecomp" };
    }

    /** Con SDL_MAIN_HANDLED el host conserva `main`; no hay `SDL_main`. */
    @Override
    protected String getMainFunction() {
        return "main";
    }

    /**
     * Argumentos del host. `--rom` fija la ruta del dump, así el motor no
     * depende de que el proceso herede el directorio de trabajo correcto.
     *
     * No se pasa `--config`: con ese argumento el host busca el catálogo de
     * mods relativo al cwd, y ese camino aborta el proceso en Android (ver
     * docs/ANDROID.md). El 16:9 viaja en el config.ini por defecto.
     */
    @Override
    protected String[] getArguments() {
        return new String[] { "--rom", RomStore.rom(this).getAbsolutePath() };
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // Antes de super.onCreate: el hilo nativo arranca desde SDLActivity y
        // el runtime de mods necesita el catálogo ya en el directorio de
        // trabajo (almacenamiento externo de la app).
        AssetInstaller.install(this);
        super.onCreate(savedInstanceState);
        applyEdgeToEdge();
        overlay = new TouchOverlay(this);
        addContentView(overlay, new android.view.ViewGroup.LayoutParams(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                android.view.ViewGroup.LayoutParams.MATCH_PARENT));
        updateOverlayVisibility();
    }

    /**
     * 16:9 a pantalla completa: la partida se dibuja hasta los bordes, incluso
     * si hay notch o isla de cámara. El motor calcula el ancho de campo a
     * partir del tamaño real del drawable y nunca pasa de 342 px (16:9); en
     * pantallas más altas la imagen queda centrada y las barras laterales son
     * del sistema, no del juego.
     */
    private void applyEdgeToEdge() {
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            WindowManager.LayoutParams lp = window.getAttributes();
            lp.layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            window.setAttributes(lp);
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Api30.immersive(window);
        } else {
            window.getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    /** API 30+ inmersivo; en una clase aparte para que los equipos viejos no
     *  intenten resolver WindowInsetsController al verificar MainActivity. */
    private static final class Api30 {
        static void immersive(Window window) {
            window.setDecorFitsSystemWindows(false);
            WindowInsetsController controller = window.getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.systemBars());
                controller.setSystemBarsBehavior(
                        WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            applyEdgeToEdge();
        }
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
