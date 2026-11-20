"""Tests for the standalone, offline judge-demo exporter."""

import json
import re
import unittest
from unittest.mock import patch

import export_demo
from pegscope import MODES


class ExportDemoTests(unittest.TestCase):
    def test_export_embeds_all_replays_and_assets(self):
        html = export_demo.export_html()

        self.assertIn("<style>", html)
        self.assertIn("<script>", html)
        self.assertNotIn('<link rel="stylesheet" href="/style.css">', html)
        self.assertNotIn('<script src="/app.js" defer></script>', html)
        match = re.search(
            r'<script type="application/json" id="replay-data">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(set(data), set(MODES))
        self.assertTrue(all(data[mode] for mode in MODES))

    def test_export_escapes_script_openers_in_serialized_data(self):
        def fake_report(_db, mode, step=None):
            return {"mode": mode, "steps": 1, "step": step or 1,
                    "untrusted": "</script><script>alert(1)</script>"}

        with patch.object(export_demo, "report", side_effect=fake_report):
            html = export_demo.export_html()

        match = re.search(
            r'<script type="application/json" id="replay-data">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertIn(r"\u003c/script>", match.group(1))
        self.assertNotIn("</script><script>alert(1)", match.group(1))

    def test_export_rejects_template_asset_map_drift(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            web = Path(directory) / "web"
            web.mkdir()
            (web / "index.html").write_text("<html></html>", encoding="utf-8")
            (web / "style.css").write_text("", encoding="utf-8")
            (web / "app.js").write_text("", encoding="utf-8")
            with patch.object(export_demo, "ROOT", Path(directory)):
                with self.assertRaisesRegex(ValueError, "template changed"):
                    export_demo.export_html()


if __name__ == "__main__":
    unittest.main()
