"""Run the offline tests for every lab. No API key or network needed.

    uv run --with httpx python labs/run_tests.py
"""
import sys
import unittest
from pathlib import Path

suite = unittest.TestSuite()
for folder in sorted(Path(__file__).parent.glob("e[0-9][0-9]")):
    suite.addTests(unittest.defaultTestLoader.discover(str(folder), pattern="test_*.py", top_level_dir=str(folder)))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
