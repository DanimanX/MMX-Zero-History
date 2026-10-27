#!/usr/bin/env python3
"""Contract tests for tools/capsule_shuffle.py.

Run directly (no pytest needed):

    python3 tools/test_capsule_shuffle.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capsule_shuffle as cs  # noqa: E402


class LayoutContract(unittest.TestCase):
    def test_bijection_over_many_seeds(self) -> None:
        for seed in range(2048):
            placements = cs.layout(seed)
            self.assertEqual(len(placements), len(cs.STAGES))
            self.assertEqual({p.stage_id for p in placements},
                             {s for s, _ in cs.STAGES})
            self.assertEqual({p.item_id for p in placements},
                             {i[0] for i in cs.ITEMS})
            for p in placements:
                self.assertIn(p.alcove, range(cs.ALCOVES_PER_STAGE))

    def test_determinism(self) -> None:
        a = cs.layout(0xDEADBEEF)
        b = cs.layout(0xDEADBEEF)
        self.assertEqual(a, b)

    def test_seeds_differ(self) -> None:
        layouts = {tuple((p.stage_id, p.item_id) for p in cs.layout(s))
                   for s in range(64)}
        # 64 seeds colliding into one layout would mean the shuffle is broken.
        self.assertGreater(len(layouts), 60)

    def test_speedrun_is_pinned(self) -> None:
        self.assertEqual(cs.seed_for("speedrun"), cs.SPEEDRUN_SEED)
        self.assertEqual(cs.seed_for("speedrun", seed=0), cs.SPEEDRUN_SEED)
        with self.assertRaises(ValueError):
            cs.seed_for("speedrun", seed=7)

    def test_historia_derivation_is_stable_and_slot_sensitive(self) -> None:
        s0 = cs.seed_for("historia", profile="danimanx", slot=0, run=0)
        self.assertEqual(s0, cs.seed_for("historia", profile="danimanx",
                                         slot=0, run=0))
        self.assertNotEqual(s0, cs.seed_for("historia", profile="danimanx",
                                            slot=1, run=0))

    def test_unknown_mode_rejected(self) -> None:
        with self.assertRaises(ValueError):
            cs.seed_for("turbo")

    def test_validate_rejects_duplicate_item(self) -> None:
        placements = cs.layout(1)
        broken = list(placements)
        broken[1] = cs.Placement(
            stage_id=broken[1].stage_id, stage=broken[1].stage,
            alcove=broken[1].alcove, item_id=broken[0].item_id,
            item=broken[0].item, effect=broken[0].effect)
        with self.assertRaises(ValueError):
            cs.validate(broken)


if __name__ == "__main__":
    unittest.main(verbosity=2)
