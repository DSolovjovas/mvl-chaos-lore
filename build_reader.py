from pathlib import Path
import html
import json
import re
import sys
from datetime import datetime
import hashlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'reader'


def write(path, text):
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Output path is outside the workspace.')
    if path.exists():
        if path.is_symlink():
            raise ValueError('Refusing to overwrite a symbolic link.')
        previous = path.read_bytes()
        if previous == text.encode('utf-8'):
            return
        relative = path.relative_to(ROOT)
        backup = ROOT / 'Корзина' / relative.parent / (path.stem + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f') + path.suffix)
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(previous)
        if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(previous).digest():
            raise ValueError('Backup verification failed.')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def inline(text):
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html.escape(text))


CHAPTERS = {
    'Векса не помнила своего возраста.': '01 · Время без конца',
    'Бар был знаком Вексе': '02 · Вода вместо коктейля',
    'До той ночи Миу жила': '03 · Девушка за дверью',
    'Утром они отправились': '04 · Тише воды',
    'Готовить умела Луми:': '05 · Удивите меня',
    'Вексе не требовался сон.': '06 · Поводы возвращаться',
    'О странностях Вексы': '07 · Правда о Бруно',
    'Позже разговор начала Миу.': '08 · Ещё по одному вопросу',
    'Однажды Векса спокойно достала': '09 · Дом',
}
LABELS = {'vexa': 'Векса', 'miu': 'Миу', 'lumi': 'Луми', 'girls': 'Девушки'}


def render(text, lore=False, speakers=None):
    blocks, toc, counter, dialogue = [], [], 0, 0
    in_list = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        is_list = bool(re.match(r'^(?:- |\d+\. )', line))
        if in_list and not is_list:
            blocks.append('</ul>')
            in_list = False
        if lore and line.startswith('#'):
            continue
        if lore and line.startswith('Непубличный взрослый лор.'):
            blocks.append('<details class="content-note"><summary>О содержании · 18+</summary><p>' + inline(line) + '</p></details>')
            continue
        chapter = next((title for start, title in CHAPTERS.items() if lore and line.startswith(start)), None)
        if chapter:
            counter += 1
            ident = f'section-{counter}'
            toc.append((ident, chapter))
            blocks.append(f'<h2 id="{ident}">{inline(chapter)}</h2>')
        if line.startswith('#'):
            level = min(len(line) - len(line.lstrip('#')), 4)
            title = line.lstrip('# ').strip()
            if level == 1:
                continue
            counter += 1
            ident = f'section-{counter}'
            if level == 2:
                toc.append((ident, title))
            blocks.append(f'<h{level} id="{ident}">{inline(title)}</h{level}>')
        elif line.startswith('—'):
            speaker = 'girls'
            if lore:
                record = speakers[dialogue]
                if record['text'] != line:
                    raise ValueError('Dialogue source changed; update speaker annotations.')
                speaker = record['speaker']
                dialogue += 1
            else:
                matches = [r['speaker'] for r in speakers if r['text'] == line]
                if matches and len(set(matches)) == 1:
                    speaker = matches[0]
            label = LABELS[speaker]
            blocks.append(f'<p class="dialogue {speaker}" data-speaker="{speaker}"><span class="speaker">{label}</span><span>{inline(line)}</span></p>')
        elif is_list:
            if not in_list:
                blocks.append('<ul>')
                in_list = True
            blocks.append('<li>' + inline(line[2:] if line.startswith('- ') else line) + '</li>')
        else:
            kind = 'fact' if line.startswith('**Установлено') else 'meaning' if line.startswith('**Что ') else 'open' if line.startswith('**Пока неизвестно') else ''
            blocks.append(f'<p class="{kind}">{inline(line)}</p>')
    if in_list:
        blocks.append('</ul>')
    if lore and dialogue != len(speakers):
        raise ValueError('Some annotated dialogue was not rendered.')
    return '\n'.join(blocks), toc


