"""Desktop/mobile, search, print and no-JavaScript checks in real Chrome."""

from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'test-results'
sys.path.insert(0, str(ROOT))
from src.chapters import CHAPTERS


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextmanager
def server():
    # Serve the parent directory so relative resources are checked under the
    # same project subpath used by GitHub Pages, not only at the domain root.
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT.parent)))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}/{ROOT.name}/'
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def check():
    RESULTS.mkdir(exist_ok=True)
    errors, failed = [], []
    checks = 0
    with server() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        context.grant_permissions(['clipboard-read', 'clipboard-write'])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: failed.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        page.goto(url, wait_until='networkidle')
        assert page.locator('article:visible').count() == 1
        assert page.locator('[aria-current=page]').get_attribute('data-nav') == 'overview'
        assert page.locator('img').first.get_attribute('src') == 'favicon.svg'
        page.screenshot(path=str(RESULTS / 'desktop-overview.png'), full_page=True)
        checks += 3

        for chapter in CHAPTERS:
            page.goto(url + '#' + chapter['id'], wait_until='domcontentloaded')
            assert page.locator('article:visible').count() == 1, chapter['id']
            assert page.locator('article:visible h1').inner_text() == chapter['title'], chapter['id']
            assert page.locator('[aria-current=page]').get_attribute('data-nav') == chapter['id']
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), chapter['id']
            checks += 4

        page.goto(url + '#dashboard')
        dashboard_image = page.locator('#figure-dashboard-dev104 .screenshot-link')
        dashboard_image.click()
        assert page.locator('#imageViewer').evaluate('(node) => node.open')
        assert page.locator('#imageViewerCaption').inner_text().startswith('Интерфейс dev.104')
        assert page.locator('#imageViewerImage').get_attribute('src').endswith('dashboard-dev104.png')
        page.locator('#imageActualSize').click()
        assert page.locator('#imageActualSize').get_attribute('aria-pressed') == 'true'
        assert page.locator('#imageViewerImage').evaluate('(node) => node.getBoundingClientRect().width') == 1448
        page.screenshot(path=str(RESULTS / 'desktop-image-100-percent.png'))
        page.locator('#imageActualSize').click()
        page.keyboard.press('ArrowRight')
        assert page.locator('#imageViewerImage').get_attribute('src').endswith('navigation-dev104.png')
        page.keyboard.press('Escape')
        assert not page.locator('#imageViewer').evaluate('(node) => node.open')
        assert not page.locator('body').evaluate('(node) => node.classList.contains("image-open")')
        assert dashboard_image.evaluate('(node) => node === document.activeElement')
        page.screenshot(path=str(RESULTS / 'desktop-illustrated-dashboard.png'), full_page=True)
        page.goto(url + '#self-reflux')
        page.locator('#figure-plateau-trial .screenshot-link').click()
        assert 'прежний интерфейс' in page.locator('#imageViewerCaption').inner_text()
        assert page.locator('#imageViewerCount').inner_text() == '1 / 3'
        page.locator('#imageNext').click()
        assert page.locator('#imageViewerImage').get_attribute('src').endswith('reflux-running-trial.png')
        page.locator('#imageViewerClose').click()
        checks += 12

        page.goto(url + '#pwm')
        page.locator('.chapter:visible .chapter-outline').evaluate('(node) => node.open = true')
        heading_link = page.locator('.chapter:visible .chapter-outline a').nth(1)
        heading_id = heading_link.get_attribute('href')[1:]
        heading_link.click()
        assert page.locator('article:visible').get_attribute('id') == 'pwm'
        assert page.evaluate('document.activeElement.id') == heading_id
        page.screenshot(path=str(RESULTS / 'desktop-pwm.png'), full_page=True)
        page.locator('#copyLink').click()
        assert heading_id in page.evaluate('navigator.clipboard.readText()')
        checks += 3

        page.locator('#search').fill('гистерезис')
        page.wait_for_timeout(220)
        assert page.locator('#searchResults').is_visible()
        assert page.locator('.search-result').count() >= 2
        assert page.locator('.search-result mark').count() > 0
        page.locator('.search-result').first.click()
        assert page.locator('article:visible').count() == 1
        assert not page.locator('#searchResults').is_visible()
        checks += 5

        page.locator('#search').fill('<img src=x onerror=alert(1)>')
        page.wait_for_timeout(220)
        assert page.locator('.search-result').count() == 0
        assert page.locator('#searchResults img').count() == 0
        page.locator('#search').press('Escape')
        page.goto(url + '#history')
        page.evaluate('window.print = () => { window.printCalls = (window.printCalls || 0) + 1; }')
        page.locator('#printAll').click()
        page.wait_for_function('window.printCalls >= 1')
        assert page.evaluate('document.body.dataset.print') == 'all'
        page.emulate_media(media='print')
        assert page.locator('article:visible').count() == 33
        assert page.locator('.print-cover').is_visible()
        assert page.locator('.screenshot img').evaluate_all('(images) => images.length === 17 && images.every(image => image.complete && image.naturalWidth > 0)')
        assert not page.locator('#imageViewer').is_visible()
        page.pdf(path=str(RESULTS / 'full-manual.pdf'), prefer_css_page_size=True, print_background=True)
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        page.emulate_media(media='screen')
        page.locator('#printChapter').click()
        page.wait_for_function('window.printCalls >= 2')
        page.emulate_media(media='print')
        assert page.locator('article:visible').count() == 1
        assert not page.locator('.print-cover').is_visible()
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        page.emulate_media(media='screen')
        checks += 10

        page.goto(url + '#not-a-real-chapter')
        assert page.locator('article:visible').get_attribute('id') == 'overview'
        checks += 1

        for width in (360, 390, 768):
            page.set_viewport_size({'width': width, 'height': 844})
            for chapter in CHAPTERS:
                page.goto(url + '#' + chapter['id'], wait_until='domcontentloaded')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, chapter['id'])
                assert page.locator('article:visible h1').is_visible()
                checks += 2
            page.goto(url + '#overview')
            assert page.locator('#sidebar').evaluate('(node) => node.inert')
            page.locator('#menuToggle').click()
            assert page.locator('#menuToggle').get_attribute('aria-expanded') == 'true'
            assert not page.locator('#sidebar').evaluate('(node) => node.inert')
            page.locator('#search').fill('ШИМ')
            page.locator('#search').press('Enter')
            assert page.locator('#searchResults').is_visible()
            assert page.locator('#menuToggle').get_attribute('aria-expanded') == 'false'
            assert page.locator('.search-result').count() >= 3
            page.locator('.search-result').first.click()
            assert page.locator('article:visible').count() == 1
            checks += 7
            page.goto(url + '#pwm')
            page.screenshot(path=str(RESULTS / f'mobile-{width}-pwm.png'), full_page=True)
            page.locator('#menuToggle').click()
            page.screenshot(path=str(RESULTS / f'mobile-{width}-menu.png'))
            page.keyboard.press('Escape')
            assert page.locator('#menuToggle').get_attribute('aria-expanded') == 'false'
            checks += 1
            page.goto(url + '#sensors')
            page.locator('#figure-channel-dev104 .screenshot-link').click()
            assert page.locator('#imageViewer').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#imageActualSize').click()
            assert page.locator('#imageViewerImage').evaluate('(node) => node.getBoundingClientRect().width') == 550
            assert page.locator('#imageViewerStage').evaluate('(node) => node.scrollHeight > node.clientHeight')
            page.screenshot(path=str(RESULTS / f'mobile-{width}-image-viewer.png'))
            page.locator('#imageViewerClose').click()
            assert page.locator('#figure-channel-dev104 .screenshot-link').evaluate('(node) => node === document.activeElement')
            checks += 5

        fallback = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
        nojs = fallback.new_page()
        nojs.goto(url, wait_until='networkidle')
        assert nojs.locator('article:visible').count() == 33
        assert nojs.locator('nav[aria-label="Оглавление"]').is_visible()
        assert nojs.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert nojs.locator('.screenshot-link').count() == 17
        assert nojs.locator('#figure-channel-dev104 a').get_attribute('target') == '_blank'
        checks += 5
        assert not errors, errors
        assert not failed, failed
        # The installed antivirus injects its own monitoring script into Chrome.
        # Do not change or disable it; distinguish that environment instrumentation
        # from dependencies requested by the manual itself.
        external = page.evaluate('performance.getEntriesByType("resource").filter(entry => { const u = new URL(entry.name); return u.origin !== location.origin && !u.hostname.endsWith(".kaspersky-labs.com"); }).map(entry => entry.name)')
        assert not external, external
        checks += 3
        browser.close()
    print(f'PASS: {checks} browser checks; 33 routes; 1440/768/390/360 px; search, clipboard, print, no-JS; no errors.')


if __name__ == '__main__':
    check()
