/* MMX Zero History identity/adaptation layer for the shared X2/X3 desktop host.
 *
 * The ROM identity below is deliberately UNCHANGED from Mega Man X3 (USA):
 * Zero History is a recompiled build of that cartridge, so keeping the digest
 * is what lets the launcher accept the player's own dump. Only the
 * presentation identity (names, titles, version) is rebranded. */
#define MMX_RTL_HEADER "x3_rtl.h"
#define MMX_DISPLAY_HEADER "x3_display.h"
#define MMX_SPC_HEADER "x3_spc_player.h"

#define MMX_WINDOW_TITLE "MMX Zero History (Recompiled)"
#define MMX_GAME_NAME "MMX Zero History"
#define MMX_GAME_REGION "(USA)"
#define MMX_LAUNCHER_TITLE "MMX Zero History \xE2\x80\x94 Launcher"
#define MMX_ROM_CRC32 0xFA0FE671u
#define MMX_ROM_SHA256_BYTES \
  0x65,0xb0,0x32,0x68,0xaf,0xac,0x29,0x63, \
  0x30,0xe8,0xff,0x8d,0x60,0xdd,0x08,0x25, \
  0x87,0x9e,0x13,0xed,0x65,0x8b,0x37,0x71, \
  0x3c,0x03,0x4a,0x3b,0xd0,0x74,0xf1,0xd7
#define MMX_ROM_SHA256_HEX \
  "65b03268afac296330e8ff8d60dd0825879e13ed658b37713c034a3bd074f1d7"
#define MMX_MOD_GAME_ID "megaman-x3-us"
#define MMX_ROM_FILE "mmx3.sfc"
#define MMX_ROM_CRC32_HEX "FA0FE671"
#define MMX_DEBUG_PORT 4384
#define MMX_HAS_BG3_SUB_OVERLAY 0
#define MMX_WIDESCREEN_STATUS_LINES \
  "# is native 4:3. X3's BG gutters, HUD, and object activation/cull\n" \
  "# windows are adapted for 16:9. See docs/WIDESCREEN.md.\n"

#define MmxDisplayViewport X3DisplayViewport
#define MmxDisplay_ComputeFrameWidth X3Display_ComputeFrameWidth
#define MmxDisplay_ComputeViewport X3Display_ComputeViewport
#define MmxDisplay_GetWindowBaseWidth X3Display_GetWindowBaseWidth
#define MmxDisplay_GetWindowBaseHeight X3Display_GetWindowBaseHeight
#define MmxDisplay_SetWidescreenEnabled X3Display_SetWidescreenEnabled
#define MmxDisplay_IsWidescreenEnabled X3Display_IsWidescreenEnabled
#define MmxDisplay_IsWidescreenActive X3Display_IsWidescreenActive
#define MmxDisplay_GetCurrentFrameWidth X3Display_GetCurrentFrameWidth
#define MmxConfigureWsHud X3ConfigureWsHud
#define MmxConfigureWsBgMargins X3ConfigureWsBgMargins
#define kMmxGameInfo kX3GameInfo

#ifdef __ANDROID__
/* The native host's only output channel is stderr, and Android gives a
 * process no stderr. Without this the app dies silently -- which is exactly
 * how v0.0.2 shipped: no ROM, `main` returned 1, and the activity finished
 * with nothing in logcat.
 *
 * RomSetupActivity checks the ROM before starting the game, so this log is
 * the second line of defence: if the run stops after that check, the last
 * lines here name the reason and the setup screen shows them.
 *
 * The log lands in the app's working directory, which is where the setup
 * screen and `adb pull` both look for it. */
#define MMX_ANDROID_LOG_NAME "native.log"
#define MMX_ANDROID_CWD_FILE "/data/data/cl.zerohistory.mmx/files/cwd.txt"
#define MMX_DESKTOP_ENTRY mmx_desktop_entry
#endif

#include "desktop/mmx23_host_main.inc"

#ifdef __ANDROID__
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* The host resolves `config.ini`, `keybinds.ini`, `saves/`, the log and the
 * ROM relative to the process working directory. An app process starts in
 * `/`, which is not writable: before this, config and saves had to be
 * re-anchored by the host and the mod catalog resolved against
 * `/system/bin` (a read-only filesystem).
 *
 * Java cannot chdir, so AssetInstaller writes the app's external files path
 * into a fixed private file and this reads it before the host starts. If the
 * file is missing the host still runs, with whatever cwd it inherited. */
static void mmx_android_enter_workdir(void) {
  FILE *f = fopen(MMX_ANDROID_CWD_FILE, "r");
  if (!f) return;
  char dir[1024];
  if (fgets(dir, sizeof(dir), f)) {
    size_t n = strlen(dir);
    while (n && (dir[n - 1] == '\n' || dir[n - 1] == '\r')) dir[--n] = '\0';
    if (n && chdir(dir) == 0) setenv("MMX_WORKDIR", dir, 1);
  }
  fclose(f);
}

int main(int argc, char **argv) {
  mmx_android_enter_workdir();

  /* One truncating run per launch, unbuffered: a crash or an exit() must not
   * lose the line that explains why the process is going away. The previous
   * run is kept so a re-launch does not erase the evidence. */
  rename(MMX_ANDROID_LOG_NAME, "native.prev.log");
  FILE *log = fopen(MMX_ANDROID_LOG_NAME, "w");
  if (log) {
    setvbuf(log, NULL, _IONBF, 0);
    dup2(fileno(log), STDERR_FILENO);
    dup2(fileno(log), STDOUT_FILENO);
  }
  fprintf(stderr, "[mmx] main entry (cwd=%s)\n", getenv("MMX_WORKDIR") ? getenv("MMX_WORKDIR") : "?");
#ifdef SNESRECOMP_BUILD_VERSION
  /* La pantalla de entrada lee esta línea para enseñar qué build corrió. */
  fprintf(stderr, "[mmx] build=%s\n", SNESRECOMP_BUILD_VERSION);
#endif
  int rc = mmx_desktop_entry(argc, argv);
  fprintf(stderr, "[mmx] main exit rc=%d\n", rc);
  return rc;
}
#endif
