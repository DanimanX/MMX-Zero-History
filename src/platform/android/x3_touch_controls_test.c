/* Tests for the touch layer's geometry and multi-touch bookkeeping.
 *
 * These run on the desktop: the module is pure input logic with no SDL and no
 * guest state, so the parts that actually break (overlapping hit boxes,
 * duplicate fingers, latched inputs) are testable without a phone.
 *
 *   bash tools/test_touch_controls.sh
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "x3_touch_controls.h"

static int failures;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);                   \
      ++failures;                                                              \
    }                                                                          \
  } while (0)

static const X3TouchButton *find_button(const X3TouchLayout *l, int bit) {
  for (int i = 0; i < l->count; ++i) {
    if (l->buttons[i].bit == bit) return &l->buttons[i];
  }
  return NULL;
}

static void tap_centre(X3TouchTracker *t, int64_t id, const X3TouchLayout *l,
                       int bit) {
  const X3TouchButton *b = find_button(l, bit);
  assert(b);
  float nx = b->x + b->w * 0.5f;
  float ny = b->y + b->h * 0.5f;
  uint16_t got = X3Touch_Down(t, id, l, nx, ny);
  CHECK(got == (uint16_t)(1u << bit));
}

static void test_unique_bits(void) {
  X3TouchLayout l;
  X3Touch_DefaultLayout(&l);
  CHECK(l.count == X3_BIT_COUNT);
  int seen[X3_BIT_COUNT];
  memset(seen, 0, sizeof(seen));
  for (int i = 0; i < l.count; ++i) {
    int b = l.buttons[i].bit;
    CHECK(b >= 0 && b < X3_BIT_COUNT);
    CHECK(!seen[b]);
    seen[b] = 1;
  }
  for (int b = 0; b < X3_BIT_COUNT; ++b) CHECK(seen[b]);
}

static void test_centres_are_unambiguous(void) {
  X3TouchLayout l;
  X3Touch_DefaultLayout(&l);
  for (int i = 0; i < l.count; ++i) {
    const X3TouchButton *b = &l.buttons[i];
    float cx = b->x + b->w * 0.5f;
    float cy = b->y + b->h * 0.5f;
    uint16_t got = X3Touch_HitTest(&l, cx, cy);
    if (got != (uint16_t)(1u << b->bit)) {
      printf("  button %d (bit %d) centre hits 0x%03X\n", i, b->bit, got);
    }
    CHECK(got == (uint16_t)(1u << b->bit));
  }
}

static void test_empty_regions(void) {
  X3TouchLayout l;
  X3Touch_DefaultLayout(&l);
  CHECK(X3Touch_HitTest(&l, 0.50f, 0.05f) == 0); /* sky */
  CHECK(X3Touch_HitTest(&l, 0.50f, 0.35f) == 0); /* mid play area */
  CHECK(X3Touch_HitTest(&l, 0.02f, 0.02f) == 0); /* top-left corner */
}

static void test_diagonals_read_as_two_keys(void) {
  X3TouchLayout l;
  X3Touch_DefaultLayout(&l);
  const X3TouchButton *up = find_button(&l, X3_BIT_UP);
  const X3TouchButton *left = find_button(&l, X3_BIT_LEFT);
  assert(up && left);
  /* Land in the gap between the up key and the left key. */
  float nx = (up->x + left->x + left->w) * 0.5f;
  float ny = (up->y + up->h + left->y) * 0.5f;
  uint16_t got = X3Touch_HitTest(&l, nx, ny);
  CHECK((got & (1u << X3_BIT_UP)) != 0);
  CHECK((got & (1u << X3_BIT_LEFT)) != 0);
}

static void test_all_buttons_inside_screen(void) {
  X3TouchLayout l;
  X3Touch_DefaultLayout(&l);
  for (int i = 0; i < l.count; ++i) {
    const X3TouchButton *b = &l.buttons[i];
    CHECK(b->x >= 0.0f);
    CHECK(b->y >= 0.0f);
    CHECK(b->x + b->w <= 1.0f);
    CHECK(b->y + b->h <= 1.0f);
    CHECK(b->w > 0.02f);
    CHECK(b->h > 0.02f);
  }
}

static void test_mirror_is_a_toggle(void) {
  X3TouchLayout a, b;
  X3Touch_DefaultLayout(&a);
  memcpy(&b, &a, sizeof(a));

  X3Touch_SetMirrored(&b, 1);
  CHECK(b.mirrored == 1);
  const X3TouchButton *up_a = find_button(&a, X3_BIT_UP);
  const X3TouchButton *up_b = find_button(&b, X3_BIT_UP);
  assert(up_a && up_b);
  CHECK(up_b->x > up_a->x);           /* d-pad crossed to the right */
  const X3TouchButton *a_a = find_button(&a, X3_BIT_A);
  const X3TouchButton *a_b = find_button(&b, X3_BIT_A);
  CHECK(a_b->x < a_a->x);             /* face diamond crossed to the left */

  X3Touch_SetMirrored(&b, 0);
  CHECK(b.mirrored == 0);
  for (int i = 0; i < a.count; ++i) {
    CHECK(a.buttons[i].x == b.buttons[i].x);
    CHECK(a.buttons[i].y == b.buttons[i].y);
  }

  /* Calling it again with the same value must not drift. */
  for (int pass = 0; pass < 5; ++pass) {
    X3Touch_SetMirrored(&b, 1);
    X3Touch_SetMirrored(&b, 0);
  }
  for (int i = 0; i < a.count; ++i) CHECK(a.buttons[i].x == b.buttons[i].x);
}

