from pathlib import Path
import json
from build_reader import ROOT, OUT, write
from prepare_references import copy_exact


def export():
    destination = ROOT / 'public-site'
    files = [OUT / name for name in ('index.html', 'canon.html', 'references.html')]
    files += list((OUT / 'assets').glob('*.css'))
    files += list((OUT / 'assets').glob('*.js'))
    profiles = json.loads((OUT / 'content' / 'characters.json').read_text(encoding='utf-8'))
    files += [OUT / image['path'] for character in profiles for image in character['images']]
    for source in files:
        target = destination / source.relative_to(OUT)
        if source.suffix == '.png':
            copy_exact(source, target)
        else:
            write(target, source.read_text(encoding='utf-8'))
    write(destination / '.nojekyll', '')
    print(json.dumps({'directory': str(destination), 'files': len(files) + 1, 'source_notes_included': False}))


if __name__ == '__main__':
    export()
