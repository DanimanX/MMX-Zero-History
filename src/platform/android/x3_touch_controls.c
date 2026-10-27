/* Implementación de la capa táctil. Ver x3_touch_controls.h. */
#include "x3_touch_controls.h"

#include <string.h>

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
#define X3_SHOULDER_W 0.098f
#define X3_SHOULDER_H 0.070f
#define X3_SHOULDER_Y 0.578f
#define X3_START_W 0.108f
#define X3_START_H 0.062f
#define X3_START_Y 0.640f

static void put(X3TouchLayout *l, float x, float y, float w, float h, int bit) {
  if (l->count >= X3_TOUCH_MAX_BUTTONS) return;
  X3TouchButton *b = &l->buttons[l->count];
  l->authored_x[l->count] = x;
  ++l->count;
  b->x = x;
  b->y = y;
  b->w = w;
  b->h = h;
  b->bit = bit;
}

/* Square region centred on (cx, cy) with half-extent half. */
static void put_centred(X3TouchLayout *l, float cx, float cy, float half,
                        int bit) {
  put(l, cx - half, cy - half, half * 2.0f, half * 2.0f, bit);
}

void X3Touch_DefaultLayout(X3TouchLayout *layout) {
  if (!layout) return;
  memset(layout, 0, sizeof(*layout));
  layout->opacity = 55;

  /* D-pad: four discrete keys, not a virtual stick. X3 is a D-pad game and
   * an analogue stick mapped to four directions eats diagonal inputs. */
  put_centred(layout, X3_DPAD_CX, X3_DPAD_CY - X3_DPAD_ARM, X3_DPAD_HALF,
              X3_BIT_UP);
  put_centred(layout, X3_DPAD_CX, X3_DPAD_CY + X3_DPAD_ARM, X3_DPAD_HALF,
              X3_BIT_DOWN);
  put_centred(layout, X3_DPAD_CX - X3_DPAD_ARM, X3_DPAD_CY, X3_DPAD_HALF,
              X3_BIT_LEFT);
  put_centred(layout, X3_DPAD_CX + X3_DPAD_ARM, X3_DPAD_CY, X3_DPAD_HALF,
              X3_BIT_RIGHT);

  /* Face buttons in the SNES diamond: Y top, B right, A bottom, X left. */
  put_centred(layout, X3_FACE_CX, X3_FACE_CY - X3_FACE_OFF, X3_FACE_RAD,
              X3_BIT_Y);
  put_centred(layout, X3_FACE_CX + X3_FACE_OFF, X3_FACE_CY, X3_FACE_RAD,
              X3_BIT_B);
  put_centred(layout, X3_FACE_CX, X3_FACE_CY + X3_FACE_OFF, X3_FACE_RAD,
              X3_BIT_A);
  put_centred(layout, X3_FACE_CX - X3_FACE_OFF, X3_FACE_CY, X3_FACE_RAD,
              X3_BIT_X);

  /* Shoulders, above the diamond. */
  put(layout, X3_FACE_CX - X3_FACE_OFF - X3_SHOULDER_W * 0.5f,
      X3_SHOULDER_Y - X3_SHOULDER_H * 0.5f, X3_SHOULDER_W, X3_SHOULDER_H,
      X3_BIT_L);
  put(layout, X3_FACE_CX + X3_FACE_OFF - X3_SHOULDER_W * 0.5f,
      X3_SHOULDER_Y - X3_SHOULDER_H * 0.5f, X3_SHOULDER_W, X3_SHOULDER_H,
      X3_BIT_R);

  /* Start: centred, small, out of the play area. */
  put(layout, 0.5f - X3_START_W * 0.5f, X3_START_Y - X3_START_H * 0.5f,
      X3_START_W, X3_START_H, X3_BIT_START);

  /* Select: lower centre-left, rarely used but unavoidable in some menus. */
  put_centred(layout, 0.5f, 0.870f, 0.045f, X3_BIT_SELECT);
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
