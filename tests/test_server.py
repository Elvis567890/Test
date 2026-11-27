import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
)

from app import make_arrangement

class ArrangementTests(unittest.TestCase):
    def test_arrangement_has_events(self):
        result = make_arrangement({
            "style": "Gospel",
            "key": "C",
            "chord": "C",
            "bpm": 90
        })
        self.assertEqual(result["type"], "arrangement")
        self.assertGreater(len(result["events"]), 0)

    def test_bpm_is_limited(self):
        result = make_arrangement({"bpm": 500})
        self.assertEqual(result["bpm"], 180)

    def test_unknown_key_uses_c(self):
        result = make_arrangement({"key": "UNKNOWN"})
        self.assertEqual(result["key"], "C")

if __name__ == "__main__":
    unittest.main()
