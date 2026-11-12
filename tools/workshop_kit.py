#!/usr/bin/env python3
"""Prepare a source/signing kit for Windows DayZ Tools; never include secrets."""
from pathlib import Path
import hashlib
import zipfile


def build_kit(repository: Path, output: Path) -> Path:
    selected = [repository / 'tools/Prepare-Workshop.ps1', repository / 'packaging/mod.cpp',
                repository / 'assets/wgza_tag_preview.png', repository / 'docs/WORKSHOP.md',
                repository / 'docs/TESTING.md']
    for folder in ('WGZA_DogTags', 'server'):
        selected.extend(p for p in (repository / folder).rglob('*') if p.is_file() or p.is_symlink())
    files = {}
    for path in selected:
        relative = path.relative_to(repository)
        if path.is_symlink() or not path.resolve().is_relative_to(repository.resolve()):
            raise ValueError(f'Unsafe kit path: {relative}')
        if path.suffix.lower() not in {'.c', '.cpp', '.md', '.ps1', '.xml', '.png'} and path.name != '$PBOPREFIX$':
            raise ValueError(f'Unexpected file in source kit: {relative}')
        files[relative.as_posix()] = path.read_bytes()
    files['START-HERE.txt'] = (b'WolfGamingZA Dog Tags - Workshop preparation kit\n\n'
        b'Read docs/WORKSHOP.md first. Install DayZ Tools on Windows.\n'
        b'Run tools/Prepare-Workshop.ps1 with your DayZ Tools installation path.\n'
        b'This source kit is not an installable mod and is not already signed.\n'
        b'No Steam upload or gameplay test has been performed.\n')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'WGZA_DogTags-Workshop-kit.zip'
    if destination.is_symlink():
        raise ValueError('Refusing symlinked ZIP output')
    with zipfile.ZipFile(destination, 'w') as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo('WGZA_DogTags-Workshop-kit/' + name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('Kit ZIP integrity check failed')
    print(destination)
    print('SHA256:', hashlib.sha256(destination.read_bytes()).hexdigest())
    return destination


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    build_kit(root, root / 'dist')
