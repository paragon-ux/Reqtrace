from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ExampleStyleTests(unittest.TestCase):
    def test_readme_declares_marker_semantics(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("evidence annotations, not explanatory comments", readme)
        self.assertIn("does not dogfood production source by default", readme)
        self.assertNotIn("self-tracing markers in `scripts/reqtrace.py`", readme)

    def test_agents_declares_comment_preservation_rule(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("preserve existing explanatory comments", agents)
        self.assertIn("edge cases, tradeoffs, or security assumptions", agents)
        self.assertNotIn("`@reqtrace` comment", agents)

    def test_annotation_skill_does_not_call_markers_comments(self) -> None:
        skill = (REPOSITORY_ROOT / "skills" / "reqtrace-annotation" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for line in skill.splitlines():
            if "@reqtrace" in line:
                self.assertNotIn("comment", line.lower(), line)
        self.assertIn("Do not treat the marker as a substitute", skill)

    def test_calibration_readme_declares_fixture_scope(self) -> None:
        readme = (REPOSITORY_ROOT / "examples" / "calibration" / "README.md")
        self.assertTrue(readme.exists())
        content = readme.read_text(encoding="utf-8")
        self.assertIn("not production annotation style guides", content)
        self.assertIn("01-full-coverage", content)

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

    def test_reqtrace_production_source_has_no_artificial_trd_markers(self) -> None:
        source = (REPOSITORY_ROOT / "scripts" / "reqtrace.py").read_text(encoding="utf-8")
        marker_prefix = "# @req" + "trace TRD-"
        production_markers = [
            line
            for line in source.splitlines()
            if line.strip().startswith(marker_prefix)
        ]
        self.assertEqual(production_markers, [])


if __name__ == "__main__":
    unittest.main()
