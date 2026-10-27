#!/usr/bin/env bash
# Build the ROM-free Android APK (LLE interpreter host) end to end.
#
#   tools/build_android.sh [abi]
#
# The APK ships no ROM-derived code: src/interpreter_only/dispatch_stub.c
# gives the runner empty AOT tables, and the player drops their own mmx3.sfc
# into the app's external files directory. See docs/ANDROID.md.
#
# Environment (all optional):
#   ANDROID_SDK_ROOT / ANDROID_HOME   SDK root (default: ~/Android/Sdk)
#   ANDROID_NDK_HOME                  NDK r27 (default: $SDK/ndk/27.0.12077973)
#   JAVA_HOME                         JDK 17
#   GRADLE                            gradle executable (default: `gradle`)
#   SNESRECOMP_SDL3_SOURCE_DIR        pre-fetched SDL3 source tree
#   MMX_KEYSTORE, MMX_KEY_ALIAS, MMX_KEYSTORE_PASSWORD, MMX_KEY_PASSWORD
#                                     release signing; generated if absent
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ABI=${1:-arm64-v8a}
API=${MMX_ANDROID_API:-24}
BUILD=${MMX_ANDROID_BUILD_DIR:-"$ROOT/build-android"}
TOOLS=${MMX_TOOLCHAIN_DIR:-"$ROOT/../.toolchains"}
APK_OUT="$ROOT/android/app/build/outputs/apk/release"

SDK=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-"$HOME/Android/Sdk"}}
NDK=${ANDROID_NDK_HOME:-"$SDK/ndk/27.0.12077973"}
if [ ! -f "$NDK/build/cmake/android.toolchain.cmake" ]; then
  echo "error: NDK r27 not found at $NDK" >&2
  echo "       set ANDROID_NDK_HOME or install ndk;27.0.12077973" >&2
  exit 1
fi

CMAKE=${CMAKE:-cmake}
NINJA=${NINJA:-ninja}
command -v "$CMAKE" >/dev/null || { echo "error: cmake not found" >&2; exit 1; }
command -v "$NINJA" >/dev/null || { echo "error: ninja not found" >&2; exit 1; }

echo "== configure ($ABI, android-$API, LLE only)"
"$CMAKE" -S "$ROOT" -B "$BUILD" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI="$ABI" \
  -DANDROID_PLATFORM="android-$API" \
  -DANDROID_STL=c++_static \
  -DCMAKE_BUILD_TYPE=Release \
  -DMMX_LLE_ONLY=ON \
  -DSNESRECOMP_SDL_BACKEND=SDL3 \
  -DSNESRECOMP_SDL3_FETCH=ON \
  ${SNESRECOMP_SDL3_SOURCE_DIR:+-DSNESRECOMP_SDL3_SOURCE_DIR="$SNESRECOMP_SDL3_SOURCE_DIR"}

echo "== build"
"$CMAKE" --build "$BUILD" --target MegaManX3SNESRecomp --parallel "${MMX_JOBS:-4}"

GAME_LIB=$(find "$BUILD" -maxdepth 3 -name 'libMegaManX3SNESRecomp.so' | head -1)
if [ -z "$GAME_LIB" ]; then
  echo "error: libMegaManX3SNESRecomp.so was not produced" >&2
  exit 1
fi

JNI_DIR="$ROOT/android/app/src/main/jniLibs/$ABI"
# Un APK lleva una sola ABI: restos de una corrida anterior (otra ABI) no
# deben colarse en el paquete.
rm -rf "$ROOT/android/app/src/main/jniLibs"
mkdir -p "$JNI_DIR"
cp -f "$GAME_LIB" "$JNI_DIR/libMegaManX3SNESRecomp.so"
echo "   staged $(basename "$GAME_LIB")"

# SDL3 is built statically into the game library (runner.cmake forces
# SDL_STATIC ON). If a platform build still emits a shared SDL3, package it;
# MainActivity loads it first in that case.
SDL_SHARED=$(find "$BUILD" -name 'libSDL3.so' | head -1 || true)
if [ -n "$SDL_SHARED" ]; then
  cp -f "$SDL_SHARED" "$JNI_DIR/libSDL3.so"
  echo "   staged libSDL3.so (shared SDL3 build)"
