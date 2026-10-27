#!/usr/bin/env bash
# El ancho de campo es el contrato de "16:9 en todas las versiones": 342 px
# con cualquier ventana de 16:9 o más ancha, 256 (4:3 auténtico) si la ventana
# no da para el campo ancho. Se compila x3_display.c suelto, sin SDL ni ROM.
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${OUT:-/tmp/x3_display_width_test}
CC=${CC:-cc}

cat > "$OUT.c" <<'C'
#include <stdio.h>
#include "x3_display.h"

int main(void) {
  static const struct { int w, h, want; } cases[] = {
    {1280, 720, 342}, {1920, 1080, 342}, {2340, 1080, 342}, {3440, 1440, 342},
    {960, 720, 256}, {640, 480, 256}, {800, 600, 256},
  };
  int failures = 0;
  for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
    int on = X3Display_ComputeFrameWidth(cases[i].w, cases[i].h, 1);
    int off = X3Display_ComputeFrameWidth(cases[i].w, cases[i].h, 0);
    if (on != cases[i].want || off != 256) {
      printf("FAIL %dx%d: widescreen=%d (quiero %d), 4:3=%d (quiero 256)\n",
             cases[i].w, cases[i].h, on, cases[i].want, off);
      ++failures;
    }
  }
  /* La presentación 16:9 de 342x224 mantiene la relación de píxel 7:6. */
  int pw = 0, ph = 0;
  X3Display_ComputePresentationSize(342, 224, &pw, &ph);
  if (!(pw > 398 && pw < 400 && ph == 224)) {
    printf("FAIL 342x224 se presenta como %dx%d (quiero 399x224)\n", pw, ph);
    ++failures;
  }
  if (failures) return 1;
  printf("display width: all checks passed\n");
  return 0;
}
C

"$CC" -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -I"$ROOT/src" -I"$ROOT/snesrecomp/runner/src" \
  "$OUT.c" "$ROOT/src/x3_display.c" -o "$OUT"
"$OUT"
