"""Milestone 1: split code into chunks"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: no test calls Claude
sys.path.insert(0, str(Path(__file__).parent.parent))
import qa  # noqa: E402
from fakes import TINYSHOP, repo  # noqa: E402

HINT = ("Walk ast.parse(source).body: FunctionDef nodes become chunks from node.lineno (or the first decorator's line) "
        "to node.end_lineno; for a ClassDef, one chunk for the lines before its first method and one per method, named "
        "Class.method. Collect the lines no chunk covered, and turn each run of them into a (module) chunk.")


def refs(chunks, path):
    return [(c.start, c.end, c.name) for c in chunks if c.path == path]


class ChunkPythonTest(unittest.TestCase):
    def setUp(self):
        self.chunks = qa.chunk_repo(TINYSHOP)

    def test_one_chunk_per_function_with_exact_lines(self):
        self.assertEqual(refs(self.chunks, "tinyshop/auth.py"), [
            (1, 10, "(module)"), (13, 17, "hash_password"), (20, 24, "verify_password"), (27, 39, "login"),
            (42, 46, "create_session"), (49, 55, "current_user_id")])

    def test_classes_split_into_a_header_and_methods(self):
        names = [name for _, _, name in refs(self.chunks, "tinyshop/cart.py")]
        self.assertEqual(names, ["(module)", "Cart", "Cart.__init__", "Cart.add", "Cart.remove", "Cart.subtotal_cents",
                                 "Cart.weight_grams", "Cart.apply_coupon", "Cart.discount_cents"])
        self.assertEqual(refs(self.chunks, "tinyshop/cart.py")[1], (6, 9, "Cart"))

    def test_decorators_belong_to_their_function(self):
        charge = next(c for c in self.chunks if c.name == "charge")
        self.assertEqual((charge.start, charge.end), (12, 25))
        self.assertTrue(charge.text.startswith("@retry(times=3"))

    def test_module_code_between_functions_is_kept(self):
        self.assertEqual(refs(self.chunks, "tinyshop/routes.py")[-1], (43, 47, "(module)"))
        self.assertIn("ROUTES = {", self.chunks[[c.ref for c in self.chunks].index("tinyshop/routes.py:43-47")].text)

    def test_the_text_is_exactly_those_lines(self):
        lines = (TINYSHOP / "tinyshop/tax.py").read_text().splitlines()
        tax = next(c for c in self.chunks if c.name == "tax_for")
        self.assertEqual(tax.text, "\n".join(lines[tax.start - 1:tax.end]))
        self.assertEqual(tax.ref, "tinyshop/tax.py:7-11")

    def test_a_small_example(self):
        source = 'import os\n\nLIMIT = 3\n\n\n@decorate\ndef f():\n    return 1\n\n\nclass A:\n    """Doc."""\n\n    def g(self):\n        pass\n\nprint("done")\n'
        got = [(c.name, c.start, c.end) for c in qa.chunk_python("x.py", source)]
        self.assertEqual(got, [("(module)", 1, 3), ("f", 6, 8), ("A", 11, 12), ("A.g", 14, 15), ("(module)", 17, 17)])


class ChunkRepoTest(unittest.TestCase):
    def test_every_file_is_covered_and_paths_use_slashes(self):
        chunks = qa.chunk_repo(TINYSHOP)
        self.assertEqual(len(chunks), 56)
        self.assertEqual(sorted({c.path for c in chunks})[:3], ["README.md", "tinyshop/__init__.py", "tinyshop/auth.py"])
        self.assertIn("tinyshop/utils/retry.py", {c.path for c in chunks})

    def test_hidden_files_and_secrets_are_skipped(self):
        paths = {c.path for c in qa.chunk_repo(repo())}
        self.assertFalse({p for p in paths if p.startswith(".") or "/." in p}, paths)
        self.assertNotIn("deploy_key.pem", paths)

    def test_generated_folders_are_skipped_and_bad_code_still_indexed(self):
        root = Path(tempfile.mkdtemp())
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "x.py").write_text("def cached(): pass\n")
        (root / "broken.py").write_text("def broken(:\n    pass\n")
        chunks = qa.chunk_repo(root)
        self.assertEqual([(c.path, c.name, c.start, c.end) for c in chunks], [("broken.py", "(file)", 1, 2)])


if __name__ == "__main__":
    unittest.main()