fi

# SDL's Java surface (SDLActivity and friends) is part of the SDL source tree,
# not a Maven artifact. Copy it into the app source set; it is git-ignored.
SDL_SRC=${SNESRECOMP_SDL3_SOURCE_DIR:-$(find "$BUILD/_deps" -maxdepth 2 -type d -name 'sdl3-src' 2>/dev/null | head -1)}
if [ -z "${SDL_SRC:-}" ] || [ ! -d "$SDL_SRC/android-project/app/src/main/java/org/libsdl" ]; then
  echo "error: SDL3 Java sources not found; set SNESRECOMP_SDL3_SOURCE_DIR" >&2
  exit 1
fi
rm -rf "$ROOT/android/app/src/main/java/org/libsdl"
mkdir -p "$ROOT/android/app/src/main/java/org"
cp -r "$SDL_SRC/android-project/app/src/main/java/org/libsdl" \
      "$ROOT/android/app/src/main/java/org/"
echo "   staged SDL Java surface from $SDL_SRC"

# The mod runtime reads its catalog from the filesystem, beside the executable.
# On Android it is packaged as an asset and AssetInstaller copies it to the
# app's external files directory on first launch.
if [ -d "$ROOT/mods/preloaded/packages" ]; then
  rm -rf "$ROOT/android/app/src/main/assets/mods"
  mkdir -p "$ROOT/android/app/src/main/assets/mods/preloaded"
  cp -r "$ROOT/mods/preloaded/packages" \
        "$ROOT/android/app/src/main/assets/mods/preloaded/"
  echo "   staged mod catalog into assets/mods"
fi

# Signing: reuse MMX_KEYSTORE or generate one outside the tree. A generated
# key is fine for a single sideloaded build; keep it if you plan to publish
# updates, because Android refuses an APK signed by a different key.
if [ -z "${MMX_KEYSTORE:-}" ]; then
  mkdir -p "$TOOLS"
  MMX_KEYSTORE="$TOOLS/mmx-release.jks"
  if [ ! -f "$MMX_KEYSTORE" ]; then
    echo "== generate signing key at $MMX_KEYSTORE"
    keytool -genkeypair -v -keystore "$MMX_KEYSTORE" -alias mmx \
      -keyalg RSA -keysize 2048 -validity 10000 \
      -storepass "${MMX_KEYSTORE_PASSWORD:-mmxzerohistory}" \
      -keypass "${MMX_KEY_PASSWORD:-mmxzerohistory}" \
      -dname "CN=MMX Zero History, OU=Zero History, O=Zero History, L=Santiago, C=CL" \
      >/dev/null
  fi
  export MMX_KEYSTORE
  export MMX_KEY_ALIAS=${MMX_KEY_ALIAS:-mmx}
  export MMX_KEYSTORE_PASSWORD=${MMX_KEYSTORE_PASSWORD:-mmxzerohistory}
  export MMX_KEY_PASSWORD=${MMX_KEY_PASSWORD:-mmxzerohistory}
fi

GRADLE_BIN=${GRADLE:-$(command -v gradle || true)}
if [ -z "$GRADLE_BIN" ] && [ -x "$TOOLS/gradle-8.7/bin/gradle" ]; then
  GRADLE_BIN="$TOOLS/gradle-8.7/bin/gradle"
fi
if [ -z "$GRADLE_BIN" ]; then
  echo "error: gradle not found; set GRADLE or install Gradle 8.7+" >&2
  exit 1
fi

echo "== gradle assembleRelease"
(cd "$ROOT/android" && "$GRADLE_BIN" --no-daemon -PmmxAbi="$ABI" assembleRelease)

APK=$(find "$APK_OUT" -maxdepth 1 -name '*.apk' | head -1)
if [ -z "$APK" ]; then
  echo "error: no APK produced under $APK_OUT" >&2
  exit 1
fi
mkdir -p "$ROOT/dist"
NAMED="$ROOT/dist/MMXZeroHistory-android-$ABI.apk"
cp -f "$APK" "$NAMED"
echo "== APK: $NAMED"
ls -lh "$NAMED"
