## La historia entra al juego

Hasta la 0.0.5 el proyecto aplicaba un solo parche al cartucho: el nombre
interno. El guion, los jefes y las cápsulas seguían siendo documentación. Esta
versión mete el guion completo dentro del juego y lo hace verificable.

### Qué cambió en pantalla

El prólogo de Mega Man X3, los diálogos, los textos de las cápsulas y el final
están escritos en chileno y salen del propio motor, con la caja de texto, los
retratos y el temporizado originales. No es una capa encima del juego: son los
mismos bytes de texto del cartucho, reemplazados por los nuestros.

```
[mmx] historia: 214/214 pagina(s) aplicadas sobre el ROM en memoria
```

### Cómo se hizo, y por qué es seguro

El cartucho guarda su guion como **texto ASCII plano** con saltos `0x80 0x80`
entre líneas y comandos de un byte entre páginas. Eso permite reemplazar el
contenido de cada página sin mover ni un puntero:

- `tools/build_story.py` lee el dump, localiza las páginas de texto, y
  empaqueta el guion de `content/story_es.txt` en ellas.
- Cada página conserva **su largo exacto en bytes** y el **mismo número de
  líneas** que el original, así que la caja, el centrado y los comandos de
  control siguen apuntando a lo mismo.
- Ninguna línea pasa de 22 columnas: el motor no envuelve texto, y la tercera
  línea de la caja va centrada, donde 28 columnas ya se cortaban (medido en el
  motor real, no supuesto).
- El generado (`src/x3_story_data.c`) contiene **sólo nuestro texto**, las
  direcciones y los largos. No hay guion original en el repositorio.

La aplicación ocurre en `src/x3_story.c`, después de comprobar el SHA-256 de
la imagen cargada. **Un dump distinto no recibe nada** y el log lo dice:

```
[mmx] historia: ROM distinto (…), no se aplica el guion
```

### Lo que también cambió

- **Tablas de jefes y armas**: los nombres del cast, los ocho maestros con su
  arma y sus stats POWER/SPEED, y el marcador de jefe de etapa.
- **Cápsulas**: los ocho textos de cápsula son los fragmentos de memoria de
  `docs/HISTORIA.md`, con Salas leyendo el archivo.
- **Final**: el Acto III completo, con Cero-Ω, la bofetada de "alguien te dio
  otra orden" y el cierre del archivo W-00.

### Verificación

```console
bash tools/test_story_guard.sh       # política de identidad del overlay
bash tools/test_story_apply.sh       # escribe con el dump bueno, nada con otro
python3 tools/test_story_layout.py   # forma del generado, sin dump
python3 tools/build_story.py --rom mmx3.sfc --check   # qué empaquetaría
```

Los tres corren en CI sin ROM. Los dos primeros compilan el módulo real contra
un cartucho simulado; el tercero escribe en un directorio temporal y compara
byte por byte con el archivo versionado.

### Estado honesto

Lo que **no** cambia: los sprites, los mapas, la música del SPC y la lógica de
los jefes siguen siendo los del cartucho. La historia nueva se cuenta con los
personajes y los escenarios que Mega Man X3 ya tiene — X, Zero, ocho etapas,
ocho jefes — y el guion hace que esos personajes digan otra cosa. Los jefes
nuevos (Cóndor Cobalto, Salitre Sierpe y los otros seis) existen en el texto y
en las tablas de nombre; dibujarlos y programarlos sigue siendo el trabajo
largo que describe `docs/ESTADO.md`.
