#!/usr/bin/env bash
# Pruebas de aplicación del overlay narrativo, contra un motor simulado.
#
# El overlay escribe en la imagen del jugador; lo que hay que probar no es sólo
# que el digest se compare bien (tools/test_story_guard.sh), sino que la
# escritura ocurre EXACTAMENTE cuando corresponde y nunca antes. Este test
# enlaza src/x3_story.c y los datos generados contra un cartucho simulado:
#
#   - digest distinto  -> cero páginas escritas, imagen intacta
#   - digest correcto  -> todas las páginas escritas, byte por byte
#   - segunda llamada  -> idempotente, no vuelve a escribir
#
# El SHA-256 se sustituye por un stub para poder fijar el digest sin el dump
# real; el hash de verdad lo cubren verify_rom.py y test_story_guard.sh.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CC=${CC:-cc}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

cat > "$OUT/test_apply.c" <<'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common_cpu_infra.h"
#include "common_rtl.h"
#include "snes/cart.h"
#include "snes/snes.h"
#include "sha256.h"
#include "x3_story.h"
#include "x3_story_guard.h"

/* ── motor simulado ────────────────────────────────────────────────────── */
Snes *g_snes;
Cpu *g_snes_cpu;
const uint8 *g_rom;
Ppu *g_ppu;
Dma *g_dma;
uint8 g_snesrecomp_last_hdmaen;
uint8 g_ram[0x20000];

/* Digest elegido por el test: sha256_compute lo devuelve tal cual. */
static unsigned char g_digest[32];
void sha256_compute(const uint8_t *data, size_t len, uint8_t out[32]) {
  (void)data;
  (void)len;
  memcpy(out, g_digest, 32);
}

static int failures;
static void check(int condition, const char *what) {
  if (!condition) {
    printf("FAIL %s\n", what);
    failures++;
  }
}

/* Crea una imagen de 2 MiB con el contenido "original" reconocible. */
static uint8_t *make_image(size_t *size) {
  const size_t n = 2u * 1024u * 1024u;
  uint8_t *rom = malloc(n);
  for (size_t i = 0; i < n; ++i) rom[i] = (uint8_t)(i * 7u + 3u);
  *size = n;
  return rom;
}

static void bind(Snes *snes, Cart *cart, uint8_t *rom, size_t size) {
  memset(snes, 0, sizeof *snes);
  memset(cart, 0, sizeof *cart);
  cart->rom = rom;
  cart->romSize = (uint32_t)size;
  cart->romImageSize = (uint32_t)size;
  snes->cart = cart;
  g_snes = snes;
  g_rom = rom;
}

int main(int argc, char **argv) {
  const int accept = argc > 1 && strcmp(argv[1], "accept") == 0;
  Snes snes;
  Cart cart;
  size_t size = 0;
  uint8_t *rom = make_image(&size);
  uint8_t *pristine = malloc(size);
  memcpy(pristine, rom, size);
  bind(&snes, &cart, rom, size);

  if (accept) memcpy(g_digest, kX3StoryExpectedSha256, sizeof g_digest);
  else memset(g_digest, 0xAB, sizeof g_digest);

  X3Story_Init();

  if (!accept) {
    check(!X3Story_IsActive(), "un digest distinto no debe activar el overlay");
    check(X3Story_AppliedPages() == 0, "un digest distinto no debe escribir");
    check(memcmp(rom, pristine, size) == 0,
          "un digest distinto no debe modificar la imagen");
  } else {
    check(X3Story_IsActive(), "el dump soportado debe activar el overlay");
    check(X3Story_AppliedPages() == kX3StoryPageCount,
          "deben escribirse todas las páginas declaradas");
    for (unsigned i = 0; i < kX3StoryPageCount; ++i) {
      const X3StoryPage *page = &kX3StoryPages[i];
      check(page->address + page->length <= size, "página fuera de la imagen");
      check(memcmp(rom + page->address, page->bytes, page->length) == 0,
            "la página no quedó escrita tal cual");
      if (i == 0) continue;
      check(kX3StoryPages[i - 1].address + kX3StoryPages[i - 1].length <=
                page->address,
            "dos páginas se solapan");
    }
    /* Nada fuera de las páginas cambió. */
    for (unsigned i = 0; i < kX3StoryPageCount; ++i) {
      const X3StoryPage *page = &kX3StoryPages[i];
      memcpy(pristine + page->address, page->bytes, page->length);
    }
    check(memcmp(rom, pristine, size) == 0,
          "se modificaron bytes fuera de las páginas declaradas");
  }

  /* Sólo texto: ASCII imprimible o el salto de línea del juego. */
  for (unsigned i = 0; i < kX3StoryPageCount; ++i) {
    const X3StoryPage *page = &kX3StoryPages[i];
    for (unsigned j = 0; j < page->length; ++j) {
      unsigned char v = page->bytes[j];
      if (v == 0x20 || (v >= 0x21 && v < 0x7F) || v == 0x80) continue;
      printf("FAIL página 0x%06X +%u: byte 0x%02X no es texto\n",
             (unsigned)page->address, j, v);
      failures++;
      break;
    }
  }

  free(pristine);
  free(rom);
  if (failures == 0)
    printf("ok: %s (%u páginas)\n", accept ? "aplicación" : "rechazo",
           kX3StoryPageCount);
  return failures != 0;
}
EOF

"$CC" -std=c11 -Wall -Wextra \
  -I"$ROOT/src" -I"$ROOT/snesrecomp/runner/src" \
  "$OUT/test_apply.c" \
  "$ROOT/src/x3_story.c" "$ROOT/src/x3_story_guard.c" "$ROOT/src/x3_story_data.c" \
  -o "$OUT/test_apply" 2>&1 | head -30

"$OUT/test_apply" reject
"$OUT/test_apply" accept