def page(title, subtitle, active, body, toc):
    links = ''.join(f'<a href="#{ident}">{inline(label)}</a>' for ident, label in toc)
    nav = ''.join(f'<a href="{url}" {"aria-current=\"page\"" if key == active else ""}>{label}</a>' for key, url, label in [('lore', 'index.html', 'История'), ('canon', 'canon.html', 'Канон и мир'), ('references', 'references.html', 'Референсы')])
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta name="color-scheme" content="dark light">
<title>{html.escape(title)} · MVL CHAOS</title><link rel="stylesheet" href="assets/reader.css"><script src="assets/reader.js" defer></script></head>
<body><a class="skip" href="#reading">К тексту</a><div class="progress" aria-hidden="true"></div>
<header class="top"><a class="brand" href="index.html">MVL<span>CHAOS</span></a><nav aria-label="Разделы">{nav}</nav><span class="private">Личный архив · 18+</span></header>
<div class="layout"><aside><details class="contents" open><summary>Содержание</summary><div class="toc">{links or '<a href="#reading">Персонажи</a>'}</div></details>
<div class="tools"><label for="search">Найти в тексте</label><input id="search" type="search" placeholder="Слово или фраза" autocomplete="off"><p id="search-status" role="status"></p><div id="results"></div><div class="settings"><button id="smaller" aria-label="Уменьшить текст">A−</button><button id="larger" aria-label="Увеличить текст">A+</button><button id="theme" aria-label="Сменить тему">Светлая тема</button></div></div>
<div class="legend"><span class="miu">● Миу</span><span class="vexa">● Векса</span><span class="lumi">● Луми</span></div></aside>
<main id="reading" tabindex="-1"><header class="title"><p class="eyebrow">SAME GIRLS. DIFFERENT CHAOS.</p><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p></header><article>{body}</article><footer>Same Girls. Different Chaos. <span>Внутренний авторский архив</span><a href="#reading">Наверх ↑</a></footer></main></div></body></html>'''


def build():
    story = (ROOT / 'История персонажей.md').read_text(encoding='utf-8')
    canon = (ROOT / 'Канон и объяснения.md').read_text(encoding='utf-8')
    write(OUT / 'content' / 'lore.md', story)
    write(OUT / 'content' / 'canon.md', canon)
    annotation = OUT / 'content' / 'dialogue.json'
    if not annotation.exists():
        roles = ['vexa','lumi','lumi','vexa','vexa','vexa','girls','vexa','girls','vexa','miu','vexa','miu','vexa','miu','vexa','miu','miu','vexa','miu','vexa','vexa','miu','vexa','miu','vexa','lumi','vexa','vexa','miu','vexa','lumi','vexa','vexa','lumi','miu']
        lines = [s.strip() for s in story.splitlines() if s.strip().startswith('—')]
        if len(lines) != len(roles):
            raise ValueError('Unexpected dialogue count.')
        write(annotation, json.dumps([{'text': text, 'speaker': role} for text, role in zip(lines, roles)], ensure_ascii=False, indent=2) + '\n')
    speakers = json.loads(annotation.read_text(encoding='utf-8'))
    body, toc = render(story, True, speakers)
    write(OUT / 'index.html', page('История тех, кто остался', 'Три подруги, один пёс и дом, который постепенно стал их общим.', 'lore', body, toc))
    body, toc = render(canon, False, speakers)
    write(OUT / 'canon.html', page('Канон и устройство мира', 'Факты, их значение и вопросы, на которые мы ещё ищем ответы.', 'canon', body, toc))
    characters_path = OUT / 'content' / 'characters.json'
    cards, reference_toc = [], []
    if characters_path.exists():
        for character in json.loads(characters_path.read_text(encoding='utf-8')):
            ident = 'character-' + character['id']
            reference_toc.append((ident, character['name']))
            images = []
            for image in character['images']:
                label = 'Лицо / морда · главный источник сходства' if image['role'] == 'face' else 'Полный лист · анатомия и основной образ'
                path = html.escape(image['path'], quote=True)
                images.append(f'<figure><a href="{path}" target="_blank" rel="noopener"><img src="{path}" alt="{html.escape(character["name"])} — {html.escape(label)}" loading="lazy"></a><figcaption>{html.escape(label)}<br><a href="{path}" target="_blank" rel="noopener">Открыть оригинал ↗</a></figcaption></figure>')
            rules = ''.join('<li>' + inline(rule) + '</li>' for rule in character['rules'])
            cards.append(f'<section class="character {character["colour"]}"><h2 id="{ident}">{character["name"]}</h2><p class="profile-description">{inline(character["description"])}</p><div class="reference-images">{"".join(images)}</div><h3>Характер</h3><p>{inline(character["character"])}</p><h3>Мотив и роль в истории</h3><p>{inline(character["motive"])}</p><h3>Постоянные правила</h3><ul>{rules}</ul><div class="costume-note"><strong>Хэллоуинский образ</strong><p>{inline(character["halloween"])}</p></div></section>')
    rules_text = (ROOT / 'Правила референсов.md').read_text(encoding='utf-8') if (ROOT / 'Правила референсов.md').exists() else ''
    rules_body, _ = render(rules_text, False, speakers)
    reference_toc.append(('reference-rules', 'Общие правила'))
    write(OUT / 'references.html', page('Персонажи и референсы', 'Основные листы, лица, характеры, мотивы и правила визуальной непрерывности.', 'references', ''.join(cards) + '<h2 id="reference-rules">Общие правила использования</h2>' + rules_body, reference_toc))
    print(json.dumps({'pages': 3, 'dialogue_lines': len(speakers), 'lore_chapters': len(CHAPTERS), 'output': str(OUT)}, ensure_ascii=True))


if __name__ == '__main__':
    build()
