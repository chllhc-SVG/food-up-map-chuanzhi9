"""Optional browser acceptance check. Run the local service first; requires Playwright and Edge."""
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def verify(page):
    page.goto("http://127.0.0.1:8794/")
    expect(page.locator(".city-buttons strong")).to_have_text(["福州", "武汉"])
    expect(page.get_by_role("button", name="福州", exact=True)).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#videocount")).to_contain_text("293")
    search = page.locator("#search")
    search.fill("厚千禧汉堡")
    expect(page.locator("#videos")).to_contain_text("原片提到停业")
    expect(page.locator("#places")).to_contain_text("当前条件下没有店铺")
    search.fill("")
    panel = page.locator(".note-panel")
    panel.locator("summary").click()
    panel.get_by_label("视频链接").fill("https://www.bilibili.com/video/BV1v4VpzgE5h/")
    panel.get_by_role("button", name="核对来源与店址").click()
    expect(panel).to_contain_text("以下店铺已有同一原视频的关联记录")
    panel.get_by_role("button", name="保存到我的复核记录").click()
    expect(panel.locator("li")).to_have_count(1)
    panel.get_by_role("button", name="在本城列表查看").click()
    expect(page.locator("#detail")).to_contain_text("裕莲茶楼")
    page.reload()
    expect(page.get_by_role("button", name="福州", exact=True)).to_have_attribute("aria-pressed", "true")
    panel.locator("summary").click()
    expect(panel.locator("li")).to_contain_text("裕莲茶楼")
    panel.get_by_role("button", name="移除").click()
    expect(panel.locator("li")).to_have_count(0)
    panel.get_by_label("视频链接").fill("https://example.org/video/BV1v4VpzgE5h/")
    panel.get_by_role("button", name="核对来源与店址").click()
    expect(panel).to_contain_text("请使用完整 BV")
    panel.locator("summary").click()
    page.get_by_role("button", name="武汉", exact=True).click()
    expect(page).to_have_url("http://127.0.0.1:8794/?city=wuhan")
    page.reload()
    expect(page.get_by_role("button", name="武汉", exact=True)).to_have_attribute("aria-pressed", "true")
    snapshot_path = Path(__file__).resolve().parents[1] / "data/wuhan.json"
    wuhan_count = len(json.loads(snapshot_path.read_text(encoding="utf-8-sig"))["catalog"])
    expect(page.locator("#videocount")).to_have_text(f"{wuhan_count} 条视频")
    page.evaluate("window.scrollTo(0,0)")
    output = Path(__file__).resolve().parents[1] / ".local"
    output.mkdir(exist_ok=True)
    page.screenshot(path=output / "双城预览.png")
    page.goto("http://127.0.0.1:8794/?city=fuzhou")
    expect(page.locator("#videocount")).to_contain_text("293")
    expect(page.locator("#plot .river-line").first).to_be_visible()
    page.screenshot(path=output / "福州地图预览.png")


if __name__ == "__main__":
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1380, "height": 960}, locale="zh-CN")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            verify(page)
            assert not errors, errors
            print("OK: catalog, attribution, place selection, local notes, source URL and city switch")
        finally:
            browser.close()
