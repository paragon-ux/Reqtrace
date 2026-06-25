from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ExampleStyleTests(unittest.TestCase):
    def test_refresh_token_sources_include_non_marker_comments(self) -> None:
        source_root = REPOSITORY_ROOT / "examples" / "refresh-token" / "src"
        paths = sorted(source_root.glob("*.js"))
        self.assertTrue(paths)
        for path in paths:
            lines = path.read_text(encoding="utf-8").splitlines()
            non_marker_comments = [
                line
                for line in lines
                if line.strip().startswith("//") and "@reqtrace" not in line
            ]
            self.assertTrue(non_marker_comments, f"{path.name} lacks a non-marker comment")


if __name__ == "__main__":
    unittest.main()