static void test_mirrored_hits_still_work(void) {
  X3TouchLayout l;
  X3Touch_DefaultLayout(&l);
  X3Touch_SetMirrored(&l, 1);
  for (int i = 0; i < l.count; ++i) {
    const X3TouchButton *b = &l.buttons[i];
    uint16_t got = X3Touch_HitTest(&l, b->x + b->w * 0.5f,
                                   b->y + b->h * 0.5f);
    CHECK(got == (uint16_t)(1u << b->bit));
  }
}

static void test_two_fingers_hold_two_directions(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  CHECK(X3Touch_IsIdle(&t));

  tap_centre(&t, 1, &l, X3_BIT_RIGHT);
  tap_centre(&t, 2, &l, X3_BIT_A); /* jump while running */
  CHECK(X3Touch_Active(&t) ==
        (uint16_t)((1u << X3_BIT_RIGHT) | (1u << X3_BIT_A)));

  CHECK(X3Touch_Up(&t, 1) == (uint16_t)(1u << X3_BIT_RIGHT));
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_A));
  CHECK(X3Touch_Up(&t, 2) == (uint16_t)(1u << X3_BIT_A));
  CHECK(X3Touch_IsIdle(&t));
}

static void test_two_fingers_on_one_button(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  tap_centre(&t, 10, &l, X3_BIT_B);
  tap_centre(&t, 11, &l, X3_BIT_B);
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_B));
  /* Lifting one finger must not release the button the other still holds. */
  X3Touch_Up(&t, 10);
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_B));
  X3Touch_Up(&t, 11);
  CHECK(X3Touch_IsIdle(&t));
}

static void test_input_latches_until_lift(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  tap_centre(&t, 7, &l, X3_BIT_LEFT);
  /* A thumb sliding off the key is still a held input: platformers break
   * when a drifting thumb drops the direction mid-jump. */
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_LEFT));
  CHECK(X3Touch_Up(&t, 7) == (uint16_t)(1u << X3_BIT_LEFT));
}

static void test_duplicate_and_unknown_fingers(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  tap_centre(&t, 3, &l, X3_BIT_Y);
  CHECK(X3Touch_Down(&t, 3, &l, 0.5f, 0.5f) == 0); /* duplicate id */
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_Y));
  CHECK(X3Touch_Up(&t, 999) == 0); /* unknown id */
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_Y));
}

static void test_empty_press_is_ignored(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  CHECK(X3Touch_Down(&t, 1, &l, 0.5f, 0.06f) == 0);
  CHECK(X3Touch_IsIdle(&t));
  /* An empty press must not consume a slot: the full finger table stays
   * available for real presses. */
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    tap_centre(&t, 100 + i, &l, X3_BIT_START);
  }
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_START));
}

static void test_finger_table_saturates(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    tap_centre(&t, 200 + i, &l, X3_BIT_R);
  }
  /* The 11th finger is dropped rather than corrupting tracked state. */
  CHECK(X3Touch_Down(&t, 999, &l, 0.845f, 0.675f) == 0);
  CHECK(X3Touch_Active(&t) == (uint16_t)(1u << X3_BIT_R));
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) X3Touch_Up(&t, 200 + i);
  CHECK(X3Touch_IsIdle(&t));
}

static void test_mask_never_leaves_12_bits(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  /* One finger per distinct button, up to the finger table's capacity. */
  int pressed = 0;
  for (int i = 0; i < l.count && i < X3_TOUCH_MAX_FINGERS; ++i) {
    const X3TouchButton *b = &l.buttons[i];
    if (X3Touch_Down(&t, 300 + i, &l, b->x + b->w * 0.5f,
                     b->y + b->h * 0.5f)) {
      ++pressed;
    }
  }
  CHECK(pressed == X3_TOUCH_MAX_FINGERS);
  CHECK((X3Touch_Active(&t) & ~(uint16_t)X3_PAD_MASK_ALL) == 0);
  int bits = 0;
  for (int b = 0; b < X3_BIT_COUNT; ++b) {
    if (X3Touch_Active(&t) & (1u << b)) ++bits;
  }
  CHECK(bits == pressed);
}

static void test_reset_clears_everything(void) {
  X3TouchLayout l;
  X3TouchTracker t;
  X3Touch_DefaultLayout(&l);
  X3Touch_Reset(&t);
  tap_centre(&t, 1, &l, X3_BIT_A);
  tap_centre(&t, 2, &l, X3_BIT_UP);
  X3Touch_Reset(&t);
  CHECK(X3Touch_IsIdle(&t));
  for (int i = 0; i < X3_TOUCH_MAX_FINGERS; ++i) {
    CHECK(t.fingers[i].finger_id == -1);
    CHECK(t.fingers[i].bits == 0);
  }
}

int main(void) {
  test_unique_bits();
  test_centres_are_unambiguous();
  test_empty_regions();
  test_diagonals_read_as_two_keys();
  test_all_buttons_inside_screen();
  test_mirror_is_a_toggle();
  test_mirrored_hits_still_work();
  test_two_fingers_hold_two_directions();
  test_two_fingers_on_one_button();
  test_input_latches_until_lift();
  test_duplicate_and_unknown_fingers();
  test_empty_press_is_ignored();
  test_finger_table_saturates();
  test_mask_never_leaves_12_bits();
  test_reset_clears_everything();

  if (failures) {
    printf("\n%d check(s) failed\n", failures);
    return 1;
  }
  printf("touch controls: all checks passed\n");
  return 0;
}
