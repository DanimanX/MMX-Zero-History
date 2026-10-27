// Copia el catálogo de mods empaquetado en assets/ al almacenamiento de la
// app, que es el directorio de trabajo del host nativo.
//
// El runtime de mods lee `mods/preloaded/packages` del sistema de archivos, no
// del APK. En escritorio ese árbol viaja en el zip al lado del ejecutable; acá
// hay que sacarlo de assets una vez por arranque (son unos pocos KiB) para que
// el paquete Widescreen exista cuando el motor resuelve la selección por
// defecto. Sin esto, el APK arrancaría en 4:3 aunque el manifest declare
// default_enabled = true.

package cl.zerohistory.mmx;

import android.content.Context;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

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
        try {
            copyTree(context, "mods", new File(root, "mods"));
        } catch (IOException ignored) {
            // The game still boots without mods; it just keeps the 4:3
            // default. A missing catalog is not a reason to crash the app.
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
