"""Regenerate the print-ready booklet from the adjacent source and real UI captures.

Requires Python, Playwright and Microsoft Edge. Run with the application closed or open.
The application itself has no dependency on this script.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parent / "作品说明.pdf"

def main():
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1220, "height": 840}, locale="zh-CN")
            page.goto((SOURCE / "booklet.html").as_uri(), wait_until="load")
            page.emulate_media(media="print")
            page.evaluate("document.fonts.ready")
            overflow = page.evaluate("""() => [...document.querySelectorAll('section')].flatMap((p, i) => {
                const footer = p.querySelector('.foot').getBoundingClientRect().top;
                const content = [...p.children].filter(c => !c.classList.contains('foot'));
                const bottom = Math.max(...content.map(c => c.getBoundingClientRect().bottom));
                const broken = [...p.querySelectorAll('img')].some(im => !im.complete || im.naturalWidth <= 0);
                return bottom + 5 > footer || broken ? [{page: i + 1, space: footer-bottom, broken}] : [];
            })""")
            if overflow:
                raise ValueError(f"Page overlap or broken image: {overflow}")
            page.pdf(path=str(OUTPUT), prefer_css_page_size=True, print_background=True,
                     outline=True, tagged=True)
        finally:
            browser.close()
    print(OUTPUT)

if __name__ == "__main__":
    main()