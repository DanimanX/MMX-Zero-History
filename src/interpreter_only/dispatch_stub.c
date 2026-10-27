/* Empty AOT dispatch for a ROM-free, LLE-only build (MMX_LLE_ONLY=ON).
 *
 * The runner links against g_dispatch_table / g_ram_routine_guards, which the
 * recompiler normally emits from ROM-derived input. A build that must not
 * contain ROM-derived code therefore provides them here with no entries. The
 * boot path stays the normal one: SnesInit() loads the player's ROM, and the
 * interpreter tier runs every guest instruction because no dispatch lookup
 * ever hits an AOT body.
 *
 * This is the bring-up shape described in src/gen_stubs.c ("X3 boots
 * LLE-first: absent AOT coverage runs the real ROM bytes on the interpreter
 * tier"). It is not SNESRECOMP_SETUP_HOST: that build deliberately refuses to
 * boot and only runs the Generate & rebuild wizard. This one plays.
 *
 * Both tables mirror what program_emit.py produces for an empty game: the
 * dispatch table reports zero rows, and the guard table carries the sentinel
 * row the emitter writes when a cfg declares no ram_routine.
 */

#include "cpu_state.h"

/* Zero known function boundaries: the binary search in cpu_dispatch_pc()
 * runs over [0, 0) and reports a miss. One sentinel row keeps the array
 * non-empty, which C requires. */
const DispatchEntry g_dispatch_table[] = {
    {0xFFFFFFFFu, {NULL, NULL, NULL, NULL}, 0},
};
const unsigned g_dispatch_table_count = 0u;

const RamRoutineGuard g_ram_routine_guards[] = {
    {0xFFFFFFFFu, 0u, 0u},
};
const unsigned g_ram_routine_guard_count =
    (unsigned)(sizeof(g_ram_routine_guards) / sizeof(g_ram_routine_guards[0]));
