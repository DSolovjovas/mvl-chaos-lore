from pathlib import Path
import html
import json
import re
import shutil
import sys
from datetime import datetime
import hashlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'reader'

STORY_ILLUSTRATIONS = {
    'bar-lumi-arrival.png': ROOT / 'Иллюстрации' / '01_Бар' / 'bar-lumi-arrival-v4-faces.png',
    'mansion-exterior.png': ROOT / 'Иллюстрации' / '03_Особняк' / 'mansion-exterior-v1.png',
    'guest-room.png': ROOT / 'Иллюстрации' / '04_Комната' / 'guest-room-v1.png',
    'death-scars.png': ROOT / 'Иллюстрации' / '05_Рубцы' / 'scars-under-top-v8.png',
    'first-morning.png': ROOT / 'Иллюстрации' / '06_Кухня' / 'first-morning-v3.png',
    'flour-apology.png': ROOT / 'Иллюстрации' / '07_Мука' / 'flour-apology-v2.png',
    'accident-aftermath.png': ROOT / 'Иллюстрации' / '08_Авария' / 'accident-aftermath-v4.png',
}


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


def copy_binary(source, target):
    source, target = source.resolve(), target.resolve()
    if not source.is_relative_to(ROOT) or not target.is_relative_to(ROOT):
        raise ValueError('Binary asset is outside the workspace.')
    payload = source.read_bytes()
    if target.exists() and target.read_bytes() == payload:
        return
    if target.exists():
        backup = ROOT / 'Корзина' / target.relative_to(ROOT).parent / (target.stem + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f') + target.suffix)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise ValueError('Binary backup verification failed.')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(payload).digest():
        raise ValueError('Binary copy verification failed.')


def inline(text):
    formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html.escape(text))
    names = re.compile(r'\b(Миу|Луми|Бруно|Векс(?:а|ы|е|у|ой|ою))\b')
    def colour_name(match):
        name = match.group(0)
        role = 'vexa' if name.startswith('Векс') else {'Миу': 'miu', 'Луми': 'lumi', 'Бруно': 'bruno'}[name]
        return f'<span class="character-name {role}">{name}</span>'
    return names.sub(colour_name, formatted)


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
        if lore and line.startswith('# '):
            continue
        if lore and line.startswith(('Непубличный взрослый лор.', 'Взрослый лор.')):
            blocks.append('<details class="content-note"><summary>О содержании · 18+</summary><p>' + inline(line) + '</p></details>')
            continue
        image_match = re.fullmatch(r'!\[(.+?)\]\((illustrations/[a-z0-9-]+\.png)\)', line)
        if image_match:
            alt, path = image_match.groups()
            safe_alt = html.escape(alt, quote=True)
            safe_path = html.escape(path, quote=True)
            blocks.append(f'<figure class="story-illustration"><a href="{safe_path}" target="_blank" rel="noopener"><img src="{safe_path}" alt="{safe_alt}" loading="lazy"></a><figcaption>{safe_alt}</figcaption></figure>')
            continue
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
            kind = ''
            if line.startswith('**'):
                label = line.split('**', 2)[1].lower()
                if any(word in label for word in ('неизвестно', 'открыто', 'предложение', 'возможное')):
                    kind = 'open'
                elif label.startswith('что ') or label.startswith('почему '):
                    kind = 'meaning'
                elif any(word in label for word in ('установлено', 'утверждено', 'рост по', 'рубцы', 'визуальные материалы')):
                    kind = 'fact'
            blocks.append(f'<p class="{kind}">{inline(line)}</p>')
    if in_list:
        blocks.append('</ul>')
    if lore and dialogue != len(speakers):
        raise ValueError('Some annotated dialogue was not rendered.')
    return '\n'.join(blocks), toc


