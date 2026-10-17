"""The routing table SKILL.md shows is the one show_state.py holds, never a second copy.

    cd scripts && python3 -m unittest test_sync_routing_table -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sync_routing_table as srt  # noqa: E402


class RoutingTable(unittest.TestCase):
    def test_the_committed_block_is_current(self) -> None:
        self.assertEqual(srt.main(["--check"]), 0)

    def test_every_proposal_in_the_dict_is_rendered(self) -> None:
        ss = srt.load_show_state()
        block = srt.render()
        for proposal in [*ss.COMMON_NEXT.values(), *(v for t in ss.PHASE_NEXT_BY_STACK.values() for v in t.values())]:
            self.assertIn(proposal, block)

    def test_a_hand_edit_inside_the_block_is_caught(self) -> None:
        text = srt.SKILL.read_text()
        tampered = text.replace("THEN  rn-eas-deploy", "THEN  rn-eas-deploy right away", 1)
        self.assertNotEqual(tampered, text)
        self.assertNotEqual(srt.replace_block(tampered, srt.render()), tampered)


if __name__ == "__main__":
    unittest.main()
