from pathlib import Path
import json
import hashlib
import shutil
from datetime import datetime
from build_reader import ROOT, OUT, write
from prepare_references import copy_exact


def export():
    destination = ROOT / 'public-site'
    files = [OUT / name for name in ('index.html', 'canon.html', 'references.html')]
    files += list((OUT / 'assets').glob('*.css'))
    files += list((OUT / 'assets').glob('*.js'))
    files += list((OUT / 'illustrations').glob('*.png'))
    profiles = json.loads((OUT / 'content' / 'characters.json').read_text(encoding='utf-8'))
    files += [OUT / image['path'] for character in profiles for image in character['images'] if image.get('show_on_site', False)]
    files = list(dict.fromkeys(files))
    expected = {destination / source.relative_to(OUT) for source in files}
    expected.add(destination / '.nojekyll')
    if not destination.resolve().is_relative_to(ROOT):
        raise ValueError('Export directory is outside the workspace.')
    for previous in destination.rglob('*'):
        if previous.is_symlink():
            raise ValueError('Symbolic links are not allowed in the public export.')
        if not previous.is_file() or previous in expected:
            continue
        if not previous.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Stale export file is outside the export directory.')
        backup = ROOT / 'Корзина' / 'public-site' / previous.relative_to(destination)
        backup = backup.with_name(backup.stem + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + backup.suffix)
        backup.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(previous.read_bytes()).digest()
        shutil.move(str(previous), str(backup))
        if hashlib.sha256(backup.read_bytes()).digest() != digest:
            raise ValueError('Stale export backup verification failed.')
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
