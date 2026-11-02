"""
Pull (copy out) files or directories from a Unity package into a destination
directory (normally the terminal's current directory).

Read-only with respect to the library, so no git commit is involved.
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {".git", "bin", "obj", "Library", "Temp", "Build"}


def resolve_item(pkg_dir: Path, item: str) -> list[Path]:
    """
    Resolve `item` to paths inside the package.
    1. Treated as a path relative to the package root (e.g. Runtime/Foo.cs, Editor).
    2. Otherwise, searched recursively by exact file/dir name (e.g. Foo.cs).
    Returns every match; the caller decides what to do about ambiguity.
    """
    root = pkg_dir.resolve()
    direct = (root / item).resolve()

    try:
        direct.relative_to(root)
    except ValueError:
        print(f"  WARNING: path escapes package directory, skipping: {item}", file=sys.stderr)
        return []

    if direct.exists():
        return [direct]

    return sorted(
        p for p in root.rglob("*")
        if p.name == item and p.suffix != ".meta"
    )


def resolve_items(pkg_dir: Path, items: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    for item in items:
        matches = resolve_item(pkg_dir, item)
        if not matches:
            print(f"  WARNING: '{item}' not found in package, skipping", file=sys.stderr)
        elif len(matches) > 1:
            print(f"  WARNING: '{item}' is ambiguous, be more specific. Matches:", file=sys.stderr)
            for m in matches:
                print(f"    {m.relative_to(pkg_dir.resolve())}", file=sys.stderr)
        else:
            result.append(matches[0])
    return result



def _copy_file(src: Path, dest: Path, force: bool, dry_run: bool) -> bool:
    if dest.exists() and not force:
        print(f"  WARNING: {dest} already exists, skipping (use --force to overwrite)", file=sys.stderr)
        return False
    if dry_run:
        print(f"  [dry-run] copy {src} → {dest}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"  copy {src.name} → {dest}")
    return True


def copy_paths(
    sources: list[Path],
    dest_root: Path,
    flat: bool = False,
    force: bool = False,
    include_meta: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Copy files/directories into `dest_root`. Returns the number of files copied.
    - file      → dest_root/<file name>
    - directory → dest_root/<dir name>/...   (or its contents directly if `flat`)
    .meta files and build/IDE folders are skipped unless `include_meta` is set.
    """
    dest_root = dest_root.resolve()
    count = 0

    for src in sources:
        if src.is_file():
            count += _copy_file(src, dest_root / src.name, force, dry_run)
            continue

        if not src.is_dir():
            print(f"  WARNING: unsupported path, skipping: {src}", file=sys.stderr)
            continue

        if dest_root == src or src in dest_root.parents:
            print(f"  ERROR: destination is inside {src}, refusing to copy it into itself", file=sys.stderr)
            continue

        target_base = dest_root if flat else dest_root / src.name
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            if any(part in SKIP_DIRS for part in rel.parts[:-1]):
                continue
            if f.suffix == ".meta" and not include_meta:
                continue
            count += _copy_file(f, target_base / rel, force, dry_run)

    return count


# ------------------------------------------------------------------- command

def cmd_unity_pull(
    cfg,
    name: str,
    items: list[str],
    dest: Path,
    flat: bool,
    force: bool,
    include_meta: bool,
    dry_run: bool,
) -> None:
    pkg_dir = cfg.unity_root / name
    if not pkg_dir.is_dir():
        print(f"ERROR: Package '{name}' not found at {pkg_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\nPulling from '{name}' into {dest}")
    sources = resolve_items(pkg_dir, items) if items else [pkg_dir.resolve()]
    n = copy_paths(sources, dest, flat, force, include_meta, dry_run)
    print(f"Done. {n} file(s) {'would be ' if dry_run else ''}copied.\n")


# -------------------------------------------------------------- autocomplete

def package_item_completer(prefix, parsed_args, **kwargs):
    """Complete file/dir paths (relative to the package root) for `unity pull`."""
    from lib.config import get_library, get_valid_library_path  # local import: avoid cycles
    try:
        repo = Path(get_valid_library_path(get_library(parsed_args)))
        unity_dir = json.loads((repo / ".libmanrc").read_text(encoding="utf-8"))["unity_folder"]
        pkg = repo / unity_dir / parsed_args.name
        if not pkg.is_dir():
            return []
        out = []
        for p in pkg.rglob("*"):
            if p.suffix == ".meta" or any(part in SKIP_DIRS for part in p.relative_to(pkg).parts):
                continue
            rel = p.relative_to(pkg).as_posix()
            if rel.startswith(prefix):
                out.append(rel)
        return out[:200]
    except Exception:
        return []