"""Build the dependency-free GitHub Pages manual from reviewed chapter content."""

from collections import OrderedDict
from html import escape
from hashlib import sha256
from pathlib import Path
import re

from src.chapters import CHAPTERS, UPDATED, VERSION
from src.illustrations import illustrated_body

ROOT = Path(__file__).resolve().parent
SITE = "https://kvadkl.github.io/pardozor-manual/"


def asset_url(path):
    return path + '?v=' + sha256((ROOT / path).read_bytes()).hexdigest()[:10]


def icon(name):
    paths = {
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
        "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
        "print": '<path d="M7 8V3h10v5M7 16H4V8h16v8h-3M7 13h10v8H7z"/><path d="M16 11h1"/>',
        "link": '<path d="m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 2 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
        "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
        "book": '<path d="M12 5C8 2 4 3 2 4v15c4-2 7-1 10 1 3-2 6-3 10-1V4c-2-1-6-2-10 1zm0 0v15"/>',
    }
    return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + paths[name] + '</svg>'


def render():
    groups = OrderedDict()
    for item in CHAPTERS:
        groups.setdefault(item["group"], []).append(item)
    chapters = [item for group in groups.values() for item in group]
    assert len({c["id"] for c in chapters}) == len(chapters)
    nav, articles = [], []
    number = 0
    for group, items in groups.items():
        nav.append(f'<div class="nav-group"><h2>{escape(group)}</h2><ul>')
        for item in items:
            number += 1
            nav.append(f'<li><a href="#{item["id"]}" data-nav="{item["id"]}"><span class="nav-number" aria-hidden="true">{number:02}</span><span>{escape(item["title"])}</span></a></li>')
        nav.append('</ul></div>')
    for position, item in enumerate(chapters):
        headings = []

        def heading(match):
            level, label = match.groups()
            id = f'{item["id"]}--{len(headings) + 1}'
            headings.append((id, re.sub(r"<[^>]+>", "", label)))
            return f'<h{level} id="{id}" tabindex="-1">{label}</h{level}>'

        body = re.sub(r'<h([23])>(.*?)</h\1>', heading, illustrated_body(item), flags=re.S)
        outline = '<details class="chapter-outline"><summary>В этой главе</summary><ul>' + ''.join(
            f'<li><a href="#{id}">{label}</a></li>' for id, label in headings
        ) + '</ul></details>'
        minutes = max(1, round(len(re.sub(r'<[^>]+>', ' ', body).split()) / 160))
        previous = chapters[position - 1] if position else None
        following = chapters[position + 1] if position + 1 < len(chapters) else None
        pager = '<nav class="chapter-pager" aria-label="Соседние главы">'
        if previous:
            pager += f'<a class="previous" href="#{previous["id"]}"><small>← Предыдущая глава</small><span>{escape(previous["title"])}</span></a>'
        else:
            pager += '<span></span>'
        if following:
            pager += f'<a class="next" href="#{following["id"]}"><small>Следующая глава →</small><span>{escape(following["title"])}</span></a>'
        pager += '</nav>'
        articles.append(f'''
<article class="chapter" id="{item['id']}" data-group="{escape(item['group'], quote=True)}" data-keywords="{escape(item['keywords'], quote=True)}">
<header class="chapter-header"><p class="eyebrow">{escape(item['group'])} <span aria-hidden="true">/</span> {position + 1:02} из {len(chapters)}</p>
<h1 tabindex="-1">{escape(item['title'])}</h1><p class="lead">{escape(item['lead'])}</p>
<p class="reading-time">Чтение · {minutes} мин</p></header>{outline}<div class="prose">{body}</div>{pager}</article>''')
    html = f'''<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ПарДозор — инструкция по работе с прибором</title>
<meta name="description" content="Полное руководство ПарДозора: подключение, датчики и поправки, этапы, клапан и ШИМ, весы, Wi-Fi, журналы, отчёты и обслуживание.">
<meta name="theme-color" content="#142725"><meta name="color-scheme" content="light">
<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU">
<meta property="og:title" content="ПарДозор — руководство пользователя"><meta property="og:description" content="От первого включения до настройки ШИМ и разбора журнала. Полная инструкция по работе с прибором.">
<meta property="og:url" content="{SITE}"><meta property="og:image" content="{SITE}assets/controller.jpg">
<link rel="canonical" href="{SITE}"><link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{asset_url('assets/style.css')}"><script src="{asset_url('assets/app.js')}" defer></script>
</head><body>
<a class="skip-link" href="#content">К содержанию главы</a>
<aside class="sidebar" id="sidebar" aria-label="Навигация по инструкции">
<a class="brand" href="#overview" aria-label="ПарДозор — начало инструкции"><img src="favicon.svg" alt="" width="48" height="48"><span><strong>ПарДозор</strong><small>Автоматика и контроль</small></span></a>
<div class="manual-label">Руководство пользователя</div>
<form class="search-form enhanced" role="search" id="searchForm"><label class="sr-only" for="search">Поиск по инструкции</label>{icon('search')}<input id="search" type="search" placeholder="Найти в инструкции" autocomplete="off" enterkeyhint="search" aria-controls="searchResults"><kbd aria-hidden="true">/</kbd></form>
<nav class="contents" id="contents" aria-label="Оглавление">{''.join(nav)}</nav>
<div class="sidebar-bottom"><span class="version-dot" aria-hidden="true"></span> Прошивка {VERSION}<a href="https://kvadkl.github.io/pardozor-demo/" target="_blank" rel="noopener">Записи испытаний ↗</a></div>
</aside>
<button class="drawer-backdrop" id="drawerBackdrop" type="button" aria-label="Закрыть оглавление" hidden></button>
<div class="page">
<header class="topbar"><div class="topbar-title"><button type="button" class="icon-button enhanced menu-toggle" id="menuToggle" aria-controls="sidebar" aria-expanded="false" aria-label="Открыть оглавление">{icon('menu')}</button><span class="desktop-label">ИНСТРУКЦИЯ</span><span class="breadcrumb" id="breadcrumb">Начало работы</span></div>
<div class="toolbar enhanced"><button id="copyLink" type="button" title="Скопировать ссылку на текущий раздел">{icon('link')}<span>Ссылка</span></button><button id="printChapter" type="button" title="Напечатать текущую главу">{icon('print')}<span>Печать главы</span></button><button id="printAll" class="print-all" type="button" title="Напечатать или сохранить в PDF все главы">{icon('book')}<span>Вся инструкция / PDF</span></button></div></header>
<main id="content" tabindex="-1">
<div class="print-cover"><img src="favicon.svg" width="56" height="56" alt=""><h1>ПарДозор</h1><p>Автоматика и контроль · Руководство пользователя</p><p>Прошивка {VERSION} · {UPDATED}</p><p>{SITE}</p></div>
<noscript><p class="no-script">JavaScript выключен: ниже доступны все главы. Оглавление и поиск браузера работают; для печати всей инструкции используйте меню браузера.</p></noscript>
<section id="searchResults" class="search-results" aria-labelledby="searchTitle" hidden><p class="eyebrow">По всей инструкции</p><h1 id="searchTitle">Результаты поиска</h1><p id="searchSummary" role="status" aria-live="polite"></p><div id="searchList"></div></section>
{''.join(articles)}
</main>
<footer class="page-footer"><div><strong>ПарДозор · Руководство пользователя</strong><span>Проверено по прошивке {VERSION} · {UPDATED}</span></div><a href="#reference">Краткая памятка {icon('arrow')}</a></footer>
</div><div class="toast" id="toast" role="status" aria-live="polite"></div>
<dialog class="image-viewer" id="imageViewer" aria-labelledby="imageViewerTitle" aria-describedby="imageViewerCaption"><div class="viewer-toolbar"><p id="imageViewerTitle"></p><div class="viewer-actions"><button type="button" id="imageActualSize" aria-pressed="false">100%</button><a id="imageOriginal" href="assets/controller.jpg" target="_blank" rel="noopener">Оригинал ↗</a><button type="button" id="imageViewerClose" aria-label="Закрыть изображение">Закрыть ×</button></div></div><div id="imageViewerStage" class="viewer-stage" tabindex="0" aria-label="Изображение. В режиме 100% его можно прокручивать."><img id="imageViewerImage" src="assets/controller.jpg" width="800" height="600" alt=""></div><p id="imageViewerCaption"></p><div class="viewer-navigation"><button type="button" id="imagePrevious">← Предыдущее</button><span id="imageViewerCount" role="status" aria-live="polite"></span><button type="button" id="imageNext">Следующее →</button></div></dialog>
</body></html>'''
    (ROOT / 'index.html').write_text(html, encoding='utf-8', newline='\n')
    print(f'Built index.html: {len(chapters)} chapters, {len(html.encode("utf-8")):,} bytes')


if __name__ == '__main__':
    render()
