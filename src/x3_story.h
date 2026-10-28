/* Overlay narrativo de MMX Zero History.
 *
 * El guion vive en `content/story_es.txt`; `tools/build_story.py` lo empaqueta
 * en `src/x3_story_data.c` usando las mismas páginas de texto del cartucho.
 * Esta capa escribe esas páginas sobre la copia EN MEMORIA del dump del
 * jugador, y sólo después de comprobar que el SHA-256 de la imagen cargada es
 * el del dump soportado. Un ROM distinto no recibe nada.
 *
 * No se guardan bytes del guion original en el repositorio: el generador lee
 * el dump en la máquina del jugador para conocer el tamaño de cada página, y
 * emite únicamente nuestro texto, las direcciones y los largos.
 */
#ifndef X3_STORY_H
#define X3_STORY_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct X3StoryPage {
  uint32_t address;             /* offset lineal en la imagen sin cabecera */
  uint32_t length;              /* largo exacto de la página original */
  const unsigned char *bytes;   /* reemplazo, mismo largo */
} X3StoryPage;

extern const X3StoryPage kX3StoryPages[];
extern const unsigned kX3StoryPageCount;

/* Aplica el overlay. Idempotente. Si el dump no es el soportado, no escribe
 * nada y lo informa una sola vez por stderr. */
void X3Story_Init(void);

/* 1 si el overlay se aplicó sobre esta imagen. */
int X3Story_IsActive(void);

/* Páginas efectivamente escritas (0 si no se aplicó). */
unsigned X3Story_AppliedPages(void);

#ifdef __cplusplus
}
#endif

#endif /* X3_STORY_H */
