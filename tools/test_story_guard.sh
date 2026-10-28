#!/usr/bin/env bash
# Pruebas de la política de identidad del overlay narrativo.
#
# El overlay escribe bytes sobre la imagen del jugador, así que la comparación
# de digest es una condición de seguridad. Este test compila el módulo solo
# (sin motor ni dump) y comprueba que acepta exactamente el dump soportado y
# que ningún otro digest pasa.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CC=${CC:-cc}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

cat > "$OUT/test_guard.c" <<'EOF'
#include <stdio.h>
#include <string.h>
#include "x3_story_guard.h"

static int failures;

static void check(int condition, const char *what) {
  if (!condition) {
    printf("FAIL %s\n", what);
    failures++;
  }
}

static void digest_from_hex(const char *hex, unsigned char out[32]) {
  for (unsigned i = 0; i < 32; ++i) {
    unsigned value = 0;
    sscanf(hex + 2 * i, "%2x", &value);
    out[i] = (unsigned char)value;
  }
}

int main(void) {
  unsigned char digest[32];
  char hex[65];

  /* El dump soportado pasa. */
  digest_from_hex("65b03268afac296330e8ff8d60dd0825"
                  "879e13ed658b37713c034a3bd074f1d7", digest);
  check(X3Story_DigestMatches(digest), "el dump soportado debe pasar");

  /* Un solo bit distinto ya no pasa. */
  for (unsigned byte = 0; byte < 32; ++byte) {
    unsigned char copy[32];
    memcpy(copy, digest, sizeof copy);
    copy[byte] ^= 0x01;
    check(!X3Story_DigestMatches(copy), "un digest alterado no debe pasar");
  }

  /* Todos ceros y todos 0xFF: los dos valores que aparecen cuando algo sale
   * mal antes de hashear. */
  memset(digest, 0x00, sizeof digest);
  check(!X3Story_DigestMatches(digest), "digest en cero no debe pasar");
  memset(digest, 0xFF, sizeof digest);
  check(!X3Story_DigestMatches(digest), "digest en 0xFF no debe pasar");
  check(!X3Story_DigestMatches(NULL), "NULL no debe pasar");

  /* El hex es el mismo que tools/verify_rom.py. */
  digest_from_hex("65b03268afac296330e8ff8d60dd0825"
                  "879e13ed658b37713c034a3bd074f1d7", digest);
  X3Story_DigestHex(digest, hex, sizeof hex);
  check(strcmp(hex, "65b03268afac296330e8ff8d60dd0825"
                    "879e13ed658b37713c034a3bd074f1d7") == 0,
        "el hex no coincide con verify_rom.py");
  X3Story_DigestHex(digest, hex, 10);
  check(hex[0] == '\0', "un buffer corto debe quedar vacío, no truncado");

  if (failures == 0) printf("ok: política de identidad del overlay\n");
  return failures != 0;
}
EOF

"$CC" -std=c11 -Wall -Wextra -Werror -pedantic \
  -I"$ROOT/src" \
  "$OUT/test_guard.c" "$ROOT/src/x3_story_guard.c" \
  -o "$OUT/test_guard"

"$OUT/test_guard"

# El digest del código y el de la herramienta de verificación son el mismo.
python3 - "$ROOT" <<'EOF'
import re, sys
from pathlib import Path
root = Path(sys.argv[1])
guard = (root / "src" / "x3_story_guard.c").read_text()
verify = (root / "tools" / "verify_rom.py").read_text()
bytes_ = re.findall(r"0x([0-9a-fA-F]{2})", guard.split("kX3StoryExpectedSha256")[1].split("};")[0])
joined = "".join(b.lower() for b in bytes_)
expected = re.search(r'EXPECTED_SHA256 = "([0-9a-f]{64})"', verify).group(1)
if joined != expected:
    print(f"FAIL digest del guard {joined} != verify_rom {expected}")
    raise SystemExit(1)
print("ok: el digest del guard coincide con tools/verify_rom.py")
EOF

# El generador rechaza un ROM que no es el soportado.
if [ -f "$ROOT/mmx3.sfc" ]; then
  python3 "$ROOT/tools/verify_rom.py" "$ROOT/mmx3.sfc" >/dev/null
fi

echo "ok: guard del overlay narrativo"