def page(title, subtitle, active, body, toc):
    links = ''.join(f'<a href="#{ident}">{inline(label)}</a>' for ident, label in toc)
    nav = ''.join(f'<a href="{url}" {"aria-current=\"page\"" if key == active else ""}>{label}</a>' for key, url, label in [('lore', 'index.html', 'История'), ('canon', 'canon.html', 'Канон и мир'), ('references', 'references.html', 'Персонажи')])
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta name="color-scheme" content="dark light">
<title>{html.escape(title)} · MVL CHAOS</title><link rel="stylesheet" href="assets/reader.css"><script src="assets/reader.js" defer></script></head>
<body><a class="skip" href="#reading">К тексту</a><div class="progress" aria-hidden="true"></div>
<header class="top"><a class="brand" href="index.html">MVL<span>CHAOS</span></a><nav aria-label="Разделы">{nav}</nav><span class="private">Лор и персонажи · 18+</span></header>
<div class="layout"><aside><details class="contents"><summary>Содержание</summary><div class="toc">{links or '<a href="#reading">Персонажи</a>'}</div></details>
<details class="reading-options"><summary>Поиск и вид</summary><div class="tools"><label for="search">Найти в тексте</label><input id="search" type="search" placeholder="Слово или фраза" autocomplete="off"><p id="search-status" role="status"></p><div id="results"></div><div class="settings"><button id="smaller" aria-label="Уменьшить текст">A−</button><button id="larger" aria-label="Увеличить текст">A+</button><button id="theme" aria-label="Сменить тему">Светлая тема</button></div></div></details>
<div class="legend"><span class="miu">● Миу</span><span class="vexa">● Векса</span><span class="lumi">● Луми</span><span class="bruno">● Бруно</span></div></aside>
<main id="reading" tabindex="-1"><header class="title"><p class="eyebrow">SAME GIRLS. DIFFERENT CHAOS.</p><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p></header><article>{body}</article><footer>Same Girls. Different Chaos. <span>Авторский мир и его истории</span><a href="#reading">Наверх ↑</a></footer></main></div></body></html>'''


def build():
    story = (ROOT / 'История персонажей.md').read_text(encoding='utf-8')
    canon = (ROOT / 'Канон и объяснения.md').read_text(encoding='utf-8')
    write(OUT / 'content' / 'lore.md', story)
    write(OUT / 'content' / 'canon.md', canon)
    for filename, source in STORY_ILLUSTRATIONS.items():
        copy_binary(source, OUT / 'illustrations' / filename)
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
    public_canon = canon.split('### Визуальная непрерывность', 1)[0].rstrip()
    body, toc = render(public_canon, False, speakers)
    body = '<details class="content-note"><summary>Справочник раскрывает сюжет</summary><p>Здесь собран полный канон, включая прошлое персонажей и исход событий. Для первого знакомства с миром начните с раздела «История».</p></details>' + body
    write(OUT / 'canon.html', page('Канон и устройство мира', 'Факты, их значение и вопросы, на которые мы ещё ищем ответы.', 'canon', body, toc))
    characters_path = OUT / 'content' / 'characters.json'
    cards, reference_toc = [], []
    if characters_path.exists():
        for character in json.loads(characters_path.read_text(encoding='utf-8')):
            ident = 'character-' + character['id']
            reference_toc.append((ident, character['name']))
            public = character['public']
            images = []
            for image in character['images']:
                if not image.get('show_on_site', False):
                    continue
                label = 'Портрет' if image['role'] == 'face' else 'Основной образ'
                path = html.escape(image['path'], quote=True)
                images.append(f'<figure><a href="{path}" target="_blank" rel="noopener"><img src="{path}" alt="{html.escape(character["name"])} — {label}" loading="lazy"></a><figcaption>{label}<br><a href="{path}" target="_blank" rel="noopener">Рассмотреть изображение ↗</a></figcaption></figure>')
            cards.append(f'<section class="character {character["colour"]}"><h2 id="{ident}">{inline(character["name"])}</h2><p>{inline(public["description"])}</p><div class="reference-images">{"".join(images)}</div><h3>Характер</h3><p>{inline(public["character"])}</p><h3>Что для них важно</h3><p>{inline(public["motive"])}</p></section>')
    reference_toc.append(('future-looks', 'Другие образы'))
    upcoming = '<h2 id="future-looks">Другие образы</h2><p>Для персонажей подготовлены хэллоуинские костюмы. Они появятся здесь после их показа в истории.</p>'
    write(OUT / 'references.html', page('Персонажи', 'Миу, Векса, Луми и Бруно: внешность, характеры и то, что их объединяет.', 'references', ''.join(cards) + upcoming, reference_toc))
    print(json.dumps({'pages': 3, 'dialogue_lines': len(speakers), 'lore_chapters': sum(line.startswith('## ') for line in story.splitlines()), 'output': str(OUT)}, ensure_ascii=True))


if __name__ == '__main__':
    build()
