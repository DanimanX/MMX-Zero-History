> **La numeración parte de cero en este repositorio.** El port original de
> `mstan` llegó a la 0.0.6; MMX Zero History es una línea nueva y arranca en
> 0.0.1. Las notas de las versiones anteriores viven en
> [el repositorio original](https://github.com/mstan/MegamanX3SNESRecomp).

# MMX Zero History v0.0.1 — *Bóveda Ω*

Primera etiqueta de la línea Zero History. Esta versión establece la identidad
del proyecto, la historia, el diseño de jefes y cápsulas, la banda sonora y el
andamiaje multiplataforma. **No** inserta contenido nuevo dentro del cartucho;
la frontera exacta está en [`docs/ESTADO.md`](docs/ESTADO.md).

## Incluido

- **Identidad propia.** El host se presenta como *MMX Zero History*. La
  identidad del ROM no cambió (SHA-256 `65b03268…f1d7`), así que cada jugador
  sigue usando su propio dump de Mega Man X3 (USA).
- **Historia nueva, en español chileno.** Bóveda Ω, el Eco de Wily, las ocho
  revisiones W de la unidad W-00 y el hilo de qué pasó con Zero: Wily lo creó
  para matar a Mega Man y Zero alcanzó a intentarlo. Tres finales según los
  fragmentos recuperados.
  → [`docs/HISTORIA.md`](docs/HISTORIA.md), [`docs/GUION.md`](docs/GUION.md)
- **Ocho mavericks nuevos** con etapas del norte y sur de Chile y un anillo de
  debilidades cerrado. → [`docs/MAVERICKS.md`](docs/MAVERICKS.md)
- **Cápsulas errantes.** Reparto determinista por semilla, con garantías de
  biyección, alcanzabilidad y ausencia de callejones sin salida, implementadas
  y probadas (`tools/capsule_shuffle.py`, 7 pruebas).
  → [`docs/CAPSULAS.md`](docs/CAPSULAS.md)
- **Banda sonora original**, doce pistas a 32 kHz generadas desde código, en
  `assets/audio/`. → [`docs/MUSICA.md`](docs/MUSICA.md)
- **Controles táctiles probados** en su lógica: geometría del pad, multi-touch,
  latcheo al deslizar y espejado (`tools/test_touch_controls.sh`, 15 pruebas).
- **Andamiaje Android** con actividad SDL, capa táctil y puente JNI.
  → [`android/`](android/), [`docs/ANDROID.md`](docs/ANDROID.md)
- **CI**: gate de escritorio en Linux, build jugable manual con ROM desde
  secreto, Android experimental y release por etiqueta.

## Qué no está verificado

- La app Android **nunca se ejecutó en un dispositivo** (no había SDK/NDK en la
  máquina de desarrollo). El job de CI es manual y experimental.
- Los jobs de Windows y macOS están escritos pero no se corrieron.
- Las cápsulas y la música están **especificadas y renderizadas**, no
  conectadas al binario.

## Requisitos

Mega Man X3 (USA), CRC32 `0xFA0FE671`. Sin el ROM el proyecto compila como
setup host, pero no arranca el juego.

## Verificación de esta etiqueta

```console
$ python3 tools/verify_rom.py mmx3.sfc
OK: es el ROM esperado

$ python3 tools/test_capsule_shuffle.py
Ran 7 tests ... OK

$ bash tools/test_touch_controls.sh
touch controls: all checks passed

$ cmake --build build --target MegaManX3SNESRecomp
[2/3] Linking CXX executable MegaManX3SNESRecomp
```
