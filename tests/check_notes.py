"""Optional browser acceptance check. Run the local service first; requires Playwright and Edge."""
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def verify(page):
    page.goto("http://127.0.0.1:8794/")
    page.get_by_role("button", name="福州", exact=True).click()
    expect(page.locator("#videocount")).to_contain_text("293")
    panel = page.locator(".note-panel")
    panel.locator("summary").click()
    panel.get_by_label("视频链接").fill("https://www.bilibili.com/video/BV1afNJzGE9z/")
    panel.get_by_role("button", name="核对来源与店址").click()
    expect(panel).to_contain_text("以下店铺已有同一原视频的关联记录")
    panel.get_by_role("button", name="保存到我的复核记录").click()
    expect(panel.locator("li")).to_have_count(1)
    panel.get_by_role("button", name="在本城列表查看").click()
    expect(page.locator("#detail")).to_contain_text("裕莲茶楼")
    page.reload()
    page.get_by_role("button", name="福州", exact=True).click()
    panel.locator("summary").click()
    expect(panel.locator("li")).to_contain_text("裕莲茶楼")
    panel.get_by_role("button", name="移除").click()
    expect(panel.locator("li")).to_have_count(0)
    panel.get_by_label("视频链接").fill("https://example.org/video/BV1afNJzGE9z/")
    panel.get_by_role("button", name="核对来源与店址").click()
    expect(panel).to_contain_text("请使用完整 BV")
    panel.locator("summary").click()
    page.get_by_role("button", name="武汉", exact=True).click()
    expect(page.locator("#videocount")).to_contain_text("342")
    page.evaluate("window.scrollTo(0,0)")
    output = Path(__file__).resolve().parents[1] / ".local"
    output.mkdir(exist_ok=True)
    page.screenshot(path=output / "双城预览.png")


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
