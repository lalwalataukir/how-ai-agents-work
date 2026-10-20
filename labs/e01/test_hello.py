"""Offline test for hello.py: run it and check what it prints."""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent


class HelloTest(unittest.TestCase):
    def test_prints_greeting_and_python_version(self):
        out = subprocess.run([sys.executable, str(HERE / "hello.py")], capture_output=True, text=True, check=True).stdout
        lines = out.splitlines()
        self.assertEqual(lines[0], "Hello from the research assistant!")
        self.assertRegex(lines[1], r"^Python 3\.\d+\.\d+ on \w+")


if __name__ == "__main__":
    unittest.main()
