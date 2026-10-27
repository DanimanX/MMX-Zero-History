![MMX Zero History](docs/img/banner.png)

# MMX Zero History

Recompilación nativa de **Mega Man X3 (USA)** con identidad, historia, jefes,
cápsulas y banda sonora propias, en **español chileno**, para Linux, Windows,
macOS y Android.

> La historia que Zero nunca alcanzó a contar.

[![Desktop host](https://github.com/DanimanX/MMX-Zero-History/actions/workflows/build.yml/badge.svg)](https://github.com/DanimanX/MMX-Zero-History/actions/workflows/build.yml)

## Qué es esto

Un fork de [MegamanX3SNESRecomp](https://github.com/mstan/MegamanX3SNESRecomp)
que conserva el motor (ejecución LLE del 65816 con cobertura AOT encima, Cx4
emulado por instrucción) y le cambia todo lo que se puede cambiar sin tocar el
cartucho: nombre, identidad visual, línea narrativa, guion, diseño de jefes y
cápsulas, banda sonora original, controles táctiles y CI multiplataforma.

## Qué **no** es esto

**No es un ROM hack.** No trae sprites nuevos de jefes, mapas nuevos, música
insertada en el SPC ni el texto del juego traducido dentro del cartucho. Eso es
un proyecto de meses y está especificado, no implementado.

Lo que hay acá es todo el andamiaje alrededor de eso más el motor real
compilando. La línea exacta entre "funciona" y "está escrito" está en
[`docs/ESTADO.md`](docs/ESTADO.md), sin adornos.

## El ROM

Tenés que poner tu propio dump, legalmente obtenido. Nada derivado del ROM se
versiona en este repositorio.

- **archivo**: `mmx3.sfc` en la raíz del repo
- **tamaño**: 2 MiB, sin cabecera
- **CRC32**: `0xFA0FE671`
- **SHA-256**: `65b03268afac296330e8ff8d60dd0825879e13ed658b37713c034a3bd074f1d7`

Una cabecera de copiador SMC de 512 bytes se descarta automáticamente, tanto
en el recompilador como en el launcher. Verificalo con:

```bash
python3 tools/verify_rom.py mmx3.sfc
```

## La historia

Años después de Doppler, una excavación bajo Atacama abre la **Bóveda Ω**: el
archivo personal del Dr. Wily, todavía en línea. Adentro no hay un robot, hay
un **eco** — la voz y el criterio de Wily, grabados para seguir dando órdenes
después de muerto. Y lo que el eco quiere no es conquistar el mundo: es
terminar un trabajo que quedó a medias y recuperar a Zero.

Para eso reactiva ocho revisiones de la unidad **W-00**, el nombre de fábrica
de Zero. Cada jefe carga un fragmento cifrado de su pasado. X baja a las ocho
zonas y, por cada jefe que cae, una memoria vuelve a su lugar.

La historia no se cuenta en una cinemática: se cuenta en pedazos, y el pedazo
que importa es el último — **Wily construyó a Zero para matar a Mega Man**, y
Zero alcanzó a intentarlo.

![Línea de tiempo](docs/img/linea-tiempo.png)

- Biblia narrativa completa: [`docs/HISTORIA.md`](docs/HISTORIA.md)
- Guion de todas las cinemáticas, en chileno: [`docs/GUION.md`](docs/GUION.md)
- Tres finales según cuántos fragmentos juntaste

## Los ocho mavericks

Ocho revisiones W más el jefe final, con anillo de debilidades cerrado: ningún
orden de etapas deja al jugador sin respuesta.

- **W-01 — Cóndor Cobalto**, Cordillera de los Andes · *Ala Cobalto*
- **W-02 — Salitre Sierpe**, Desierto de Atacama · *Salmuera*
- **W-03 — Glaciar Grifo**, Campo de Hielo Sur · *Aliento Blanco*
- **W-04 — Víbora Caldor**, Volcán Caldor · *Erupción*
- **W-05 — Marea Mantis**, Fiordos de Chiloé · *Ola Cortante*
- **W-06 — Jabalí Alerce**, Selva Valdiviana · *Astilla*
- **W-07 — Búho Reloj**, Puerto del Reloj · *Segundero*
- **W-08 — Puma Chatarra**, Desarmadero Wily · *Imán Puma*
- **Ω — Cero-Ω y el Eco de Wily**, Bóveda Ω

![Mapa de etapas](docs/img/mapa-etapas.png)

Patrones de ataque, fases y drops en [`docs/MAVERICKS.md`](docs/MAVERICKS.md).

## Cápsulas errantes

Ninguna cápsula tiene posición fija. Cada etapa tiene **tres nichos**
autorados, todos alcanzables con el equipo base; cada partida elige uno por
etapa y reparte los ocho contenidos al azar.

![Cápsulas errantes](docs/img/capsulas.png)

El reparto es determinista y verificable — publicado como semilla en el select
de etapas:

```console
$ python3 tools/capsule_shuffle.py --mode speedrun
semilla 00000000
  W-01 condor_cobalto   nicho 3  -> Casco      (rompe bloques)
  W-02 salitre_sierpe   nicho 2  -> Núcleo 01  (fragmento de memoria)
  W-03 glaciar_grifo    nicho 1  -> Núcleo 02  (fragmento de memoria)
  ...

$ python3 tools/capsule_shuffle.py --mode historia --slot 1
semilla CC0D3F32
  ...
```

Modos: **Historia** (semilla por perfil/slot/partida), **Speedrun** (semilla
fija `0`) y **Caos** (semilla nueva cada vez). Contrato completo en
[`docs/CAPSULAS.md`](docs/CAPSULAS.md); pruebas con
`python3 tools/test_capsule_shuffle.py`.

## Música

Doce pistas originales a 32 kHz mono, generadas desde código: el tema de la
Bóveda, el select de etapas, las ocho etapas, la Bóveda Ω y el tema de Zero.
Misma familia de timbres que un juego de SNES (dos pulsos, triángulo, ruido),
melodías y progresiones nuevas.

```console
python3 tools/make_soundtrack.py          # renderiza las doce
python3 tools/make_soundtrack.py --list   # tempo, compás y mood
```

Escuchalas en [`assets/audio/`](assets/audio). Diseño y camino de integración
al motor en [`docs/MUSICA.md`](docs/MUSICA.md).

## Plataformas y controles

- **Linux / Windows / macOS** — host de escritorio SDL2, con soporte real de
  mando por `SDL_GameController` (Xbox, DualShock, 8BitDo) y teclado
  remapeable en `keybinds.ini`.
- **Android** — andamiaje con controles táctiles (D-pad, rombo SNES, hombros,
  start), auto-ocultado al conectar un mando y zona muerta configurable.

![Android](docs/img/android.png)

La **lógica táctil** sí está probada en el escritorio (15 pruebas: dos dedos a
la vez, dos dedos en el mismo botón, latcheo al deslizar, saturación de la
tabla de dedos, espejado exacto):

```console
bash tools/test_touch_controls.sh
```

La **app Android no está verificada**: se escribió sin SDK ni NDK disponible en
la máquina de desarrollo y nunca se ejecutó en un dispositivo. Los pasos que
faltan están enumerados en [`docs/ANDROID.md`](docs/ANDROID.md) y
[`docs/ESTADO.md`](docs/ESTADO.md).

## Build

```bash
git submodule update --init --recursive
cp /ruta/a/tu/dump mmx3.sfc
python3 tools/verify_rom.py mmx3.sfc
bash tools/regen.sh --no-tests          # emite src/gen/*.c + recomp/funcs.h
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_SDL_BACKEND=SDL2
cmake --build build --target MegaManX3SNESRecomp
```

Para depurar con el servidor TCP de 4384 y los anillos de observabilidad,
configurá con `-DSNESRECOMP_ENABLE_TRACE=ON`.

Sin ROM se puede compilar igual el *setup host*, que es lo que corre CI:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_SETUP_HOST=ON
cmake --build build --target MegaManX3SNESRecomp
```

## Integración continua

- **`build.yml`** — pruebas (cápsulas + táctil) y compilación del host de
  escritorio en Linux. Es el gate real.
- **`rom-build.yml`** — **manual**. Compila el binario jugable en Linux,
  Windows y macOS leyendo tu ROM desde el secreto `MMX3_ROM_BASE64`, que nunca
  entra al repositorio. Verifica el SHA-256 antes de aceptar el archivo.
- **`android.yml`** — **manual y experimental**. Marcado con
  `continue-on-error`: puede fallar sin romper nada mientras se itera.
- **`release.yml`** — al empujar una etiqueta `v*`, publica los paquetes de las
  tres plataformas de escritorio con arte, banda sonora y el aviso de ROM.

Estado de cada uno al publicar la 0.0.1:

- **Desktop host (Linux)**: verde — pruebas + compilación, corrida real en CI.
- **Release**: verde en las tres plataformas. La etiqueta `v0.0.1` publicó
  `MMXZeroHistory-linux-x86_64.zip`, `-windows-x86_64.zip` y `-macos-arm64.zip`
  construidos en runners reales.
- **rom-build**: escrito, nunca corrido (necesita el secreto con tu ROM).
- **Android**: escrito, nunca corrido con éxito confirmado.

## Estado

Lo que corre hoy, lo que está escrito y lo que no existe (sprites, mapas,
música insertada, traducción dentro del cartucho) está separado explícitamente
en [`docs/ESTADO.md`](docs/ESTADO.md). Si algo de este README suena a que el
juego nuevo ya está adentro del cartucho, leé ese archivo.

## Créditos y licencia

- Motor: [snesrecomp](https://github.com/RetroPortingToolKit/snesrecomp) y
  [recomp-ui](https://github.com/RetroPortingToolKit/recomp-ui), con el port
  original de [mstan](https://github.com/mstan/MegamanX3SNESRecomp).
- Emulación del Cx4: adaptada de [ares](https://github.com/ares-emulator/ares)
  (ISC), vía snesrecomp.
- Anotaciones de desensamblado: [bogaa/dizProjects](https://github.com/bogaa/dizProjects).
- Todo el contenido nuevo de Zero History —historia, guion, diseño, arte,
  banda sonora y código— es original de este repositorio.
- Licencia del código: **PolyForm Noncommercial 1.0.0** (ver [`LICENSE`](LICENSE)).
  El ROM de Mega Man X3 y cualquier dato extraído de él **no** se distribuyen
  acá y no están licenciados para redistribución.

Documentación técnica heredada del port original: [`docs/WIDESCREEN.md`](docs/WIDESCREEN.md),
[`docs/SAVE_STATES.md`](docs/SAVE_STATES.md), [`docs/CX4.md`](docs/CX4.md),
[`docs/COVERAGE_2026-10-18.md`](docs/COVERAGE_2026-10-18.md).
