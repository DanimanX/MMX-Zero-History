/* Implementación de la capa táctil. Ver x3_touch_controls.h. */
#include "x3_touch_controls.h"

#include <string.h>

/* All sizes are short-edge (height) units: a key authored at half = 0.070
 * occupies 14% of the short edge on any display, so it stays square instead
 * of stretching with the window. Positions stay normalised 0..1. */
#define X3_DPAD_CX 0.155f
#define X3_DPAD_CY 0.760f
/* One d-pad key is HALF wide; the four keys are placed ARM away from the
 * centre, which leaves a small dead gap between them. Without the gap the
 * exact centre of one key also tests inside its neighbour, and a straight
 * "up" press would fire "up+left". Diagonals still read as two keys because
 * a thumb landing in the gap is inside both boxes. */
#define X3_DPAD_ARM 0.078f   /* centre offset from the d-pad origin */
#define X3_DPAD_HALF 0.070f  /* half-size of one d-pad key */
#define X3_FACE_CX 0.845f
#define X3_FACE_CY 0.760f
#define X3_FACE_OFF 0.085f
#define X3_FACE_RAD 0.056f
#define X3_SHOULDER_W 0.174f
#define X3_SHOULDER_H 0.070f
#define X3_SHOULDER_Y 0.578f
#define X3_START_W 0.192f
#define X3_START_H 0.062f
#define X3_START_Y 0.640f
#define X3_SELECT_CY 0.870f
#define X3_SELECT_RAD 0.045f

static void put(X3TouchLayout *l, float x, float y, float w, float h, int bit) {
  if (l->count >= X3_TOUCH_MAX_BUTTONS) return;
  /* Keep every key inside the surface even at extreme aspects: a shoulder
   * authored for 16:9 would otherwise poke past the right edge at 1:1. */
  if (x < 0.0f) x = 0.0f;
  if (y < 0.0f) y = 0.0f;
  if (x + w > 1.0f) x = 1.0f - w;
  if (y + h > 1.0f) y = 1.0f - h;
  X3TouchButton *b = &l->buttons[l->count];
  l->authored_x[l->count] = x;
  ++l->count;
  b->x = x;
  b->y = y;
  b->w = w;
  b->h = h;
  b->bit = bit;
}

/* Square key centred on (cx, cy); half is in short-edge units. */
static void put_square(X3TouchLayout *l, float cx, float cy, float half,
                       int bit) {
  float h = half * 2.0f;
  float w = h / l->aspect;
  put(l, cx - w * 0.5f, cy - h * 0.5f, w, h, bit);
}

/* Rectangular key centred on (cx, cy); wu/hu are short-edge units. */
static void put_units(X3TouchLayout *l, float cx, float cy, float wu,
                      float hu, int bit) {
  float w = wu / l->aspect;
  put(l, cx - w * 0.5f, cy - hu * 0.5f, w, hu, bit);
}

static void build_layout(X3TouchLayout *layout, float aspect) {
  memset(layout, 0, sizeof(*layout));
  layout->aspect = aspect;
  layout->opacity = 55;

  /* A horizontal offset of one short-edge unit is 1/aspect in normalised x. */
  const float xu = 1.0f / aspect;

  /* D-pad: four discrete keys, not a virtual stick. X3 is a D-pad game and
   * an analogue stick mapped to four directions eats diagonal inputs. */
  put_square(layout, X3_DPAD_CX, X3_DPAD_CY - X3_DPAD_ARM, X3_DPAD_HALF,
             X3_BIT_UP);
  put_square(layout, X3_DPAD_CX, X3_DPAD_CY + X3_DPAD_ARM, X3_DPAD_HALF,
             X3_BIT_DOWN);
  put_square(layout, X3_DPAD_CX - X3_DPAD_ARM * xu, X3_DPAD_CY,
             X3_DPAD_HALF, X3_BIT_LEFT);
  put_square(layout, X3_DPAD_CX + X3_DPAD_ARM * xu, X3_DPAD_CY,
             X3_DPAD_HALF, X3_BIT_RIGHT);

  /* Face buttons in the SNES diamond: Y top, B right, A bottom, X left. */
  put_square(layout, X3_FACE_CX, X3_FACE_CY - X3_FACE_OFF, X3_FACE_RAD,
             X3_BIT_Y);
  put_square(layout, X3_FACE_CX + X3_FACE_OFF * xu, X3_FACE_CY, X3_FACE_RAD,
             X3_BIT_B);
  put_square(layout, X3_FACE_CX, X3_FACE_CY + X3_FACE_OFF, X3_FACE_RAD,
             X3_BIT_A);
  put_square(layout, X3_FACE_CX - X3_FACE_OFF * xu, X3_FACE_CY, X3_FACE_RAD,
             X3_BIT_X);

  /* Shoulders, above the diamond and aligned with its columns. */
  put_units(layout, X3_FACE_CX - X3_FACE_OFF * xu, X3_SHOULDER_Y,
            X3_SHOULDER_W, X3_SHOULDER_H, X3_BIT_L);
  put_units(layout, X3_FACE_CX + X3_FACE_OFF * xu, X3_SHOULDER_Y,
            X3_SHOULDER_W, X3_SHOULDER_H, X3_BIT_R);

  /* Start: centred, small, out of the play area. */
  put_units(layout, 0.5f, X3_START_Y, X3_START_W, X3_START_H, X3_BIT_START);

  /* Select: lower centre, rarely used but unavoidable in some menus. */
  put_square(layout, 0.5f, X3_SELECT_CY, X3_SELECT_RAD, X3_BIT_SELECT);
}

