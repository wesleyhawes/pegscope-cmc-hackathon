"""Generate a self-contained judge demo from the same engine and UI as the live desk."""

import argparse
import json
from pathlib import Path

from pegscope import MODES, ROOT, report


def export_html():
    web = ROOT / "web"
    frames = {}
    for mode in MODES:
        size = report(None, mode)["steps"]
        frames[mode] = [report(None, mode, step) for step in range(1, size + 1)]
    data = json.dumps(frames, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    page = (web / "index.html").read_text(encoding="utf-8")
    css = (web / "style.css").read_text(encoding="utf-8")
    js = (web / "app.js").read_text(encoding="utf-8")
    style_tag = '<link rel="stylesheet" href="/style.css">'
    js_tag = '<script src="/app.js" defer></script>'
    if style_tag not in page or js_tag not in page:
        raise ValueError("The dashboard template changed. Update the export asset map.")
    page = page.replace(style_tag, f"<style>{css}</style>").replace(js_tag, "")
    content = f'<script type="application/json" id="replay-data">{data}</script>\n<script>{js}</script>'
    return page.replace("</body>", content + "\n</body>")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path, help="destination HTML file")
    args = cli.parse_args()
    args.output.write_text(export_html(), encoding="utf-8")
    print(args.output)
