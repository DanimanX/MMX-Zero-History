// Localiza, verifica e importa el ROM del jugador.
//
// El host nativo no trae el cartucho: arranca, hace chdir al almacenamiento
// externo de la app y busca `mmx3.sfc` ahí. Si no lo encuentra, `main` devuelve
// 1 y la actividad se cierra -- que es exactamente el "se abre y se cierra"
// que reportó el primer usuario de la 0.0.2.
//
// Por eso la app comprueba y, si hace falta, importa el ROM antes de arrancar
// el motor. La verificación es la misma identidad que usa el host: SHA-256 del
// dump sin cabecera de copiador.

package cl.zerohistory.mmx;

import android.content.Context;
import android.net.Uri;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

final class RomStore {
    static final String ROM_NAME = "mmx3.sfc";
    static final String EXPECTED_SHA256 =
            "65b03268afac296330e8ff8d60dd0825879e13ed658b37713c034a3bd074f1d7";
    static final String EXPECTED_CRC32 = "FA0FE671";

    /** Dump sin cabecera. Una cabecera de copiador SMC son 512 bytes. */
    static final int ROM_BYTES = 2 * 1024 * 1024;
    static final int COPIER_HEADER_BYTES = 512;

    private RomStore() {}

    /** Directorio de trabajo del host nativo. */
    static File dir(Context context) {
        File external = context.getExternalFilesDir(null);
        return external != null ? external : context.getFilesDir();
    }

    static File rom(Context context) {
        return new File(dir(context), ROM_NAME);
    }

    static final class Result {
        final boolean ok;
        final String message;

        Result(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }

        static Result ok(String message) {
            return new Result(true, message);
        }

        static Result fail(String message) {
            return new Result(false, message);
        }
    }

    /** True si el ROM ya está en su sitio y coincide con la identidad. */
    static boolean isReady(Context context) {
        return verify(rom(context));
    }

    static boolean verify(File file) {
        if (file == null || !file.isFile()) return false;
        long length = file.length();
        if (length != ROM_BYTES && length != ROM_BYTES + COPIER_HEADER_BYTES) {
            return false;
        }
        try (InputStream in = new java.io.FileInputStream(file)) {
            return EXPECTED_SHA256.equalsIgnoreCase(digest(in, length));
        } catch (IOException e) {
            return false;
        }
    }

    /**
     * Copia el documento elegido a `mmx3.sfc`, quitando la cabecera de
     * copiador si la trae. Nada se escribe en su lugar definitivo hasta que
     * el digest coincide, así que un archivo equivocado no deja el juego en
     * un estado a medias.
     */
    static Result importFrom(Context context, Uri uri) {
        File destination = rom(context);
        File staging = new File(dir(context), ROM_NAME + ".incoming");
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            return Result.fail("Este Android no tiene SHA-256; no se puede verificar el ROM.");
        }

        long written = 0;
        try (InputStream in = context.getContentResolver().openInputStream(uri)) {
            if (in == null) return Result.fail("No se pudo abrir el archivo elegido.");
            byte[] buffer = new byte[64 * 1024];
            int read;
            long offset = 0;
            // Se necesita el tamaño total para saber si la cabecera SMC está
            // ahí, así que se escribe entero y se decide después.
            try (FileOutputStream out = new FileOutputStream(staging)) {
                while ((read = in.read(buffer)) > 0) {
                    out.write(buffer, 0, read);
                    offset += read;
                }
                written = offset;
            }
        } catch (IOException | SecurityException e) {
            staging.delete();
            return Result.fail("No se pudo leer el archivo: " + e.getMessage());
        }

        long payload = written;
        boolean hasHeader =
                written == ROM_BYTES + COPIER_HEADER_BYTES;
        if (written != ROM_BYTES && !hasHeader) {
            staging.delete();
            return Result.fail(String.format(Locale.US,
                    "El archivo tiene %d bytes; se esperan %d (dump sin cabecera) "
                            + "o %d (con cabecera de copiador).",
                    written, ROM_BYTES, ROM_BYTES + COPIER_HEADER_BYTES));
        }

        String actual;
        try (InputStream in = new java.io.FileInputStream(staging)) {
            actual = digest(in, payload);
        } catch (IOException e) {
            staging.delete();
            return Result.fail("No se pudo verificar el archivo copiado.");
        }
        if (!EXPECTED_SHA256.equalsIgnoreCase(actual)) {
            staging.delete();
            return Result.fail("El SHA-256 no coincide: no es un dump de Mega Man X3 (USA).\n"
                    + "obtenido  " + actual);
        }

        // Todo verificado: mover a su lugar, recortando la cabecera si sobra.
        try {
            if (hasHeader) {
                File trimmed = new File(dir(context), ROM_NAME + ".trimmed");
                try (InputStream in = new java.io.FileInputStream(staging);
                     FileOutputStream out = new FileOutputStream(trimmed)) {
                    in.skip(COPIER_HEADER_BYTES);
                    byte[] buffer = new byte[64 * 1024];
                    int read;
                    while ((read = in.read(buffer)) > 0) {
                        out.write(buffer, 0, read);
                    }
                }
                if (!staging.delete() || !trimmed.renameTo(staging)) {
                    trimmed.delete();
                    return Result.fail("No se pudo preparar el archivo en su lugar definitivo.");
                }
            }
            if (destination.exists() && !destination.delete()) {
                return Result.fail("No se pudo reemplazar el ROM anterior.");
            }
            if (!staging.renameTo(destination)) {
                return Result.fail("No se pudo guardar el ROM en " + destination);
            }
        } catch (IOException e) {
            staging.delete();
            return Result.fail("No se pudo guardar el ROM: " + e.getMessage());
        }
        return Result.ok("ROM verificado (SHA-256 correcto).");
    }

    private static String digest(InputStream in, long length) throws IOException {
        MessageDigest md;
        try {
            md = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IOException("no SHA-256", e);
        }
        if (length == ROM_BYTES + COPIER_HEADER_BYTES) {
            long skipped = in.skip(COPIER_HEADER_BYTES);
            if (skipped != COPIER_HEADER_BYTES) {
                throw new IOException("no se pudo saltar la cabecera SMC");
            }
        }
        byte[] buffer = new byte[64 * 1024];
        int read;
        while ((read = in.read(buffer)) > 0) {
            md.update(buffer, 0, read);
        }
        StringBuilder hex = new StringBuilder(64);
        for (byte b : md.digest()) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }
}
