#!/usr/bin/env bash
# Captura una pantalla del juego desde un dispositivo o emulador conectado.
#
#   tools/capture_android.sh [salida.png] [serial]
#
# La usamos para las capturas del README. Necesita un dispositivo con la app
# instalada y el dump del jugador ya cargado (ver docs/ANDROID.md): sin ROM el
# juego no dibuja nada, y una captura de la pantalla de selección de ROM no es
# una captura de una etapa.
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${1:-"$ROOT/docs/img/android-etapa-1.png"}
SERIAL=${2:-}
ADB=${ADB:-adb}

if [ -n "$SERIAL" ]; then
  ADB="$ADB -s $SERIAL"
fi

if ! $ADB get-state >/dev/null 2>&1; then
  echo "error: no hay dispositivo conectado (\`adb devices\`)" >&2
  exit 1
fi

if ! $ADB shell pidof cl.zerohistory.mmx >/dev/null 2>&1; then
  echo "aviso: la app no está corriendo; abrila y entrá a la etapa que querés capturar" >&2
fi

mkdir -p "$(dirname "$OUT")"
$ADB exec-out screencap -p > "$OUT"
echo "$OUT"
