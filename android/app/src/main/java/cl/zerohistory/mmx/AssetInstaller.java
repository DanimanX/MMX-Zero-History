// Prepara el directorio de trabajo del host nativo antes de que arranque.
//
// Dos cosas, en este orden:
//
//   1. `cwd.txt`: el proceso nativo arranca en `/` y el host resuelve
//      `mods/preloaded`, `keybinds.ini`, `config.ini` y el ROM de forma
//      relativa. Java no puede hacer chdir, así que le deja la ruta escrita y
//      `main()` la lee antes de llamar al motor. Sin esto el runtime de mods
//      intentaba crear `/system/bin/mods` (read-only) y el paquete 16:9 quedaba
//      deshabilitado en silencio.
//   2. El catálogo de mods del APK, copiado desde assets.
package cl.zerohistory.mmx;

import android.content.Context;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

final class AssetInstaller {
    private AssetInstaller() {}

    static void install(Context context) {
        File root = context.getExternalFilesDir(null);
        if (root == null) {
            root = context.getFilesDir();
        }
        if (root == null) {
            return;
        }
        writeWorkdir(context, root);
        installDefaultConfig(context, root);
        try {
            copyTree(context, "mods", new File(root, "mods"));
        } catch (IOException ignored) {
            // The game still boots without mods; it just keeps the 4:3
            // default. A missing catalog is not a reason to crash the app.
        }
    }

    /**
     * config.ini por defecto con `Widescreen = 1`.
     *
     * En Android no hay launcher de escritorio donde activar el 16:9, y el
     * paquete de mods no puede cargarse porque el runtime lo busca relativo al
     * ejecutable (`/system/bin`, de solo lectura). El host sí lee
     * `[Graphics] Widescreen` del config.ini, así que la app parte de un
     * archivo completo —el mismo conjunto de claves que escribe el motor— con
     * el campo ancho ya encendido.
     *
     * Solo se copia si no existe: lo que el jugador cambie después manda.
     */
    private static void installDefaultConfig(Context context, File workdir) {
        File config = new File(workdir, "config.ini");
        if (config.exists()) return;
        try (InputStream in = context.getAssets().open("config.default.ini");
             OutputStream out = new FileOutputStream(config)) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = in.read(buffer)) > 0) {
                out.write(buffer, 0, n);
            }
        } catch (IOException ignored) {
            // Sin este archivo el host crea el suyo (4:3). No es fatal.
        }
    }

    /**
     * Ruta que `main()` convierte en su directorio de trabajo. Se escribe en el
     * almacenamiento privado porque su ubicación también es fija (no depende
     * de que el almacenamiento externo esté montado).
     */
    private static void writeWorkdir(Context context, File workdir) {
        File marker = new File(context.getFilesDir(), "cwd.txt");
        try (FileOutputStream out = new FileOutputStream(marker)) {
            out.write(workdir.getAbsolutePath().getBytes(StandardCharsets.UTF_8));
            out.write('\n');
        } catch (IOException ignored) {
            // Sin marcador el host usa el cwd heredado; el juego arranca
            // igual, solo que sin catálogo de mods.
        }
    }

    private static void copyTree(Context context, String assetPath, File dest)
            throws IOException {
        String[] children = context.getAssets().list(assetPath);
        if (children != null && children.length > 0) {
            if (!dest.exists() && !dest.mkdirs()) {
                throw new IOException("cannot create " + dest);
            }
            for (String child : children) {
                copyTree(context, assetPath + "/" + child, new File(dest, child));
            }
            return;
        }
        if (!dest.getParentFile().exists() && !dest.getParentFile().mkdirs()) {
            throw new IOException("cannot create " + dest.getParentFile());
        }
        try (InputStream in = context.getAssets().open(assetPath);
             OutputStream out = new FileOutputStream(dest)) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = in.read(buffer)) > 0) {
                out.write(buffer, 0, n);
            }
        }
    }
}
