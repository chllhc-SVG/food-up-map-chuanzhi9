"""Serve the offline map. Optional --catalog-import enables a single local import."""

import argparse
from datetime import date, datetime
from functools import partial
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import urlsplit
import webbrowser


ROOT = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 8794
APP_ID = "food-up-map"
ORIGIN = f"http://{HOST}:{PORT}"
DEST = ROOT / ".local" / "fuzhou-catalog.json"
MAX_BYTES = 4 * 1024 * 1024
STATIC = {
    "/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
    "/styles.css": "styles.css", "/note.js": "note.js", "/data/wuhan.json": "data/wuhan.json",
    "/data/fuzhou.json": "data/fuzhou.json",
}
for name in ("leaflet.js", "leaflet.css", "leaflet.js.map", "LICENSE", "SOURCE.txt",
             "images/marker-icon.png", "images/marker-icon-2x.png", "images/marker-shadow.png",
             "images/layers.png", "images/layers-2x.png"):
    STATIC["/vendor/leaflet/" + name] = "vendor/leaflet/" + name

CAPTURE = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>福州公开视频目录导入</title>
<style>body{font:16px/1.65 system-ui;max-width:48rem;margin:3rem auto;padding:0 1rem}
textarea{box-sizing:border-box;width:100%;min-height:17rem;padding:1rem}button{padding:.55rem 1.2rem}</style>
<h1>福州公开视频目录导入</h1><p>粘贴由 bvid、title、published 三个字段组成的 JSON 数组。
published 可用 ISO 日期、带时间的 ISO 日期或 Unix 秒数。请一次粘贴完整目录。</p>
<label for="rows">视频目录 JSON</label><textarea id="rows" spellcheck="false"></textarea>
<p><button id="save">保存目录</button></p><output id="result" aria-live="polite"></output>
<script>const save=document.querySelector('#save'),result=document.querySelector('#result');
save.onclick=async()=>{save.disabled=true;
try {const response=await fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},
body:document.querySelector('#rows').value});const data=await response.json();result.textContent=data.message;
save.disabled=response.ok||response.status===409;} catch(e){result.textContent='未保存，请检查本机服务。';save.disabled=false;}};</script></html>"""


def parse_catalog(payload):
    rows = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ValueError("目录必须为含 1 至 10000 项的 JSON 数组。")
    seen = set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict) or row.keys() != {"bvid", "title", "published"}:
            raise ValueError(f"第 {i} 行必须且只能包含 bvid、title、published。")
        code, title, published = row["bvid"], row["title"], row["published"]
        if not isinstance(code, str) or not re.fullmatch(r"BV[0-9A-Za-z]{10}", code) or code in seen:
            raise ValueError(f"第 {i} 行 BV 号无效或重复。")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 500 or any(ord(c) < 32 for c in title):
            raise ValueError(f"第 {i} 行标题无效。")
        row["title"] = title.strip()
        if type(published) is int:
            valid_date = 946684800 <= published <= 4102444800
        elif isinstance(published, str) and 10 <= len(published) <= 40:
            try:
                if len(published) == 10:
                    date.fromisoformat(published)
                else:
                    datetime.fromisoformat(published.replace("Z", "+00:00"))
                valid_date = True
            except ValueError:
                valid_date = False
        else:
            valid_date = False
        if not valid_date:
            raise ValueError(f"第 {i} 行发布时间无效。")
        seen.add(code)
    return rows


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, import_enabled, **kwargs):
        self.import_enabled = import_enabled
        super().__init__(*args, **kwargs)

    def respond(self, status, content, kind):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def message(self, status, text):
        self.respond(status, json.dumps({"message": text}, ensure_ascii=False).encode(),
                     "application/json; charset=utf-8")

    def local_host(self):
        return self.headers.get_all("Host", []) == [f"{HOST}:{PORT}"]

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.local_host():
            return self.message(403, "仅限本机地址。")
        path = urlsplit(self.path).path
        if path == "/health":
            return self.respond(200, json.dumps({"appId": APP_ID, "message": "ok"}).encode(),
                                "application/json; charset=utf-8")
        if path == "/capture" and self.import_enabled:
            return self.respond(200, CAPTURE.encode(), "text/html; charset=utf-8")
        if path not in STATIC:
            return self.message(404, "未找到。")
        target = ROOT / STATIC[path]
        if not target.is_file() or not target.resolve().is_relative_to(ROOT):
            return self.message(404, "未找到。")
        self.respond(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")

    def do_POST(self):
        if self.path != "/capture" or not self.import_enabled:
            return self.message(404, "未启用此入口。")
        if not self.local_host() or self.headers.get_all("Origin", []) != [ORIGIN]:
            return self.message(403, "来源不符。")
        if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
            return self.message(415, "请使用 application/json。")
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,8}", lengths[0]):
            return self.message(411, "需要有效的 Content-Length。")
        size = int(lengths[0])
        if not 1 <= size <= MAX_BYTES:
            return self.message(413, "目录为空或超过 4 MiB。")
        self.connection.settimeout(10)
        try:
            payload = self.rfile.read(size)
            if len(payload) != size:
                raise ValueError("目录未完整接收。")
            rows = parse_catalog(payload)
            content = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        except (UnicodeError, json.JSONDecodeError, RecursionError, TimeoutError):
            return self.message(400, "目录不是有效的 UTF-8 JSON 数组。")
        except ValueError as exc:
            return self.message(400, str(exc))
        try:
            with self.server.import_lock:
                if DEST.exists():
                    return self.message(409, "目录已保存。一次性导入不会覆盖已有文件。")
                DEST.parent.mkdir(exist_ok=True)
                if DEST.parent.resolve() != DEST.parent:
                    return self.message(409, "导入目录位置无效。")
                # Atomically expose the validated file after the write completes.
                with tempfile.NamedTemporaryFile(dir=DEST.parent, delete=False) as handle:
                    tmp = Path(handle.name)
                    try:
                        handle.write(content)
                    except BaseException:
                        handle.close()
                        tmp.unlink(missing_ok=True)
                        raise
                try:
                    os.link(tmp, DEST)
                finally:
                    tmp.unlink(missing_ok=True)
        except FileExistsError:
            return self.message(409, "目录已存在。")
        except OSError:
            return self.message(500, "无法保存本地目录。")
        self.message(201, f"已保存 {len(rows)} 条公开视频元数据。")


def our_server_is_running():
    http = HTTPConnection(HOST, PORT, timeout=2)
    try:
        http.request("GET", "/health")
        response = http.getresponse()
        return response.status == 200 and json.loads(response.read(512)).get("appId") == APP_ID
    except (OSError, HTTPException, ValueError, AttributeError):
        return False
    finally:
        http.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-import", action="store_true", help="enable one-time localhost catalog import")
    parser.add_argument("--open", action="store_true", help="open the map in your default browser")
    options = parser.parse_args()
    if options.open and not options.catalog_import and our_server_is_running():
        webbrowser.open(ORIGIN + "/")
        return
    try:
        server = ThreadingHTTPServer((HOST, PORT), partial(Handler, import_enabled=options.catalog_import))
    except OSError as exc:
        if options.open and not options.catalog_import and our_server_is_running():
            webbrowser.open(ORIGIN + "/")
            return
        raise SystemExit(f"Cannot start Food Up Map at {ORIGIN}: {exc}") from exc
    with server:
        server.import_lock = threading.Lock()
        print(ORIGIN + ("/capture" if options.catalog_import else "/"), flush=True)
        if options.open:
            # The server is already bound and listening before the browser gets the URL.
            threading.Thread(target=webbrowser.open, args=(ORIGIN + "/",), daemon=True).start()
        server.serve_forever()


if __name__ == "__main__":
    main()
