"""Run the offline tests for every lab and guided project. No API key or network needed.

    uv run --with-requirements labs/test-requirements.txt python labs/run_tests.py

Each lab folder is tested as if it were your project folder: E5's research_bot.py and E6's
rag.py can be imported, as they can in your repo, and a module that another lab also has
(E7 to E10 each have their own agent.py) is cleared before that lab's tests load.
Each guided project in projects/ is tested the same way, from its own folder, and
projects/test_projects.py checks the starters built from them.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

import chromadb

LABS = Path(__file__).parent
PROJECTS = LABS.parent / "projects"
SHARED = [str(LABS / "e05"), str(LABS / "e06")]

suite = unittest.TestSuite()
with mock.patch.object(chromadb, "PersistentClient", lambda path: chromadb.EphemeralClient()):  # no chroma folders
    for folder in sorted(LABS.glob("e[0-9][0-9]")):
        for path in folder.glob("*.py"):
            sys.modules.pop(path.stem, None)
        sys.path[:0] = [str(folder)] + [p for p in SHARED if p != str(folder)]
        suite.addTests(unittest.defaultTestLoader.discover(str(folder), pattern="test_*.py", top_level_dir=str(folder)))
    for folder in sorted(PROJECTS.glob("p[0-9]-*/")):
        for path in [*folder.glob("*.py"), *folder.glob("tests/*.py")]:
            sys.modules.pop(path.stem, None)
        sys.path[:0] = [str(folder), str(folder / "tests")]
        suite.addTests(unittest.defaultTestLoader.discover(str(folder / "tests"), pattern="test_*.py"))
    suite.addTests(unittest.defaultTestLoader.discover(str(PROJECTS), pattern="test_projects.py"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
