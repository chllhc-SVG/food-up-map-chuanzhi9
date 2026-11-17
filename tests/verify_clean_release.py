"""Verify the software from an isolated ZIP or a fresh git archive. See docs/复现验收.md."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
from time import perf_counter
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check_edge(origin, city_counts):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as toolkit:
        browser = toolkit.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(locale="zh-CN", service_workers="block")
            external = []
            errors = []

            def restrict_to_test_server(route):
                url = route.request.url
                if urlsplit(url).netloc == urlsplit(origin).netloc:
                    route.continue_()
                else:
                    external.append(urlsplit(url).netloc)
                    route.abort()

            context.route("**/*", restrict_to_test_server)
            page = context.new_page()
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.goto(origin, wait_until="domcontentloaded")
            expect(page.locator(".city-buttons strong")).to_have_text(["福州", "武汉"])
            for city, key, shop in (("福州", "fuzhou", "裕莲茶楼"), ("武汉", "wuhan", "三怪牛肉炒饭")):
                button = page.get_by_role("button", name=city, exact=True)
                if key == "wuhan":
                    button.click()
                    page.reload()
                expect(button).to_have_attribute("aria-pressed", "true")
                expect(page.locator("#videocount")).to_have_text(f"{city_counts[key]} 条视频")
                if key == "fuzhou":
                    page.locator("#origin").select_option(label="米丝林 · 店铺点位")
                    expect(page.locator("#location")).to_contain_text("已切换为「距出发点最近」")
                    expect(page.locator("#sort")).to_have_value("near")
                    page.locator("#sort").select_option("personal")
                    expect(page.locator("#location")).not_to_contain_text("已切换")
                page.locator("#search").fill(shop)
                page.locator("#places .place").filter(has=page.get_by_text(shop, exact=True)).first.click()
                expect(page.locator("#detail")).to_contain_text(shop)
                source = page.locator('#detail a[href*="www.bilibili.com/video/BV"]').first
                expect(source).to_be_visible()
            if external or errors:
                raise AssertionError({"external_requests": external, "page_errors": errors})
            return {"version": browser.version, "external_requests": external, "page_errors": errors}
        finally:
            browser.close()


def verify(work, args):
    started = perf_counter()
    if args.zip:
        source_zip = args.zip.resolve(strict=True)
        source = source_zip.name
    else:
        source_zip = work / "source.zip"
        source = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"{args.ref}^{{commit}}"], cwd=ROOT, text=True
        ).strip()
        subprocess.run(["git", "archive", "--format=zip", "-o", str(source_zip), source], cwd=ROOT, check=True)
    fresh = work / "extracted"
    fresh.mkdir()
    with zipfile.ZipFile(source_zip) as archive:
        for name in archive.namelist():
            if not (fresh / name).resolve().is_relative_to(fresh):
                raise ValueError(f"Unsafe archive member: {name}")
        archive.extractall(fresh)
    if (fresh / ".git").exists() or (fresh / ".local").exists():
        raise ValueError("The release must run without local development state.")
    extracted = perf_counter()
    spec = importlib.util.spec_from_file_location("isolated_map_server", fresh / "server.py")
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    if server.ROOT != fresh:
        raise ValueError("The test service is not using the extracted project.")

    response = build_opener(ProxyHandler({})).open
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(server.Handler, import_enabled=False)) as httpd:
        server.PORT = httpd.server_port
        origin = server.ORIGIN = f"http://127.0.0.1:{server.PORT}"
        runner = threading.Thread(target=httpd.serve_forever, daemon=True)
        runner.start()
        try:
            with response(origin + "/health", timeout=10) as result:
                if json.load(result).get("appId") != "food-up-map":
                    raise AssertionError("Unexpected service")
            counts = {}
            for city in ("fuzhou", "wuhan"):
                with response(f"{origin}/data/{city}.json", timeout=15) as result:
                    counts[city] = len(json.load(result)["catalog"])
            http_done = perf_counter()
            ui = check_edge(origin, counts) if args.edge else None
            ui_done = perf_counter()
        finally:
            httpd.shutdown()
            runner.join()
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                           check=True, text=True, capture_output=True, cwd=fresh)
    done = perf_counter()
    return {"source": source, "system": platform.platform(), "python": platform.python_version(),
            "city_counts": counts, "edge": ui, "data_tests": tests.stderr.strip(),
            "seconds": {"archive_and_extract": round(extracted-started, 3),
                        "http_checks": round(http_done-extracted, 3),
                        "browser_checks": round(ui_done-http_done, 3),
                        "total_through_data_tests": round(done-started, 3)}}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    selection = cli.add_mutually_exclusive_group()
    selection.add_argument("--ref", default="HEAD", help="Git commit for the clean build (default: HEAD)")
    selection.add_argument("--zip", type=Path, help="Trusted source ZIP with server.py at its root")
    cli.add_argument("--edge", action="store_true", help="Add the real Edge checks; requires Python Playwright")
    with tempfile.TemporaryDirectory() as tmp:
        print(json.dumps(verify(Path(tmp).resolve(), cli.parse_args()), ensure_ascii=True, indent=2))
