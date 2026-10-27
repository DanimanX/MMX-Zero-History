/* Aplicación del contenido propio sobre el ROM del jugador.
 *
 * El proyecto no distribuye el cartucho ni lo modifica en disco: al arrancar,
 * el motor carga el dump del jugador, verifica su identidad y recién entonces
 * esta capa aplica la tabla `content/zerohistory.toml` sobre la copia en
 * memoria (`snes_text_xlate` en el runner). Cada parche está guardado por
 * contenido, así que un ROM distinto no recibe nada a medias.
 *
 * El archivo del jugador queda intacto; `tools/x3_content_patch.py --apply`
 * es la vía para quien quiera además una copia parcheada en disco.
 */
#ifndef X3_CONTENT_H
#define X3_CONTENT_H

#ifdef __cplusplus
extern "C" {
#endif

/* Carga la tabla de contenido. Idempotente y sin efectos si falta el archivo:
 * el juego arranca igual, sin contenido aplicado, y lo dice en el log. */
void X3Content_Init(void);

/* Aplica lo pendiente. Se llama una vez por frame; el propio runner decide
 * cuándo hay trabajo (parches de ROM una sola vez, los de RAM cada frame). */
void X3Content_Tick(void);

/* 1 si la tabla se cargó y el idioma quedó activo. */
int X3Content_IsActive(void);

/* Cantidad de parches de ROM aplicados desde el arranque (0 si ninguno). */
unsigned X3Content_AppliedRomPatches(void);

/* Ruta de la tabla en uso, o "" si no se cargó ninguna. */
const char *X3Content_TablePath(void);

#ifdef __cplusplus
}
#endif

#endif /* X3_CONTENT_H */