void X3Touch_DefaultLayout(X3TouchLayout *layout) {
  if (!layout) return;
  build_layout(layout, X3_TOUCH_DEFAULT_ASPECT);
}

void X3Touch_SetAspect(X3TouchLayout *layout, float aspect) {
  if (!layout) return;
  if (!(aspect >= X3_TOUCH_MIN_ASPECT && aspect <= X3_TOUCH_MAX_ASPECT))
    aspect = X3_TOUCH_DEFAULT_ASPECT;
  int mirrored = layout->mirrored;
  int opacity = layout->opacity;
  build_layout(layout, aspect);
  if (opacity > 0) layout->opacity = opacity;
  if (mirrored) X3Touch_SetMirrored(layout, 1);
}

void X3Touch_SetMirrored(X3TouchLayout *layout, int mirrored) {
  if (!layout) return;
  int want = mirrored ? 1 : 0;
  for (int i = 0; i < layout->count; ++i) {
    layout->buttons[i].x = want ? 1.0f - layout->authored_x[i] -
                                      layout->buttons[i].w
                                : layout->authored_x[i];
  }
  layout->mirrored = want;
}

static int inside(const X3TouchButton *b, float nx, float ny) {
  return nx >= b->x && nx <= b->x + b->w &&
         ny >= b->y && ny <= b->y + b->h;
}

uint16_t X3Touch_HitTest(const X3TouchLayout *layout, float nx, float ny) {
  if (!layout) return 0;
  uint16_t bits = 0;
  for (int i = 0; i < layout->count; ++i) {
    if (inside(&layout->buttons[i], nx, ny)) {
      bits |= (uint16_t)(1u << layout->buttons[i].bit);
    }
  }
  return bits;
}

void X3Touch_Reset(X3TouchTracker *tracker) {
  if (!tracker) return;
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    tracker->fingers[i].finger_id = -1;
    tracker->fingers[i].bits = 0;
  }
  tracker->held = 0;
  tracker->latch_on_slide = 1;
}

static uint16_t recompute(X3TouchTracker *t) {
  uint16_t bits = 0;
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    bits |= t->fingers[i].bits;
  }
  t->held = bits;
  return bits;
}

uint16_t X3Touch_Down(X3TouchTracker *tracker, int64_t finger_id,
                      const X3TouchLayout *layout, float nx, float ny) {
  if (!tracker) return 0;
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    if (tracker->fingers[i].finger_id == finger_id) return 0; /* dup */
  }
  uint16_t bits = X3Touch_HitTest(layout, nx, ny);
  if (!bits) return 0; /* pressed empty space: nothing to track */

  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    if (tracker->fingers[i].finger_id == -1) {
      tracker->fingers[i].finger_id = finger_id;
      tracker->fingers[i].bits = bits;
      recompute(tracker);
      return bits;
    }
  }
  return 0; /* finger table full: drop the gesture rather than corrupt state */
}

uint16_t X3Touch_Up(X3TouchTracker *tracker, int64_t finger_id) {
  if (!tracker) return 0;
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    if (tracker->fingers[i].finger_id == finger_id) {
      uint16_t released = tracker->fingers[i].bits;
      tracker->fingers[i].finger_id = -1;
      tracker->fingers[i].bits = 0;
      recompute(tracker);
      return released;
    }
  }
  return 0;
}

uint16_t X3Touch_Active(const X3TouchTracker *tracker) {
  return tracker ? tracker->held : 0;
}

int X3Touch_IsIdle(const X3TouchTracker *tracker) {
  return X3Touch_Active(tracker) == 0;
}
