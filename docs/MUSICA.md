# Música — *MMX Zero History*

Doce pistas originales, renderizadas desde código, en
[`assets/audio/`](../assets/audio). La idea del brief era *"distinta a la
original pero parecida"*: misma familia de timbres (dos canales de pulso, bajo
de triángulo, ruido para percusión, melodías heroicas en menor), pero cada
melodía, progresión y tempo es nuevo. Nada está transcrito del soundtrack de
Mega Man X3.

El generador es [`tools/make_soundtrack.py`](../tools/make_soundtrack.py) y es
determinista: correrlo de nuevo produce los mismos bytes.

```console
python3 tools/make_soundtrack.py --list
python3 tools/make_soundtrack.py                 # las doce
python3 tools/make_soundtrack.py --track omega   # una
```

## Las pistas

- **`title_boveda`** — 76 bpm, La menor. El archivo abriéndose. Lento, grave,
  eco largo. Es el tema que da nombre al juego.
- **`stage_select`** — 132 bpm, Mi menor. Decisión. Pulso firme y arpegio
  constante; el jugador va a escuchar esto cientos de veces, así que no tiene
  gancho cansador.
- **`w01_condor_cobalto`** — 150 bpm, Re menor. Viento de altura; arpegios
  rápidos, batería a cuatro.
- **`w02_salitre_sierpe`** — 124 bpm, Do frigio. Desierto. El modo frigio no
  resuelve cómodo: es exactamente la sensación que se busca.
- **`w03_glaciar_grifo`** — 118 bpm, Fa♯ menor. Hielo. Timbre delgado,
  silencios largos, eco corto.
- **`w04_vibora_caldor`** — 168 bpm, Sol menor. Lava. Siera, batería a toda,
  el tema más rápido del juego.
- **`w05_marea_mantis`** — 108 bpm, La dórico **en 3/4**. La única etapa en
  compás de tres; el vaivén de la marea es el compás.
- **`w06_jabali_alerce`** — 142 bpm, Si menor. Selva. Síncopa y peso en el
  contratiempo.
- **`w07_buho_reloj`** — 126 bpm, Re menor. Relojería: el arpegio hace de
  tictac y todo está cuadrado a propósito.
- **`w08_puma_chatarra`** — 156 bpm, Mi frigio. Chatarra. Industrial, con el
  timbre sucio a propósito.
- **`omega`** — 96 bpm, Do menor. Bóveda Ω. Marcial, lento, inevitable.
- **`zero_history`** — 88 bpm, La menor. Créditos. Es el motivo del tema de
  título, pero resuelto: la misma melodía que abría el juego, ahora cerrando.

## Cómo está construido el generador

- **Síntesis**: pulso con duty ajustable (12.5 %, 25 %, 50 %), triángulo y
  sierra; ruido filtrado para percusión con caída exponencial. Nada de samples.
- **Envolventes**: ADSR por canal. El ataque corto es lo que hace que suene a
  chip y no a órgano.
- **Composición**: cada pista tiene un motivo escrito a mano (un compás de
  corcheas) y una progresión de grados. El secuenciador transporta el motivo
  sobre la progresión, agrega el bajo en las raíces y un arpegio de tríada.
  Cada tercera pasada por la progresión aplica una variación rítmica o
  melódica, así el loop no se siente idéntico.
- **Mezcla**: saturación suave (`tanh`), normalización a −1 dBFS y fundido de
  8 ms en los extremos para que el punto de loop no haga clic.
- **Formato**: 32 kHz mono s16 PCM, la frecuencia nativa del DSP del SNES. Se
  guarda como Ogg Vorbis para el repositorio; el WAV queda en un directorio
  temporal.

## Estado de integración

Las pistas existen y se pueden escuchar y usar hoy como banda sonora del
proyecto (tráiler, videos, menú del launcher en una etapa futura), pero **no
están insertadas en el motor de audio del juego**.

Insertarlas de verdad significa elegir entre dos caminos, y ninguno es un
cambio de una tarde:

1. **Reemplazo real del SPC** — volver a componer cada tema como secuencia de
   comandos del driver de sonido de X3 y parchear los bloques de música en el
   ROM. Es el camino fiel, y requiere ingeniería inversa del formato del driver.
2. **Mezcla PCM sobre el motor** — el motor ya expone
   `snes_mod_audio_*` (`snesrecomp/runner/src/mod_audio.h`) para que un mod
   mezcle PCM propio. Permitiría reproducir estas pistas tal cual, pero
   apagar el APU para que no se superpongan también apaga los efectos de
   sonido, así que hay que resolver primero la separación música/SFX.

La versión 0.0.1 no elige por ti: deja el audio listo y el camino documentado.
Ver [`ESTADO.md`](ESTADO.md).

## Licencia del audio

Las doce pistas son originales, generadas por código de este repositorio, y
quedan bajo la misma licencia que el resto del código (PolyForm Noncommercial
1.0.0). No contienen material del soundtrack de Capcom.
