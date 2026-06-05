"""
Unity package commands.

Each cmd_* function performs its file-system work and then the caller
is responsible for calling git.commit() with an appropriate message.
"""

import json
import shutil
import sys
import re
from pathlib import Path

from lib.config import Config
from lib.git_ops import GitContext
from lib.unity.names import derive_names, make_package_json, make_runtime_asmdef, make_editor_asmdef
from lib.unity.files import copy_sources, remove_files


# helpers

def _require_package_exists(unity_root: Path, name: str) -> Path:
    pkg_dir = unity_root / name
    if not pkg_dir.is_dir():
        print(f"ERROR: Package '{name}' not found at {pkg_dir}", file=sys.stderr)
        sys.exit(1)
    return pkg_dir


def _require_package_absent(unity_root: Path, name: str) -> Path:
    pkg_dir = unity_root / name
    if pkg_dir.exists():
        print(f"ERROR: Package '{name}' already exists at {pkg_dir}", file=sys.stderr)
        sys.exit(1)
    return pkg_dir


def _write(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  write {path}")


# create 

def cmd_unity_create(
    cfg: Config,
    git: GitContext,
    name: str,
    runtime_sources: list[str],
    editor_sources: list[str],
    dry_run: bool,
) -> None:
    unity_root = cfg.unity_root
    pkg_dir = _require_package_absent(unity_root, name)
    names = derive_names(cfg, name)

    print(f"\nCreating Unity package '{names.display_name}' ({names.package_id})")

    runtime_dir = pkg_dir / "Runtime"
    editor_dir = pkg_dir / "Editor"

    # Folder structure
    for d in (runtime_dir, editor_dir):
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  [dry-run] mkdir {d}")

    # package.json
    _write(pkg_dir / "package.json", make_package_json(cfg, names), dry_run)

    # Assembly definitions
    _write(
        runtime_dir / names.asmdef_runtime_file,
        make_runtime_asmdef(names),
        dry_run,
    )
    _write(
        editor_dir / names.asmdef_editor_file,
        make_editor_asmdef(names),
        dry_run,
    )

    # Copy provided source files
    if runtime_sources:
        print(f"  Copying runtime files:")
        copy_sources(runtime_sources, runtime_dir, dry_run)
    if editor_sources:
        print(f"  Copying editor files:")
        copy_sources(editor_sources, editor_dir, dry_run)

    print(f"Done. Package at: {pkg_dir}\n")


# delete

def cmd_unity_delete(
    cfg: Config,
    git: GitContext,
    name: str,
    dry_run: bool,
) -> None:
    unity_root = cfg.unity_root
    pkg_dir = _require_package_exists(unity_root, name)
    meta_path = pkg_dir.with_suffix(pkg_dir.suffix + ".meta")  # e.g., "MyPackage.meta"

    print(f"\nDeleting Unity package '{name}' at {pkg_dir}")
    confirm = input(f"Are you sure? {'[dry-run]' if dry_run else 'This cannot be undone'}. [Y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    if dry_run:
        print(f"  [dry-run] remove {pkg_dir}")
        if meta_path.exists():
            print(f"  [dry-run] remove {meta_path}")
    else:
        shutil.rmtree(pkg_dir)
        print(f"  Removed {pkg_dir}")
        if meta_path.exists():
            meta_path.unlink()
            print(f"  Removed {meta_path}")

    print("Done.\n")


# add-files

def ensure_namespace_in_file(file_path: Path, namespace: str) -> bool:
    """Add namespace wrapper to a C# file if it doesn't have one."""
    if not file_path.suffix == '.cs':
        return False
    
    content = file_path.read_text(encoding='utf-8')
    
    # Check if already has a namespace
    if 'namespace ' in content:
        return False
    
    # Extract class name
    class_match = re.search(r'public\s+class\s+(\w+)', content)
    if not class_match:
        return False
    
    class_name = class_match.group(1)
    
    # Wrap content in namespace
    wrapped = f"""namespace {namespace} {{
{content}
}}"""
    
    file_path.write_text(wrapped, encoding='utf-8')
    return True

def cmd_unity_add_files(cfg, git, package_name, runtime_files, editor_files, dry_run):
    """Add files to package with namespace enforcement."""
    package_path = cfg.unity_root / package_name
    
    # Determine namespace from package prefix
    namespace = f"{cfg.assembly_prefix}.{package_name}"
    
    for file_path in runtime_files:
        src = Path(file_path)
        dest = package_path / "Runtime" / src.name
        if dry_run:
            print(f"[dry-run] Would copy {src} -> {dest}")
        else:
            shutil.copy2(src, dest)
            # Ensure C# files have namespace
            ensure_namespace_in_file(dest, namespace)
            print(f"  Added {dest} (namespaced as {namespace})")
    
    for file_path in editor_files:
        src = Path(file_path)
        dest = package_path / "Editor" / src.name
        if dry_run:
            print(f"[dry-run] Would copy {src} -> {dest}")
        else:
            shutil.copy2(src, dest)
            ensure_namespace_in_file(dest, namespace)
            print(f"  Added {dest} (namespaced as {namespace})")


# remove-files

def cmd_unity_remove_files(
    cfg: Config,
    git: GitContext,
    name: str,
    runtime_names: list[str],
    editor_names: list[str],
    dry_run: bool,
) -> None:
    unity_root = cfg.unity_root
    pkg_dir = _require_package_exists(unity_root, name)

    print(f"\nRemoving files from Unity package '{name}'")

    if runtime_names:
        print(f"  From Runtime/:")
        remove_files(runtime_names, pkg_dir / "Runtime", dry_run)

    if editor_names:
        print(f"  From Editor/:")
        remove_files(editor_names, pkg_dir / "Editor", dry_run)

    if not runtime_names and not editor_names:
        print("  Nothing to do — no files specified.")
        sys.exit(0)

    print("Done.\n")


# list

def cmd_unity_list(cfg: Config) -> None:
    unity_root = cfg.unity_root

    if not unity_root.is_dir():
        print(f"Unity folder not found: {unity_root}")
        return

    packages = sorted(
        p for p in unity_root.iterdir()
        if p.is_dir() and (p / "package.json").exists()
    )

    if not packages:
        print("No Unity packages found.")
        return

    print(f"\nUnity packages in {unity_root}:\n")
    col_name = max(len(p.name) for p in packages)

    for pkg_dir in packages:
        try:
            meta = json.loads((pkg_dir / "package.json").read_text())
        except (json.JSONDecodeError, OSError):
            meta = {}

        name = pkg_dir.name.ljust(col_name)
        version = meta.get("version", "?")
        pkg_id = meta.get("name", "")
        display = meta.get("displayName", "")

        print(f"  {name}  v{version}  {pkg_id}  ({display})")

    print()


# structure

def cmd_unity_structure(
    cfg: Config,
    git: GitContext,
    name: str,
    with_files: bool,
    dry_run: bool,
) -> None:
    """
    Display folder (and optionally file) tree structure of a Unity package.
    
    Args:
        cfg: Configuration object containing unity_root.
        git: GitContext (unused, kept for signature consistency).
        name: Package name (subfolder under unity_root).
        with_files: If True, include file names; otherwise only directories.
        dry_run: Not used for this read‑only command, but kept for compatibility.
    """
    unity_root = cfg.unity_root
    pkg_dir = _require_package_exists(unity_root, name)

    print(f"\nStructure of Unity package '{name}':\n")
    
    # Directories we typically want to skip when showing structure
    SKIP_DIRS = {".git", "bin", "obj", "Library", "Temp", "Build"}
    
    def should_skip(path: Path) -> bool:
        """Check if a file or directory should be skipped."""
        # Skip .meta files
        if path.suffix == '.meta':
            return True
        # Skip specific directories
        if path.is_dir() and path.name in SKIP_DIRS:
            return True
        return False
    
    def _print_tree(path: Path, prefix: str = ""):
        """Recursively print directory tree."""
        # Get sorted list of children: directories first, then files
        try:
            children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            return
        
        # Filter out items we want to skip
        children = [c for c in children if not should_skip(c)]
        
        for i, child in enumerate(children):
            is_last = (i == len(children) - 1)
            connector = "└── " if is_last else "├── "
            
            if child.is_dir():
                print(f"{prefix}{connector}{child.name}/")
                extension = "    " if is_last else "│   "
                _print_tree(child, prefix + extension)
            elif with_files:
                print(f"{prefix}{connector}{child.name}")
    
    _print_tree(pkg_dir)
    print()