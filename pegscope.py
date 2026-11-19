"""PegScope operator CLI and loopback dashboard server. Python 3.10+."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from urllib.parse import parse_qs, urlsplit

from cmc_client import ApiError, quote_sample
from peg_engine import analyze, scenario

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / ".local" / "captures.sqlite3"
MODES = ("drift", "recovery", "stale", "quiet")
STATIC = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
          "/style.css": ("style.css", "text/css"), "/app.js": ("app.js", "text/javascript")}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def add_capture(db, frame, evidence):
    db.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with closing(sqlite3.connect(db, timeout=8)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS captures
            (seq INTEGER PRIMARY KEY, captured TEXT NOT NULL, source TEXT NOT NULL,
             frame TEXT NOT NULL, evidence TEXT NOT NULL, UNIQUE(source,captured))""")
        conn.execute("INSERT OR IGNORE INTO captures(captured,source,frame,evidence) VALUES(?,?,?,?)",
                     (frame["at"], evidence["source"], json.dumps(frame), json.dumps(evidence)))


def live_history(db):
    if not db.is_file():
        raise LookupError("No CMC captures yet. Run python3 pegscope.py sample, then refresh.")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=8)) as conn, conn:
        conn.execute("BEGIN")
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='captures' AND type='table'").fetchone():
            raise LookupError("No CMC captures yet. Run the sample command.")
        row = conn.execute("SELECT source,evidence FROM captures ORDER BY captured DESC,seq DESC LIMIT 1").fetchone()
        if not row:
            raise LookupError("No CMC captures yet. Run the sample command.")
        source, proof = row
        # Replay this source's entire state history. Only recent plot points go to the browser.
        frames = [json.loads(f) for (f,) in conn.execute(
            "SELECT frame FROM captures WHERE source=? ORDER BY captured,seq", (source,))]
    return frames, json.loads(proof)


def report(db, mode, step=None, current=now):
    if mode != "live" and mode not in MODES:
        raise ValueError("Choose drift, recovery, stale, quiet, or live.")
    if mode == "live":
        if step is not None:
            raise ValueError("Step applies to synthetic replays only.")
        frames, evidence = live_history(db)
        steps = len(frames)
        as_of = current()
        if as_of > frames[-1]["at"]:
            # Same provider timestamp cannot confirm a breach. It can become stale with the clock.
            frames.append({"at": as_of, "quotes": frames[-1]["quotes"]})
        source = evidence["source"]
        step = steps
    else:
        evidence = None
        frames = scenario(mode)
        steps = len(frames)
        step = steps if step is None else step
        if not 1 <= step <= steps:
            raise ValueError(f"Step must be between 1 and {steps}.")
        frames = frames[:step]
        source = "Synthetic scenario • illustrative prices"
    result = analyze(frames)
    for asset in result["assets"]:
        asset["series"] = asset["series"][-120:]
    return dict(result, mode=mode, source=source, step=step, steps=steps, evidence=evidence)


def handler_for(db):
    class Handler(BaseHTTPRequestHandler):
        def send_content(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def reply(self, status, obj):
            self.send_content(status, json.dumps(obj, allow_nan=False).encode(), "application/json")

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path in STATIC:
                name, mime = STATIC[path.path]
                self.send_content(200, (ROOT / "web" / name).read_bytes(), mime)
            elif path.path == "/api/report":
                query = parse_qs(path.query, keep_blank_values=True)
                try:
                    mode = query.get("mode", ["drift"])[0]
                    step = int(query["step"][0]) if "step" in query else None
                    self.reply(200, report(db, mode, step))
                except ValueError as error:
                    self.reply(400, {"error": str(error)})
                except LookupError as error:
                    self.reply(409, {"error": str(error)})
                except sqlite3.Error:
                    self.reply(503, {"error": "Capture store unavailable. Check the local database."})
            else:
                self.reply(404, {"error": "Unknown resource."})

    return Handler


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--db", type=Path, default=Path(os.getenv("PEGSCOPE_DB", DEFAULT_DB)))
    commands = cli.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="open the dashboard on localhost")
    serve.add_argument("--port", type=int, default=8765)
    sample = commands.add_parser("sample", help="capture quote frames using the CMC API")
    sample.add_argument("--keyless", action="store_true", help="use the explicitly labeled public API")
    sample.add_argument("--proof", action="store_true", help="print a minimal real request/response excerpt")
    sample.add_argument("--count", type=int, default=1, help="number of captures, 1 to 120")
    sample.add_argument("--interval", type=int, default=60, help="seconds between captures, minimum 60")
    args = cli.parse_args()
    db = args.db.expanduser().resolve()
    if args.command == "serve":
        if not 1 <= args.port <= 65535:
            cli.error("port must be between 1 and 65535")
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(db)) as server:
            print(f"PegScope dashboard  http://127.0.0.1:{args.port}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                return 0
    if not 1 <= args.count <= 120 or args.interval < 60:
        cli.error("count must be 1–120 and interval must be at least 60 seconds")
    try:
        for i in range(args.count):
            if i:
                time.sleep(args.interval)
            frame, evidence, receipt = quote_sample(now, public=args.keyless)
            add_capture(db, frame, evidence)
            if args.proof:
                print(json.dumps(receipt, indent=2), flush=True)
            else:
                print(f"{frame['at']}  {evidence['source']}  {len(frame['quotes'])}/3 USD records", flush=True)
    except ApiError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error):
        print("Capture could not be saved. Check the local database and disk.", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
