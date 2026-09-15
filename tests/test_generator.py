import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from generator.pitch_builder import generate_pitch

class TestGenerator(unittest.TestCase):
    def test_generate_pitch_import(self):
        # We just verify it's importable for now.
        self.assertTrue(callable(generate_pitch))

if __name__ == "__main__":
    unittest.main()
