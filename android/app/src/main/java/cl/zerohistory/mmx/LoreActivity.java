// La historia y los jefes del proyecto, legibles dentro de la app.
//
// El cartucho no cambia: esta pantalla es donde el contenido narrativo existe
// hoy. Está separada de la de entrada a propósito (ver docs/CONTENIDO.md):
// nadie debe confundir "está escrito en la app" con "está insertado en el
// juego".

package cl.zerohistory.mmx;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class LoreActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTheme(android.R.style.Theme_Material_NoActionBar);
        setContentView(buildUi());
    }

    private ScrollView buildUi() {
        int pad = (int) (24 * getResources().getDisplayMetrics().density);
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(pad, pad, pad, pad);
        column.setBackgroundColor(Color.rgb(8, 12, 24));

        column.addView(heading("MMX ZERO HISTORY", 28, Color.rgb(238, 244, 255)));
        column.addView(paragraph("La historia que Zero nunca alcanzó a contar",
                15, Color.rgb(255, 176, 64)));

        column.addView(heading("La Bóveda Ω", 20, Color.rgb(86, 232, 255)));
        column.addView(paragraph(
                "Años después de Doppler, una excavación bajo Atacama abre la Bóveda Ω: "
                        + "el archivo personal del Dr. Wily, todavía en línea. Adentro no hay un "
                        + "robot, hay un eco: la voz y el criterio de Wily, grabados para seguir "
                        + "dando órdenes después de muerto.\n\n"
                        + "Lo que el eco quiere no es conquistar el mundo. Es terminar un trabajo "
                        + "que quedó a medias y recuperar a Zero. Para eso reactiva ocho revisiones "
                        + "de la unidad W-00, el nombre de fábrica de Zero. Cada jefe carga un "
                        + "fragmento cifrado de su pasado: X baja a las ocho zonas y, por cada jefe "
                        + "que cae, una memoria vuelve a su lugar.\n\n"
                        + "La historia no se cuenta en una cinemática: se cuenta en pedazos, y el "
                        + "pedazo que importa es el último. Wily construyó a Zero para matar a "
                        + "Mega Man, y Zero alcanzó a intentarlo.",
                13, Color.rgb(200, 210, 225)));

        column.addView(heading("Las ocho revisiones W", 20, Color.rgb(86, 232, 255)));
        String[][] bosses = {
                {"W-01 · Cóndor Cobalto", "Cordillera de los Andes", "Ala Cobalto"},
                {"W-02 · Salitre Sierpe", "Desierto de Atacama", "Salmuera"},
                {"W-03 · Glaciar Grifo", "Campo de Hielo Sur", "Aliento Blanco"},
                {"W-04 · Víbora Caldor", "Volcán Caldor", "Erupción"},
                {"W-05 · Marea Mantis", "Fiordos de Chiloé", "Ola Cortante"},
                {"W-06 · Jabalí Alerce", "Selva Valdiviana", "Astilla"},
                {"W-07 · Búho Reloj", "Puerto del Reloj", "Segundero"},
                {"W-08 · Puma Chatarra", "Desarmadero Wily", "Imán Puma"},
                {"Ω · Bóveda Ω", "Cero-Ω y el Eco de Wily", "—"},
        };
        for (String[] boss : bosses) {
            column.addView(paragraph(boss[0] + "\n" + boss[1] + " · arma: " + boss[2],
                    13, Color.rgb(200, 210, 225)));
        }
        column.addView(paragraph(
                "Anillo de debilidades: Puma → Cobalto → Alerce → Mantis → Caldor → Grifo → "
                        + "Sierpe → Reloj → Puma. Ningún orden de etapas deja al jugador sin arma "
                        + "para el siguiente jefe.",
                12, Color.rgb(255, 176, 64)));

        column.addView(heading("Cápsulas errantes", 20, Color.rgb(86, 232, 255)));
        column.addView(paragraph(
                "Ninguna cápsula tiene posición fija. Cada etapa tiene tres nichos autorados, "
                        + "todos alcanzables con el equipo base; cada partida elige uno por etapa y "
                        + "reparte los ocho contenidos al azar con una semilla publicada en el "
                        + "select de etapas.\n\n"
                        + "Contenidos: Botas, Armadura, Casco, Buster, Sable Zero y tres Núcleos "
                        + "de memoria. Modos: Historia (semilla por perfil/slot), Speedrun (fija) "
                        + "y Caos (nueva cada vez).",
                13, Color.rgb(200, 210, 225)));

        column.addView(heading("Dónde vive esto", 20, Color.rgb(255, 92, 92)));
        column.addView(paragraph(
                "Este texto está en la app, no en el cartucho. El juego ejecuta tu dump de "
                        + "Mega Man X3 sin modificarlo, y lo único que el proyecto cambia en "
                        + "pantalla es el nombre, el arte de arranque y el campo 16:9.\n\n"
                        + "El motor trae el mecanismo para insertar contenido sin tocar el "
                        + "cartucho (parches de ROM, RAM y VRAM en memoria del invitado), y esta "
                        + "build aplica los que están verificados. Insertar jefes, mapas o el "
                        + "guion requiere derivar del ROM las direcciones y los glifos reales: "
                        + "eso es trabajo pendiente, documentado en docs/CONTENIDO.md.",
                12, Color.rgb(150, 162, 180)));

        ScrollView scroll = new ScrollView(this);
        scroll.addView(column);
        return scroll;
    }

    private TextView heading(String text, int size, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setPadding(0, (int) (12 * getResources().getDisplayMetrics().density), 0,
                (int) (6 * getResources().getDisplayMetrics().density));
        return view;
    }

    private TextView paragraph(String text, int size, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setLineSpacing(0f, 1.15f);
        return view;
    }
}
