"""Read-only content, link and publishing checks; standard library only."""

from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.chapters import CHAPTERS, VERSION


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.images, self.scripts = [], [], [], []
        self.articles = 0
        self.buttons = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'img':
            self.images.append(attrs)
        if tag == 'script':
            self.scripts.append(attrs)
        if tag == 'link' and attrs.get('rel') in ('stylesheet', 'icon'):
            self.links.append(attrs.get('href', ''))
        if tag == 'article':
            self.articles += 1
        if tag == 'button':
            self.buttons.append(attrs)


class ManualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, 'build.py'], cwd=ROOT, check=True, capture_output=True)
        cls.html = (ROOT / 'index.html').read_text(encoding='utf-8')
        cls.document = Document(cls.html)

    def test_all_chapters_are_built(self):
        self.assertEqual(len(CHAPTERS), 33)
        self.assertEqual(self.document.articles, len(CHAPTERS))
        for chapter in CHAPTERS:
            self.assertIn(chapter['id'], self.document.ids)
            self.assertIn(chapter['title'], self.html)

    def test_ids_are_unique(self):
        self.assertEqual(len(self.document.ids), len(set(self.document.ids)))

    def test_internal_anchors_resolve(self):
        for href in self.document.links:
            if href.startswith('#'):
                self.assertIn(unquote(href[1:]), self.document.ids, href)

    def test_local_assets_exist_and_are_relative(self):
        for attrs in self.document.images + self.document.scripts:
            src = attrs.get('src')
            self.assertTrue(src)
            self.assertFalse(src.startswith('/'), src)
            self.assertTrue((ROOT / src).is_file(), src)
        for href in self.document.links:
            parts = urlsplit(href)
            if not parts.scheme and parts.path:
                self.assertFalse(parts.path.startswith('/'), href)
                self.assertTrue((ROOT / parts.path).is_file(), href)

    def test_images_have_accessible_text_and_dimensions(self):
        for attrs in self.document.images:
            self.assertIn('alt', attrs)
            self.assertTrue(attrs.get('width'))
            self.assertTrue(attrs.get('height'))

    def test_no_remote_dependencies_or_device_commands(self):
        script = (ROOT / 'assets/app.js').read_text(encoding='utf-8')
        self.assertNotRegex(script, r'\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(')
        self.assertNotIn('onclick=', self.html)
        self.assertNotIn('onload=', self.html)
        self.assertNotIn('innerHTML', script)
        self.assertNotRegex(self.html, r'<script[^>]+src="https?://')
        self.assertNotRegex(self.html, r'<link[^>]+rel="(?:stylesheet|icon)"[^>]+href="https?://')

    def test_manual_limits_and_safety_are_explicit(self):
        by_id = {chapter['id']: chapter for chapter in CHAPTERS}
        self.assertIn('не закрывает клапан', by_id['target']['body'])
        self.assertIn('не управляет нагревателем', by_id['overview']['body'])
        self.assertIn('ROM', by_id['calibration']['body'])
        self.assertIn('Собрать отчёт', by_id['report']['body'])
        self.assertIn('Снижение', by_id['reduction']['title'])
        self.assertIn('8 профилей', by_id['wifi']['body'])
        self.assertIn('0,05', by_id['temperature']['body'])
        self.assertIn(VERSION, self.html)

    def test_semantics_and_fallback(self):
        self.assertIn('<html lang="ru">', self.html)
        self.assertIn('<noscript>', self.html)
        self.assertIn('role="search"', self.html)
        self.assertTrue(all(button.get('type') == 'button' for button in self.document.buttons))
        self.assertTrue((ROOT / '.nojekyll').exists())

    def test_no_private_local_paths_or_placeholder_copy(self):
        public = self.html + (ROOT / 'assets/app.js').read_text(encoding='utf-8')
        self.assertNotRegex(public, r'[CD]:\\|Users[/\\]user|Telegram Desktop|gh[pousr]_[A-Za-z0-9]{20,}')
        self.assertNotRegex(public, r'(?i)lorem ipsum|TODO|coming soon|в разработке|схемы сборки')
        self.assertNotIn('\ufffd', public)

    def test_build_is_deterministic(self):
        first = (ROOT / 'index.html').read_bytes()
        subprocess.run([sys.executable, 'build.py'], cwd=ROOT, check=True, capture_output=True)
        self.assertEqual(first, (ROOT / 'index.html').read_bytes())


if __name__ == '__main__':
    unittest.main()
