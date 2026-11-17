"""Optional UI acceptance test. Start server.py on localhost:8794, then run:
python tests/check_locations.py  (requires Microsoft Edge and Python Playwright).
Uses a new isolated browser context; it does not touch the user's favorites.
"""
import re

from playwright.sync_api import Page, expect, sync_playwright


URL = "http://127.0.0.1:8794"
MULTI_STORE_FILM = "BV1gLZUYgEMz"


def card(page: Page, name: str):
    return page.locator("#places .place").filter(
        has=page.get_by_text(name, exact=True)
    )


def verify_location(page: Page):
    page.goto(f"{URL}/?city=fuzhou")
    expect(page.locator("#channel")).to_contain_text("酷酷的珊文鱼")
    page.locator("#locate").click()
    expect(page.locator("#location")).to_contain_text("未获得定位权限")
    expect(page.locator("#places")).not_to_contain_text("直线约")

    page.locator("#origin").select_option(label="米丝林 · 店铺点位")
    expect(page.locator("#sort")).to_have_value("near")
    expect(page.locator("#location")).to_contain_text("已切换为「距出发点最近」")
    expect(page.locator("#location")).to_contain_text("手选起点「米丝林」")
    origin_card = card(page, "米丝林")
    expect(origin_card).to_contain_text("直线约 0 米")

    # The verified venue point and the documented mall address point are ~227 m apart.
    page.locator("#search").fill("裕莲茶楼")
    mall = card(page, "裕莲茶楼")
    expect(mall).to_contain_text("地址参考")
    match = re.search(r"地址参考直线约\s*(\d+)\s*米", mall.inner_text())
    assert match and 200 <= int(match.group(1)) <= 260, mall.inner_text()

    page.locator("#search").fill("银河隧道")
    area = card(page, "银河隧道")
    expect(area).to_contain_text("片区参考")
    expect(area).not_to_contain_text("直线约")
    page.locator("#approx").check()
    expect(area).to_contain_text("片区参考直线约")
    page.locator("#approx").uncheck()
    expect(area).not_to_contain_text("直线约")
    return match.group(1)


def verify_saved_places(page: Page):
    page.locator("#search").fill("米丝林")
    card(page, "米丝林").click()
    page.locator("#detail").get_by_role("button", name="☆ 收藏这家店").click()
    page.reload()
    expect(page.get_by_role("button", name="福州", exact=True)).to_have_attribute("aria-pressed", "true")
    page.locator("#onlyfav").click()
    expect(page.locator("#places .place-name")).to_have_text(["米丝林"])

    page.get_by_role("button", name="武汉", exact=True).click()
    expect(page.locator("#channel")).to_contain_text("员外的觅食人生")
    page.locator("#onlyfav").click()
    expect(page.locator("#places .place")).to_have_count(0)

    page.get_by_role("button", name="福州", exact=True).click()
    expect(page.locator("#channel")).to_contain_text("酷酷的珊文鱼")
    page.locator("#onlyfav").click()
    expect(page.locator("#places .place-name")).to_have_text(["米丝林"])
    page.locator("#onlyfav").click()


def verify_device_sort_notice(browser):
    with browser.new_context(geolocation={"latitude": 26.08, "longitude": 119.30},
                             permissions=["geolocation"], locale="zh-CN") as context:
        page = context.new_page()
        page.goto(f"{URL}/?city=fuzhou")
        expect(page.locator("#channel")).to_contain_text("酷酷的珊文鱼")
        page.locator("#locate").click()
        expect(page.locator("#sort")).to_have_value("near")
        expect(page.locator("#location")).to_contain_text("已切换为「距出发点最近」")
        page.locator("#sort").select_option("personal")
        expect(page.locator("#location")).not_to_contain_text("已切换为")
        expect(page.locator("#location")).to_contain_text("设备位置")


def verify_mixed_film(page: Page):
    search = page.locator("#search")
    search.fill("CARPORT")
    expect(card(page, "CARPORT咖啡")).to_be_visible()
    search.fill("汉堡")
    more = page.locator("#moreplaces")
    while more.is_visible():
        more.click()
    expect(card(page, "CARPORT咖啡")).to_have_count(0)
    source_link = page.locator(f'#videos a[href*="{MULTI_STORE_FILM}"]')
    while not source_link.count() and page.locator("#morevideos").is_visible():
        page.locator("#morevideos").click()
    expect(source_link).to_be_visible()
    expect(source_link).to_contain_text("汉堡")


def main():
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 960}, locale="zh-CN")
            # Simulate a user refusing the OS/browser location prompt.
            context.add_init_script(
                "navigator.geolocation.getCurrentPosition = (_ok, fail) => "
                "fail({code: 1, message: 'User denied geolocation'});"
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            meters = verify_location(page)
            verify_saved_places(page)
            verify_mixed_film(page)
            verify_device_sort_notice(browser)
            assert not errors, errors
            print(f"PASS: device and manual origin show the automatic sort change; mall address {meters} m; "
                  "area distances opt-in; favorite persisted and remained city-specific; "
                  f"multi-store film {MULTI_STORE_FILM} searchable without a false burger match.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
