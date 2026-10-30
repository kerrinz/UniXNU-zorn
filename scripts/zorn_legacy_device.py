"""Materialize the pinned format1 input view used only by the debug builder.

The public root board uses format2. This view preserves the historical flat
output/module lookup and intentionally excludes its new feeds and xnu series.
It never edits the original board, source tree, archive or phone.
"""
import hashlib
import json
from pathlib import Path
import tomllib

LEGACY_SHA256 = 'd65567ecd289b9fcddb1c1a7dcbf5af277f990f1184a09def54a3582f194b380'


def prepare(device, destination):
    device, destination = Path(device).resolve(), Path(destination).absolute()
    raw = (device / 'compat/legacy/board.toml').read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEGACY_SHA256:
        raise RuntimeError('legacy board differs from the retained diagnostic input')
    board = tomllib.loads(raw.decode())
    if board.get('schema_version', 1) != 1 or board['board']['name'] != 'zorn':
        raise RuntimeError('legacy board identity differs')
    if destination.is_symlink() or destination.resolve().is_relative_to(device):
        raise RuntimeError('legacy view must be a separate generated directory')
    destination.mkdir(parents=True, exist_ok=True)
    marker = destination / 'zorn-legacy-view.json'
    if any(destination.iterdir()) and not marker.is_file():
        raise RuntimeError('unowned nonempty legacy view refused')
    if marker.is_file() and json.loads(marker.read_text()).get('source') != str(device):
        raise RuntimeError('legacy view source differs')
    marker.write_text(json.dumps({'source':str(device), 'board_sha256':LEGACY_SHA256}, indent=2)+'\n')
    for name in ('configs', 'scripts', 'native'):
        target, link = device / name, destination / name
        if link.is_symlink() and link.resolve() == target:
            continue
        if link.exists() or link.is_symlink():
            raise RuntimeError('unexpected legacy view entry: '+name)
        link.symlink_to(target, target_is_directory=True)
    patchdir = destination / 'patches'
    patchdir.mkdir(exist_ok=True)
    if (patchdir / 'xnu').exists() or (patchdir / 'xnu').is_symlink():
        raise RuntimeError('format2 series must not replace the legacy base patch module')
    for source in (device / 'patches').iterdir():
        if source.name == 'xnu' or not source.is_dir():
            continue
        link = patchdir / source.name
        if link.is_symlink() and link.resolve() == source:
            continue
        if link.exists() or link.is_symlink():
            raise RuntimeError('unexpected legacy patch view entry')
        link.symlink_to(source, target_is_directory=True)
    for name, content in [('board.toml',raw), ('unixnu.lock',(device/'unixnu.lock').read_bytes())]:
        target = destination/name
        if target.is_symlink():
            raise RuntimeError('mutable legacy view file must not alias a source')
        target.write_bytes(content)
    if (destination/'feeds.toml').exists():
        raise RuntimeError('format2 feeds must not enter the legacy view')
    return destination
