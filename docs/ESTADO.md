# Estado real de la versión 0.0.6

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
- **El guion dentro del juego (0.0.6).** `src/x3_story_data.c` lleva 227
  páginas: intro, Acto I, ocho cápsulas, Acto II/III, tablas de jefes y armas,
  y los rótulos del título. Verificado en el motor real: el prólogo y los
  diálogos salen en la caja de texto del juego, y `EMPEZAR / CLAVE / OPCIONES`
  reemplazan el menú del título. Con un dump distinto no se escribe nada y el
  log lo dice.
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
  material de Capcom. Desde la 0.0.2 las cinco láminas y la placa de arranque
  son 1920×1080 (16:9), y el icono de launcher se genera desde el mismo código.
- **16:9 activo por defecto.** El paquete
  `megaman-x3.enhancement.widescreen` declara `default_enabled = true`; el
  catálogo viaja en los zips de escritorio y en los assets del APK. La
  geometría táctil se mide en unidades del lado corto y pasa sus pruebas en
  16:9, 19.5:9, 20:9 y 4:3.
- **APK Android compilado, firmado y ejecutado en un emulador.** Se instalaron
  el emulador y una imagen `google_apis;x86_64` de Android 14 con KVM.
  `tools/build_android.sh` produjo los APK `arm64-v8a` y `x86_64`
  (`versionCode 3`, `versionName 0.0.3`, firmados, con `aapt` y `apksigner`
  verificados). En el emulador: la app abre y **queda abierta** en la pantalla
  de entrada; el selector del sistema importa un `mmx3.sfc`; un archivo con
  SHA-256 distinto se rechaza sin dejar restos; con un dump presente el motor
  llega a `SDL init ok`, `renderer initialized: sdl` y `first frame
  simulated`. El campo con `Widescreen = 1` mide 342 px.
- **Campo 16:9 acotado a 342.** `tools/test_display_width.sh` cubre ventanas
  16:9, 16:10 y ultrawide: 342 px cuando la ventana da para el campo ancho,
  256 en 4:3.
- **CI de escritorio en tres plataformas.** El workflow `Release` compiló el
  setup host en Linux, Windows y macOS en runners reales, y los tres `.zip`
  quedaron adjuntos a la release `v0.0.1`. El gate `Desktop host` corrió verde
  en Linux (pruebas + compilación).

## Qué se ve al jugar (0.0.6)

El juego sigue siendo el cartucho original ejecutado por el intérprete LLE, con
su motor, sus sprites y sus escenarios. Lo que el proyecto cambia en pantalla:

- el nombre, el icono y la placa de arranque de la app;
- el campo 16:9 (342×224) con el HUD y las ventanas de objetos ajustadas;
- la pantalla de entrada, con la importación verificada del ROM y el
  diagnóstico (`build=`, `video: 342x224`);
- **el guion**: prólogo, diálogos, cápsulas, final, nombres de los ocho jefes,
  sus stats y las armas, todo en chileno y dibujado por el motor con su propia
  caja de texto;
- **el menú del título**: `EMPEZAR / CLAVE / OPCIONES`, y `TECLAS` / `SONIDO`
  en opciones.

Lo que sigue sin cambiar: los sprites, los mapas, la música del SPC y la
lógica de los jefes. La historia nueva se cuenta con lo que el cartucho ya
tiene; dibujar a los ocho mavericks sigue siendo el trabajo largo de más abajo.

### La historia ya está en el juego (0.0.6)

El prólogo, los diálogos, los textos de las cápsulas, el final y los nombres de
los ocho jefes salen del motor. No es una capa encima: son las páginas de texto
del propio cartucho, reemplazadas por las nuestras.

```
[mmx] historia: 227/227 pagina(s) aplicadas sobre el ROM en memoria
```

El cartucho guarda el guion como ASCII plano con `0x80 0x80` entre líneas, así
que cada página se puede sustituir conservando su largo exacto en bytes: ningún
puntero ni comando de control se mueve. `tools/build_story.py` empaqueta
`content/story_es.txt` en `src/x3_story_data.c`, y `src/x3_story.c` lo aplica
sobre la imagen cargada **sólo si el SHA-256 es el del dump soportado**.

Las tres invariantes están fijadas por tests, no por disciplina:

- misma longitud de página que el original;
- sólo ASCII imprimible y `0x80` (un byte de control pisado rompería la página);
- ninguna línea de más de 22 columnas — el motor no envuelve texto, y la
  tercera línea de la caja va centrada, donde 28 columnas ya se cortan. Se
  midió en el motor real.

Lo que sigue igual: sprites, mapas, música del SPC y la lógica de los jefes.

### El contenido ya se aplica (0.0.5)

`src/x3_content.c` inicializa `snes_text_xlate` con
`content/zerohistory.toml` y bombea un tick por frame desde
`X3DrawPpuFrame`. La tabla se aplica **sobre la copia en memoria** del ROM del
jugador, guardada por contenido: un `source_hex` que no coincide no escribe
nada. Verificado en el emulador Android con un dump sintético que lleva la
cabecera real:

```
[mmx] contenido: tabla content/zerohistory.toml, idioma es, 1 parche(s) de ROM, 0 de VRAM
[mmx] contenido: 1/1 parche(s) de ROM aplicados
```

El parche incluido es la identidad interna del cartucho (cabecera LoROM,
`0x7FC0`). `tools/x3_content_patch.py` aplica la misma tabla a una copia en
disco con checksum SNES recalculado, y `tools/test_content_patch.py` cubre el
motor con imágenes sintéticas.

Lo que **sigue** sin insertarse en el juego es todo lo demás: guion, jefes,
mapas y música. Eso exige derivar del dump los glifos (mapa carácter → byte de
la fuente de X3), las direcciones de los bloques de texto y los tiles
comprimidos. Adivinarlos escribe basura legible por el juego, así que no se
hace. Ver `docs/CONTENIDO.md`.

## Lo que está escrito pero NO ejecutado

- **Una partida Android real.** El emulador arranca la app y el motor, pero
  este repositorio no incluye el ROM: con un archivo aleatorio el guest termina
  en un bucle de `BRK`. Falta un teléfono con el dump del dueño y medir el
  intérprete en ARM.
- **El catálogo de mods en Android.** El host lo resuelve relativo a
  `/system/bin`; con `--config` el proceso muere en
  `snes_mod_runtime_commit_c` (reproducido en el emulador). El 16:9 viaja por
  `config.ini`. Es un bug del host, río arriba.
- **El envío de toques al guest.** La capa táctil dibuja y calcula la máscara
  de 12 bits, pero el estado del pad es privado de `host_main.c`; no hay API
  de inyección. Con mando Bluetooth sí se juega.
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

Lo que sí entrega la 0.0.2 es todo el andamiaje alrededor de eso: identidad,
historia, guion, diseño de jefes y cápsulas, arte 16:9, banda sonora, capa
táctil probada, soporte de mando, APK Android y CI multiplataforma — más el
motor real compilando.

## Orden sugerido para seguir

1. Exponer `snesrecomp_desktop_set_pad_mask()` en el host y cerrar el lazo
   táctil. Es el cambio más chico con el mayor efecto verificable.
2. Instalar el APK en un teléfono real y medir el intérprete en ARM; el
   empaquetado ya está verificado, la ejecución no.
3. Conectar el barajado de cápsulas a la tabla de objetos de etapa.
4. Recién ahí, arte y jefes nuevos: es el trabajo largo.
