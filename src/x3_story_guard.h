/* Política de identidad del overlay narrativo.
 *
 * Vive aparte de x3_story.c para poder probarla en el host, sin motor ni
 * dump: `bash tools/test_story_guard.sh`. El overlay escribe bytes sobre la
 * imagen cargada, así que la comparación de digest es una condición de
 * seguridad, no un detalle de implementación.
 */
#ifndef X3_STORY_GUARD_H
#define X3_STORY_GUARD_H

#include <stddef.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

/* SHA-256 del único dump que este port recompila (Mega Man X3 USA, 2 MiB sin
 * cabecera). Debe coincidir con `tools/verify_rom.py`. */
extern const unsigned char kX3StoryExpectedSha256[32];

/* 1 si `digest` es el dump soportado. `digest` debe tener 32 bytes. */
int X3Story_DigestMatches(const unsigned char *digest);

/* Escribe el digest como 64 hex minúsculas + NUL. */
void X3Story_DigestHex(const unsigned char *digest, char *out, size_t cap);

#ifdef __cplusplus
}
#endif

#endif /* X3_STORY_GUARD_H */
