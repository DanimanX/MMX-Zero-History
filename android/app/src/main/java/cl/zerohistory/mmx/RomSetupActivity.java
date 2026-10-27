// Pantalla de entrada de la app: consigue el ROM y arranca el juego.
//
// Antes de la 0.0.3 la actividad principal era la del motor, así que abrir la
// app sin un `mmx3.sfc` en el almacenamiento de la app hacía que `main`
// devolviera 1 y todo se cerrara sin decir nada. Ahora la app abre acá:
//
//   - si el ROM está y el SHA-256 coincide, arranca el juego;
//   - si falta, explica qué archivo hace falta, lo importa con el selector del
//     sistema y lo verifica antes de escribirlo en su lugar definitivo;
//   - si el motor se cierra después de arrancar, muestra las últimas líneas
//     de `native.log` en vez de desaparecer.

package cl.zerohistory.mmx;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.method.ScrollingMovementMethod;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;

public class RomSetupActivity extends Activity {
    private static final int REQUEST_PICK_ROM = 1001;
    private static final String STATE_LAUNCHED = "launched";

    private TextView status;
    private TextView logTitle;
    private TextView buildView;
    private TextView logView;
    private Button pickButton;
    private Button playButton;
    private boolean launchedGame;
    private boolean startedOnce;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState != null) {
            launchedGame = savedInstanceState.getBoolean(STATE_LAUNCHED, false);
            startedOnce = launchedGame;
        }
        AssetInstaller.install(this);
        setContentView(buildUi());
        refresh();
        // No se arranca el motor solo. Esta pantalla es la casa de la app: es
        // donde se ve qué build corre, qué campo eligió el motor y qué cambia
        // esta versión. Arrancar de automático la escondía para siempre y, si
        // el motor moría, el jugador volvía a caer en un arranque sin
        // explicación. Un toque en JUGAR es una decisión, no una sorpresa.
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putBoolean(STATE_LAUNCHED, launchedGame);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (launchedGame) {
            launchedGame = false;
            refresh();
            showLastRun();
        }
    }

    private View buildUi() {
        int pad = (int) (24 * getResources().getDisplayMetrics().density);

        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(pad, pad, pad, pad);
        column.setBackgroundColor(Color.rgb(8, 12, 24));

        TextView title = new TextView(this);
        title.setText("MMX ZERO HISTORY");
        title.setTextColor(Color.rgb(238, 244, 255));
        title.setTextSize(30);
        column.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("La historia que Zero nunca alcanzó a contar");
        subtitle.setTextColor(Color.rgb(255, 176, 64));
        subtitle.setTextSize(15);
        subtitle.setPadding(0, pad / 6, 0, pad);
        column.addView(subtitle);

        status = new TextView(this);
        status.setTextColor(Color.rgb(150, 162, 180));
        status.setTextSize(15);
        status.setPadding(0, 0, 0, pad);
        column.addView(status);

        pickButton = new Button(this);
        pickButton.setText("Elegir mi mmx3.sfc");
        pickButton.setOnClickListener(v -> pickRom());
        column.addView(pickButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        playButton = new Button(this);
        playButton.setText("Jugar");
        playButton.setOnClickListener(v -> startGame());
        LinearLayout.LayoutParams playParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        playParams.topMargin = pad / 2;
        column.addView(playButton, playParams);

        Button loreButton = new Button(this);
        loreButton.setText("Historia y jefes");
        loreButton.setOnClickListener(v ->
                startActivity(new Intent(this, LoreActivity.class)));
        LinearLayout.LayoutParams loreParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        loreParams.topMargin = pad / 4;
        column.addView(loreButton, loreParams);

        TextView help = new TextView(this);
        help.setText(
                "El juego no incluye el cartucho.\n\n"
                        + "1. Usá tu propio dump de Mega Man X3 (USA), obtenido legalmente.\n"
                        + "2. Tiene que ser el dump sin cabecera: 2 MiB, CRC32 "
                        + RomStore.EXPECTED_CRC32 + ".\n"
                        + "3. Tocá «Elegir mi mmx3.sfc». Se copia a la carpeta privada de la app, "
                        + "se verifica el SHA-256 y se borra cualquier cabecera de copiador.\n\n"
                        + "Carpeta: " + RomStore.dir(this).getAbsolutePath());
        help.setTextColor(Color.rgb(150, 162, 180));
        help.setTextSize(13);
        help.setPadding(0, pad, 0, pad / 2);
        column.addView(help);

        logTitle = new TextView(this);
        logTitle.setText("Última salida del motor");
        logTitle.setTextColor(Color.rgb(86, 232, 255));
        logTitle.setTextSize(13);
        logTitle.setVisibility(View.GONE);
        column.addView(logTitle);

        buildView = new TextView(this);
        buildView.setTextColor(Color.rgb(110, 255, 210));
        buildView.setTextSize(12);
        buildView.setTypeface(android.graphics.Typeface.MONOSPACE);
        buildView.setVisibility(View.GONE);
        column.addView(buildView);

        TextView scope = new TextView(this);
        scope.setText(
                "Qué cambia esta build y qué no\n\n"
                        + "Esta app es una recompilación del cartucho: ejecuta los mismos "
                        + "bytes de tu dump. Lo que agrega el proyecto, y se puede ver:"
                        + "\n· nombre «MMX Zero History» y arte de arranque;"
                        + "\n· campo 16:9 (342×224) con HUD y enemigos ajustados;"
                        + "\n· importación verificada del ROM y diagnóstico."
                        + "\n\nLo que NO trae, porque está diseñado y no insertado en el "
                        + "cartucho: historia nueva, jefes nuevos, cápsulas, texto en "
                        + "español y banda sonora dentro del juego. El cartucho se juega "
                        + "igual que el original; ver docs/ESTADO.md.");
        scope.setTextColor(Color.rgb(150, 162, 180));
        scope.setTextSize(12);
        scope.setPadding(0, pad, 0, pad / 2);
        column.addView(scope);

        logView = new TextView(this);
        logView.setTextColor(Color.rgb(200, 210, 225));
        logView.setTextSize(11);
        logView.setTypeface(android.graphics.Typeface.MONOSPACE);
        logView.setVisibility(View.GONE);
        logView.setMovementMethod(new ScrollingMovementMethod());
        column.addView(logView);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(column);
        return scroll;
    }

    private void refresh() {
        boolean ready = RomStore.isReady(this);
        if (ready) {
            status.setText("ROM listo. SHA-256 verificado.");
            status.setTextColor(Color.rgb(110, 255, 210));
        } else if (RomStore.rom(this).isFile()) {
            // El archivo está pero no es el cartucho correcto: decirlo, en vez
            // de fingir que falta (el motor lo cargaría igual y correría basura).
            status.setText("Hay un archivo en la carpeta de la app, pero su SHA-256 "
                    + "no coincide con Mega Man X3 (USA). Elejí tu dump otra vez.");
            status.setTextColor(Color.rgb(255, 92, 92));
        } else {
            status.setText("Falta el ROM del juego en esta app.");
            status.setTextColor(Color.rgb(255, 92, 92));
        }
        playButton.setEnabled(ready);
        playButton.setAlpha(ready ? 1f : 0.4f);
        pickButton.setText(ready ? "Cambiar ROM" : "Elegir mi mmx3.sfc");
        showBuildInfo();
    }

    private void pickRom() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        try {
            startActivityForResult(intent, REQUEST_PICK_ROM);
        } catch (android.content.ActivityNotFoundException e) {
            showMessage("Este Android no tiene un selector de archivos.");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_PICK_ROM || resultCode != RESULT_OK
                || data == null || data.getData() == null) {
            return;
        }
        Uri uri = data.getData();
        showMessage("Verificando el archivo…");
        RomStore.Result result = RomStore.importFrom(this, uri);
        refresh();
        if (result.ok) {
            status.setText(result.message);
            status.setTextColor(Color.rgb(110, 255, 210));
            // Importar es una acción explícita: si salió bien, jugar.
            startGame();
        } else {
            showMessage(result.message);
            status.setTextColor(Color.rgb(255, 92, 92));
        }
    }

    private void showMessage(String message) {
        status.setText(message);
        status.setTextColor(Color.rgb(255, 176, 64));
    }

    private void startGame() {
        if (!RomStore.isReady(this)) {
            showMessage("Primero elegí tu mmx3.sfc.");
            return;
        }
        launchedGame = true;
        startedOnce = true;
        startActivity(new Intent(this, MainActivity.class));
    }

    /**
     * El motor deja dos líneas al arrancar: `[mmx] build=<versión>` y
     * `[mmx] video: 342x224 (widescreen=1, ...)`. Son la prueba de que esta
     * corrida es la build del proyecto y de que el campo ancho se aplicó:
     * sin ellas, «se ve como el original» no se puede ni confirmar ni negar.
     */
    private void showBuildInfo() {
        String log = tail(new File(RomStore.dir(this), "native.prev.log"), 4096);
        if (log == null) log = tail(new File(RomStore.dir(this), "native.log"), 4096);
        String build = firstLineStartingWith(log, "[mmx] build=");
        String video = firstLineStartingWith(log, "[mmx] video:");
        if (build == null && video == null) {
            buildView.setVisibility(View.GONE);
            return;
        }
        StringBuilder sb = new StringBuilder();
        if (build != null) sb.append(build.replace("[mmx] ", ""));
        if (video != null) {
            if (sb.length() > 0) sb.append('\n');
            sb.append(video.replace("[mmx] ", ""));
        }
        buildView.setText(sb.toString());
        buildView.setVisibility(View.VISIBLE);
    }

    private static String firstLineStartingWith(String text, String prefix) {
        if (text == null) return null;
        for (String line : text.split("\n")) {
            if (line.startsWith(prefix)) return line.trim();
        }
        return null;
    }

    /**
     * El motor escribe su stderr en `native.log`, no en logcat. Si la corrida
     * se corta, esas líneas son la única explicación disponible.
     */
    private void showLastRun() {
        File log = new File(RomStore.dir(this), "native.log");
        String tail = tail(log, 1600);
        if (tail == null || tail.isEmpty()) {
            logTitle.setVisibility(View.GONE);
            logView.setVisibility(View.GONE);
            return;
        }
        int exit = tail.lastIndexOf("[mmx] main exit");
        if (tail.contains("[mmx] main entry") && exit < 0) {
            // Sin línea de salida: el proceso murió (crash) o Android lo mató.
            status.setText("El motor se cerró de forma anormal. Abajo está el final del registro.");
            status.setTextColor(Color.rgb(255, 92, 92));
        }
        logView.setText(tail);
        logTitle.setVisibility(View.VISIBLE);
        logView.setVisibility(View.VISIBLE);
        logView.setGravity(Gravity.START);
    }

    private static String tail(File file, int bytes) {
        if (file == null || !file.isFile()) return null;
        try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {
            long length = raf.length();
            long from = Math.max(0, length - bytes);
            byte[] buffer = new byte[(int) (length - from)];
            raf.seek(from);
            raf.readFully(buffer);
            return new String(buffer, "UTF-8").trim();
        } catch (IOException e) {
            return null;
        }
    }
}
