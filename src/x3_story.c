/* Ver x3_story.h. */
#include "x3_story.h"

#include <stdio.h>
#include <string.h>

#include "common_cpu_infra.h"
#include "common_rtl.h"
#include "sha256.h"
#include "snes/cart.h"
#include "snes/snes.h"
#include "x3_story_guard.h"

static int s_tried;
static int s_active;
static unsigned s_applied;

void X3Story_Init(void) {
  if (s_tried) return;
  s_tried = 1;

  if (!g_snes || !g_snes->cart || !g_snes->cart->rom || !g_rom) {
    fprintf(stderr, "[mmx] historia: sin imagen de cartucho, no se aplica\n");
    return;
  }

  const size_t rom_size = g_snes->cart->romImageSize;
  unsigned char digest[32];
  sha256_compute(g_rom, rom_size, digest);
  if (!X3Story_DigestMatches(digest)) {
    char hex[65];
    X3Story_DigestHex(digest, hex, sizeof hex);
    fprintf(stderr,
            "[mmx] historia: ROM distinto (%s), no se aplica el guion\n", hex);
    return;
  }

  unsigned applied = 0;
  unsigned skipped = 0;
  for (unsigned i = 0; i < kX3StoryPageCount; ++i) {
    const X3StoryPage *page = &kX3StoryPages[i];
    if ((size_t)page->address + page->length > rom_size) {
      ++skipped;
      continue;
    }
    memcpy((unsigned char *)g_rom + page->address, page->bytes, page->length);
    ++applied;
  }

  s_active = 1;
  s_applied = applied;
  fprintf(stderr,
          "[mmx] historia: %u/%u pagina(s) aplicadas sobre el ROM en memoria%s\n",
          applied, kX3StoryPageCount,
          skipped ? " (alguna quedo fuera de la imagen)" : "");
}

int X3Story_IsActive(void) { return s_active; }

unsigned X3Story_AppliedPages(void) { return s_applied; }
