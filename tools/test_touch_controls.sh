#!/usr/bin/env bash
# Build and run the touch-layer unit tests. They are pure C with no SDL and no
# Android dependency, so they run anywhere a host compiler exists.
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SRC="$ROOT/src/platform/android"
OUT=${OUT:-/tmp/x3_touch_controls_test}
CC=${CC:-cc}

"$CC" -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -I"$SRC" \
  "$SRC/x3_touch_controls.c" "$SRC/x3_touch_controls_test.c" \
  -o "$OUT"

"$OUT"
