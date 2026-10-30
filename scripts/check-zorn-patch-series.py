#!/usr/bin/env python3
"""Replay the exact K80 patch set in a new, isolated XNU checkout; never use USB."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tomllib

DEVICE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(directory, *args):
    return subprocess.run(
        ["git", "-C", str(directory), *map(str, args)],
        text=True, capture_output=True, timeout=180,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=DEVICE.parent / "UniXNU")
    parser.add_argument("--reference", type=Path, help="local pristine, pinned Apple XNU checkout")
    parser.add_argument("--base-revision", help="explicit 40-digit core commit for base XNU patches; CLI stays current")
    parser.add_argument("--snapshot", type=Path, help="explicit generated qualified-working-tree source capsule")
    parser.add_argument("--workdir", type=Path, required=True, help="new output directory; existing results are refused")
    args = parser.parse_args()
    core = args.core.resolve()
    reference = (args.reference or core / "out/zorn/tree/refer/xnu").resolve()
    output = args.workdir.resolve()
    work = output / "xnu"
    report_path = output / "result.json"
    if output.exists() or output.is_symlink():
        parser.error("existing checkout/result refused; choose a new --workdir")
    lock = tomllib.loads((DEVICE / "unixnu.lock").read_text())
    expected = lock["source"]["xnu"]["commit"]
    source = git(reference, "rev-parse", "HEAD")
    if source.returncode or source.stdout.strip() != expected:
        parser.error("reference must be the exact XNU revision from unixnu.lock")
    snapshot = None
    if args.snapshot:
        if args.base_revision:
            parser.error('--snapshot and --base-revision are separate controls')
        snapshot = json.loads(args.snapshot.read_text())
        name = snapshot['patch']
        if Path(name).name != name or snapshot.get('schema_version') != 1 or snapshot['xnu_commit'] != expected:
            parser.error('snapshot identity/path differs')
        snapshot_patch = args.snapshot.resolve().parent / name
        if digest(snapshot_patch) != snapshot['patch_sha256']:
            parser.error('snapshot patch digest differs')
    board = {p.name: p for p in (DEVICE / "patches/zorn").glob("*.patch")}
    base = {p.name: p for p in (core / "patches/xnu").glob("*.patch")}
    if snapshot:
        base = {}
    elif args.base_revision:
        if not re.fullmatch(r'[0-9a-f]{40}', args.base_revision):
            parser.error('--base-revision requires a full commit ID')
        revision = git(core, 'rev-parse', '--verify', args.base_revision + '^{commit}')
        if revision.returncode:
            parser.error('base revision is not available locally')
        paths = git(core, 'ls-tree', '-r', '--name-only', args.base_revision, '--', 'patches/xnu')
        if paths.returncode:
            parser.error('cannot enumerate the selected base patches')
        output.mkdir(parents=True)
        inputs = output / 'base-patches'
        inputs.mkdir()
        base = {}
        for relative in paths.stdout.splitlines():
            if not relative.endswith('.patch'):
                continue
            result = git(core, 'show', args.base_revision + ':' + relative)
            if result.returncode:
                parser.error('cannot read base patch ' + relative)
            path = inputs / Path(relative).name
            path.write_text(result.stdout)
            base[path.name] = path
    else:
        for name in board.keys() & base.keys():
            if digest(board[name]) != digest(base[name]):
                parser.error(f"stale/conflicting installed device patch: {name}")
    if not snapshot:
        base.update(board)
    prelink = core / "kits/XnuPrelink/patches"
    if not prelink.is_dir():
        parser.error("the existing XnuPrelink component must be available locally")
    selected = [snapshot_patch] if snapshot else [base[n] for n in sorted(base)] + sorted(prelink.glob("*.patch"))
    if not selected:
        parser.error("no patches selected")
    rows = [{"name": p.name, "sha256": digest(p), "device_owned": p.name in board}
            for p in selected]
    report = {"status": "preparing", "source_commit": expected,
              "core_commit": git(core, "rev-parse", "HEAD").stdout.strip(),
              "base_patch_commit": args.base_revision,
              "source_snapshot_sha256": digest(args.snapshot) if snapshot else None,
              "source_snapshot_profile": snapshot['profile'] if snapshot else None,
              "patches": rows, "applied": 0, "old_xnu_objects_reused": False,
              "compiled": False, "device_operations": False}
    output.mkdir(parents=True, exist_ok=True)

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--shared", "--no-checkout", str(reference), str(work)],
            text=True, capture_output=True, timeout=180,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        result = git(work, "checkout", "--quiet", "--detach", expected)
        if result.returncode:
            raise RuntimeError(result.stderr)
        for index, path in enumerate(selected):
            report["current_patch"] = path.name
            # Reject an input edited between planning and applying it.
            if digest(path) != rows[index]["sha256"]:
                raise RuntimeError(f"patch changed during replay: {path.name}")
            for command in (("apply", "--check", path), ("apply", path)):
                result = git(work, *command)
                if result.returncode:
                    raise RuntimeError(f"{path.name}: {result.stderr.strip()}")
            report["applied"] = index + 1
        changed = set(git(work, "diff", "--name-only", "HEAD").stdout.splitlines())
        changed.update(git(work, "ls-files", "--others", "--exclude-standard").stdout.splitlines())
        changed = {name for name in changed if Path(name).name != '.DS_Store'
                   and '__pycache__' not in Path(name).parts}
        report["source_sha256"] = {
            name: digest(work / name) if (work / name).is_file() else None
            for name in sorted(changed)
        }
        if snapshot and report['source_sha256'] != snapshot['source_files']:
            raise RuntimeError('replayed source does not match every capsule file')
        pins = json.loads((DEVICE / "native/smp/runtime-source-pins.json").read_text())
        report["smp_baseline_pins_match"] = all(
            digest(work / name) == row["before"] for name, row in pins.items()
        )
        if not report["smp_baseline_pins_match"]:
            raise RuntimeError("replayed source differs from the qualified pre-SMP source pins")
        report["status"] = "source-replay-passed"
        save()
        print(f"PASS: {report['applied']} patches; four SMP source pins match; no build or USB")
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status="failed", error=str(error))
        save()
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
