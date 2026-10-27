/* Touch control geometry and multi-touch tracking for the Android build.
 *
 * This file is deliberately free of SDL and of guest state: it is pure input
 * bookkeeping, so it can be compiled and unit-tested on the desktop. The
 * Android layer feeds it normalised touch coordinates and pulls a 12-bit pad
 * mask out of it; the guest never sees a finger.
 *
 * Bit layout matches snesrecomp's keybinds word (runner/src/keybinds.h):
 *   bit  0 R   bit  1 L   bit  2 X   bit  3 A
 *   bit  4 Right  bit 5 Left  bit 6 Down  bit 7 Up
 *   bit  8 Start  bit  9 Select  bit 10 Y  bit 11 B
 */
#ifndef X3_TOUCH_CONTROLS_H
#define X3_TOUCH_CONTROLS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define X3_TOUCH_MAX_BUTTONS 12
#define X3_TOUCH_MAX_FINGERS 10

typedef enum {
  X3_BIT_R = 0,
  X3_BIT_L = 1,
  X3_BIT_X = 2,
  X3_BIT_A = 3,
  X3_BIT_RIGHT = 4,
  X3_BIT_LEFT = 5,
  X3_BIT_DOWN = 6,
  X3_BIT_UP = 7,
  X3_BIT_START = 8,
  X3_BIT_SELECT = 9,
  X3_BIT_Y = 10,
  X3_BIT_B = 11,
  X3_BIT_COUNT = 12
} X3PadBit;

#define X3_PAD_MASK_ALL 0x0FFFu

typedef struct {
  float x, y, w, h; /* normalised 0..1, origin top-left */
  int bit;          /* X3PadBit this region produces */
} X3TouchButton;

typedef struct {
  X3TouchButton buttons[X3_TOUCH_MAX_BUTTONS];
  /* Authored x of each button, kept so mirroring is an exact involution:
   * recomputing 1-x-w on each toggle drifts in floating point. */
  float authored_x[X3_TOUCH_MAX_BUTTONS];
  int count;
  /* 0 = layout authored for right-handed play; 1 = mirrored. */
  int mirrored;
  /* 0..100, presentation only: the binding logic never reads this. */
  int opacity;
} X3TouchLayout;

/* A lit bit and the finger holding it. */
typedef struct {
  int64_t finger_id; /* -1 when the slot is free */
  uint16_t bits;     /* one or more bits latched at touch-down */
} X3TouchFingerSlot;

typedef struct {
  X3TouchFingerSlot fingers[X3_TOUCH_MAX_FINGERS];
  uint16_t held; /* union of every active slot */
  /* Bits a finger latched stay held until that finger lifts, even if it
   * slides off the button. Platformers need that: a thumb drifting while
   * pressing right must not drop the input mid-jump. */
  int latch_on_slide;
} X3TouchTracker;

/* Fill a default layout: D-pad bottom-left, face diamond bottom-right,
 * shoulders above the diamond, start centred near the bottom. */
void X3Touch_DefaultLayout(X3TouchLayout *layout);

/* Mirror the layout horizontally in place. Idempotent per call: toggling
 * twice returns to the authored layout. */
void X3Touch_SetMirrored(X3TouchLayout *layout, int mirrored);

/* Return the pad mask under a normalised point, or 0. Overlapping regions
 * OR together, so a fat finger across a seam never yields nothing. */
uint16_t X3Touch_HitTest(const X3TouchLayout *layout, float nx, float ny);

void X3Touch_Reset(X3TouchTracker *tracker);

/* Register a touch-down. Returns the bits this press added. A repeated
 * down for a finger already tracked is ignored (no duplicate bits). */
uint16_t X3Touch_Down(X3TouchTracker *tracker, int64_t finger_id,
                      const X3TouchLayout *layout, float nx, float ny);

/* Register a touch-up. Returns the bits released. Unknown ids are ignored. */
uint16_t X3Touch_Up(X3TouchTracker *tracker, int64_t finger_id);

/* Every bit currently held, latches included. */
uint16_t X3Touch_Active(const X3TouchTracker *tracker);

/* Nonzero if the tracker is holding nothing. */
int X3Touch_IsIdle(const X3TouchTracker *tracker);

#ifdef __cplusplus
}
#endif

#endif /* X3_TOUCH_CONTROLS_H */
