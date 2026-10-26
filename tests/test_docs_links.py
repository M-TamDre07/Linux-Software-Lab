from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_docs_links import check_all, check_markdown_file


ROOT = Path(__file__).resolve().parents[1]


class DocumentationLinkTests(unittest.TestCase):
    def test_repository_markdown_has_no_broken_or_escaping_local_links(self) -> None:
        errors = check_all(ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_finds_missing_relative_file_and_reports_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root / "docs" / "guide.md"
            page.parent.mkdir()
            page.write_text(
                "# Guide\n\nSee [missing page](../not-here.md).\n",
                encoding="utf-8",
            )
            errors = check_markdown_file(page, root=root)
        self.assertEqual(len(errors), 1)
        self.assertIn("guide.md:3", errors[0])
        self.assertIn("missing local target", errors[0])

    def test_ignores_external_links_heading_anchors_and_code_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root / "README.md"
            page.write_text(
                "[External](https://example.com) [Anchor](#section)\n"
                "`[not a link](missing-inline.md)`\n"
                "```md\n[not a link](missing-fenced.md)\n```\n"
                "~~~md\n[not a link](missing-tilde-fenced.md)\n~~~\n"
                "[Exists](child.md)\n",
                encoding="utf-8",
            )
            (root / "child.md").write_text("# Child\n", encoding="utf-8")
            errors = check_markdown_file(page, root=root)
        self.assertEqual(errors, [])

    def test_rejects_unsafe_link_schemes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root / "README.md"
            page.write_text("[Unsafe](javascript:alert(1))\n", encoding="utf-8")
            errors = check_markdown_file(page, root=root)
        self.assertEqual(len(errors), 1)
        self.assertIn("unsafe link scheme", errors[0])

    def test_rejects_links_that_escape_the_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            page = root / "README.md"
            page.write_text("[Escape](../secret.md)\n", encoding="utf-8")
            errors = check_markdown_file(page, root=root)
        self.assertEqual(len(errors), 1)
        self.assertIn("escapes the repository", errors[0])


if __name__ == "__main__":
    unittest.main()
