/* Ver x3_content.h. */
#include "x3_content.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "snes_text_xlate.h"

#ifndef X3_CONTENT_DEFAULT_TABLE
#define X3_CONTENT_DEFAULT_TABLE "content/zerohistory.toml"
#endif

/* Mismo idioma que declara la tabla. "off" desactivaría los parches: el
 * runner sólo escribe los bytes de reemplazo cuando el idioma está activo. */
static const char kLanguage[] = "es";

static int s_tried;
static int s_active;
static char s_path[512];
static unsigned s_rom_patches;
static unsigned s_reported = (unsigned)-1;

/* Extrae un entero de un JSON plano del runner sin arrastrar un parser. */
static unsigned json_uint(const char *json, const char *key) {
  if (!json || !key) return 0;
  char needle[64];
  snprintf(needle, sizeof(needle), "\"%s\":", key);
  const char *at = strstr(json, needle);
  if (!at) return 0;
  at += strlen(needle);
  unsigned value = 0;
  while (*at >= '0' && *at <= '9') value = value * 10u + (unsigned)(*at++ - '0');
  return value;
}

static void stats(char *out, size_t cap) {
  if (!out || cap == 0) return;
  if (!snes_text_xlate_debug_json_c("stats", out, (int)cap)) out[0] = '\0';
}

void X3Content_Init(void) {
  if (s_tried) return;
  s_tried = 1;

  const char *path = getenv("MMX_CONTENT_TABLE");
  if (!path || !*path) path = X3_CONTENT_DEFAULT_TABLE;
  snprintf(s_path, sizeof(s_path), "%s", path);

  if (!snes_text_xlate_init_c(s_path, kLanguage)) {
    /* Falta el archivo o la tabla no parsea: jugar igual es correcto, fingir
     * que hay contenido no lo es. Se dice una vez y se sigue. */
    fprintf(stderr, "[mmx] contenido: no aplicado (%s): %s\n", s_path,
            snes_text_xlate_last_error_c());
    s_path[0] = '\0';
    return;
  }
  s_active = 1;

  char json[512];
  stats(json, sizeof json);
  s_rom_patches = json_uint(json, "rom_patches");
  fprintf(stderr,
          "[mmx] contenido: tabla %s, idioma %s, %u parche(s) de ROM, "
          "%u de VRAM\n",
          s_path, kLanguage, s_rom_patches, json_uint(json, "vram_patches"));
}

void X3Content_Tick(void) {
  if (!s_active) return;
  snes_text_xlate_on_frame_c();

  /* El runner cuenta lo que realmente escribió. Un parche cuyo `source` no
   * coincide con este ROM no se aplica y no se cuenta: esa diferencia es la
   * señal de que el dump no es el esperado, y se informa. */
  char json[512];
  stats(json, sizeof json);
  unsigned applied = json_uint(json, "rom_applies");
  if (applied != s_reported) {
    s_reported = applied;
    if (s_rom_patches) {
      fprintf(stderr, "[mmx] contenido: %u/%u parche(s) de ROM aplicados\n",
              applied, s_rom_patches);
      if (applied < s_rom_patches) {
        fprintf(stderr,
                "[mmx] contenido: los parches que faltan no encontraron sus "
                "bytes originales en este ROM\n");
      }
    }
  }
}

int X3Content_IsActive(void) { return s_active; }

unsigned X3Content_AppliedRomPatches(void) { return s_reported; }

const char *X3Content_TablePath(void) { return s_path; }
