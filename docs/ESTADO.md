# Estado real de la versión 0.0.1

Este documento existe porque es fácil confundir "está documentado" con "está
implementado". Acá está la línea entre las dos cosas, sin adornos.

## Lo que funciona hoy, verificado

- **El ejecutable de escritorio compila y enlaza.** Se regeneró el código AOT
  (`tools/regen.sh --no-tests`: 6.006 variantes exactas, 15 bancos) y se
  compiló con CMake + Ninja + SDL2 en Linux. Artefacto:
  `build/MegaManX3SNESRecomp` (26 MB), enlazado contra `libSDL2-2.0.so.0`.
- **El juego carga el ROM del usuario.** La identidad del ROM
  (SHA-256 `65b03268…f1d7`, CRC32 `FA0FE671`) **no cambió**. Zero History es
  una recompilación de ese cartucho; si el digest cambiara, el launcher
  rechazaría el dump de todo el mundo.
- **Soporte de mando en escritorio.** Viene del host de `snesrecomp` por
  `SDL_GameController` (Xbox, DualShock, 8BitDo), con gestos de rewind y
  launcher configurables. No lo escribimos nosotros y no lo tocamos.
- **Cápsulas errantes — especificación ejecutable.** `tools/capsule_shuffle.py`
  pasa sus 7 pruebas: biyección, determinismo, semilla fija de speedrun,
  derivación por slot y rechazo de modos desconocidos.
- **Controles táctiles — lógica.** `src/platform/android/x3_touch_controls.c`
  pasa sus 15 pruebas en el host
  (`bash tools/test_touch_controls.sh`), compilado con `-Wall -Wextra -Werror
  -pedantic`. Eso incluye dos dedos a la vez, dos dedos en el mismo botón,
  latcheo al deslizar, saturación de la tabla de dedos y espejado exacto.
- **Banda sonora original.** Doce pistas renderizadas a 32 kHz mono,
  verificadas: sin clipping (pico 0,71), RMS ≈ 0,19–0,23, dinámica por segundo
  real, contenido armónico (ZCR 478–1480 Hz), duraciones 23–51 s.
- **Arte del README.** Generado por código (`tools/make_brand_art.py`), sin
  material de Capcom.
- **CI de escritorio en tres plataformas.** El workflow `Release` compiló el
  setup host en Linux, Windows y macOS en runners reales, y los tres `.zip`
  quedaron adjuntos a la release `v0.0.1`. El gate `Desktop host` corrió verde
  en Linux (pruebas + compilación).

## Lo que está escrito pero NO ejecutado

- **La app Android.** `android/` existe, con actividades, capa táctil y puente
  JNI, pero en la máquina donde se preparó esto no hay SDK ni NDK: nunca se
  compiló ni se ejecutó en un teléfono. El job de CI de Android es manual,
  experimental y marcado `continue-on-error` por eso mismo. Tampoco se ha
  corrido.
- **`rom-build.yml`.** Es el workflow que arma el binario jugable leyendo tu
  ROM desde un secreto. Está escrito y valida el SHA-256 antes de compilar,
  pero nunca se ejecutó: requiere que el dueño del repositorio cargue
  `MMX3_ROM_BASE64`.
- **La integración de las cápsulas en el juego.** El barajado es correcto y
  probado, pero vive en Python, no dentro del binario. Conectarlo requiere la
  tabla de objetos por etapa y un hook de lectura de semilla en el código
  recompilado.
- **La banda sonora dentro del juego.** Las pistas son Ogg Vorbis reproducibles,
  no música del motor de sonido de X3. Ver `MUSICA.md` para los dos caminos.

## Lo que NO existe y no se puede fabricar en una sesión

Para que no haya ambigüedad: **esta versión no es un ROM hack**. No trae
sprites nuevos de jefes, mapas nuevos, música insertada en el SPC ni el texto
del juego traducido dentro del cartucho. Eso es un proyecto de meses, no de
una tarde, y requiere:

1. **Gráficos**: dibujar ocho jefes y ocho etapas en el formato de tiles y
   paletas de X3, comprimirlos con el esquema del juego (LC_LZ) e insertarlos
   en espacio libre del banco correspondiente.
2. **Código de jefe**: rutinas de IA y de colisión escritas en 65816 (o en el
   IR del recompilador), con las tablas de daño y el anillo de debilidades.
3. **Guion**: encontrar y reemplazar los bloques de texto del juego, que usa
   un formato propio; el guion de `GUION.md` está listo para traducirse a ese
   formato, no dentro de él.
4. **Música**: recomponer los doce temas como secuencias del driver de sonido
   de X3, no como PCM.
5. **Pruebas**: jugar las ocho etapas completas, en orden de debilidades y en
   orden libre, para descartar callejones sin salida.

Lo que sí entrega la 0.0.1 es todo el andamiaje alrededor de eso: identidad,
historia, guion, diseño de jefes y cápsulas, arte, banda sonora, capa táctil
probada, soporte de mando y CI multiplataforma — más el motor real compilando.

## Orden sugerido para seguir

1. Exponer `snesrecomp_desktop_set_pad_mask()` en el host y cerrar el lazo
   táctil. Es el cambio más chico con el mayor efecto verificable.
2. Validar el build Android en CI (primero que compile, después que arranque).
3. Conectar el barajado de cápsulas a la tabla de objetos de etapa.
4. Recién ahí, arte y jefes nuevos: es el trabajo largo.
