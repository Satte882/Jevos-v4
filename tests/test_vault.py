import tempfile
import unittest
from pathlib import Path

from jevos_local.vault import iter_notes, vault_path


class VaultTests(unittest.TestCase):
    def test_only_visible_markdown_files_and_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("Do this task.", encoding="utf-8")
            (root / "b.md").write_text("Next idea.", encoding="utf-8")
            (root / "c.txt").write_text("Ignore.", encoding="utf-8")
            (root / ".obsidian").mkdir()
            (root / ".obsidian" / "secret.md").write_text("Ignore.", encoding="utf-8")
            self.assertEqual([x[0] for x in iter_notes(root, 1)], ["a.md"])
            self.assertEqual([x[0] for x in iter_notes(root, 20)], ["a.md", "b.md"])

    def test_skips_oversized_and_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("x" * 70000, encoding="utf-8")
            (root / "b.md").write_text(" ", encoding="utf-8")
            (root / "c.md").write_text("Idea", encoding="utf-8")
            self.assertEqual([p for p, _ in iter_notes(root)], ["c.md"])

    def test_invalid_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                vault_path(Path(temp) / "missing.md")


if __name__ == "__main__":
    unittest.main()
