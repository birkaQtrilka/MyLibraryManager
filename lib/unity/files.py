"""
File operations for Unity packages — copy sources into Runtime/ or Editor/,
remove named files from those folders.
"""

import shutil
import sys
from pathlib import Path


def copy_sources(sources: list[str], dest_dir: Path, dry_run: bool = False) -> None:
    """
    Copy each path in `sources` into `dest_dir`.

    - If a source is a file, it is copied flat into dest_dir.
    - If a source is a directory, its contents are merged into dest_dir
      (preserving subdirectory structure).
    - Globs are NOT expanded here; pass resolved paths.
    """
    for src_str in sources:
        src = Path(src_str).resolve()
        if not src.exists():
            print(f"  WARNING: source path does not exist, skipping: {src}", file=sys.stderr)
            continue

        if src.is_file():
            dest = dest_dir / src.name
            _copy_file(src, dest, dry_run)
        elif src.is_dir():
            _copy_tree(src, dest_dir, dry_run)
        else:
            print(f"  WARNING: unsupported path type, skipping: {src}", file=sys.stderr)


def _copy_file(src: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] copy {src} → {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"  copy {src.name} → {dest}")


def _copy_tree(src_dir: Path, dest_dir: Path, dry_run: bool) -> None:
    for item in src_dir.rglob("*"):
        if item.is_file():
            relative = item.relative_to(src_dir)
            dest = dest_dir / relative
            _copy_file(item, dest, dry_run)


def remove_files(names: list[str], search_dir: Path, dry_run: bool = False) -> None:
    """
    Remove named files from search_dir. `names` may be bare filenames or
    relative paths within search_dir.
    
    Also deletes the corresponding Unity .meta file (if present) for each
    removed file or directory.
    """
    for name in names:
        target = (search_dir / name).resolve()

        # Safety: must remain inside search_dir
        try:
            target.relative_to(search_dir.resolve())
        except ValueError:
            print(f"  WARNING: path escapes package directory, skipping: {name}", file=sys.stderr)
            continue

        if not target.exists():
            print(f"  WARNING: file not found, skipping: {target}", file=sys.stderr)
            continue

        # Construct the associated .meta file path
        meta_path = target.parent / (target.name + ".meta")

        if dry_run:
            print(f"  [dry-run] remove {target}")
            if meta_path.exists():
                print(f"  [dry-run] remove {meta_path}")
            continue

        # Remove the main file/directory
        if target.is_file():
            target.unlink()
            print(f"  remove {target}")
        elif target.is_dir():
            shutil.rmtree(target)
            print(f"  remove dir {target}")

        # Remove the .meta file if it exists
        if meta_path.exists():
            meta_path.unlink()
            print(f"  remove {meta_path}")