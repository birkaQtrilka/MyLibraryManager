#!/usr/bin/env python3
"""
libman.py — monorepo package manager for Unity packages.

Usage:
    python libman.py init
    python libman.py unity create <Name> --runtime <files/dirs>... --editor <files/dirs>...
    python libman.py unity delete <Name>
    python libman.py unity add-files <Name> --runtime <files>... --editor <files>...
    python libman.py unity remove-files <Name> --runtime <files>... --editor <files>...
    python libman.py unity list
"""

import argparse
import sys
from pathlib import Path
from lib.config import load_or_create_config, set_focused_library, get_focused_library
from lib.git_ops import GitContext
from lib.unity.package import (
    cmd_unity_create,
    cmd_unity_delete,
    cmd_unity_add_files,
    cmd_unity_remove_files,
    cmd_unity_list,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="libman",
        description="Monorepo package manager",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Path to the target library repository (overrides focused library)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-git", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    # ── focus ────────────────────────────────────────────────────────────────
    focus_p = sub.add_parser("focus", help="Remember a library path so you don't have to use --repo")
    focus_p.add_argument("path", help="Absolute or relative path to the library repository")

    # ── init ─────────────────────────────────────────────────────────────────
    sub.add_parser("init", help="Create a .libmanrc config file in the repo root")

    # ── unity ─────────────────────────────────────────────────────────────────
    unity_p = sub.add_parser("unity", help="Manage Unity packages")
    unity_sub = unity_p.add_subparsers(dest="unity_command", required=True)

    # unity create
    create_p = unity_sub.add_parser("create", help="Create a new Unity package")
    create_p.add_argument("name", help="PascalCase package name, e.g. Utils")
    create_p.add_argument(
        "--runtime", nargs="*", default=[], metavar="PATH",
        help="Files/folders to copy into Runtime/",
    )
    create_p.add_argument(
        "--editor", nargs="*", default=[], metavar="PATH",
        help="Files/folders to copy into Editor/",
    )

    # unity delete
    delete_p = unity_sub.add_parser("delete", help="Delete a Unity package")
    delete_p.add_argument("name", help="Package name to delete")

    # unity add-files
    add_p = unity_sub.add_parser("add-files", help="Add files to an existing Unity package")
    add_p.add_argument("name", help="Package name")
    add_p.add_argument("--runtime", nargs="*", default=[], metavar="PATH")
    add_p.add_argument("--editor", nargs="*", default=[], metavar="PATH")

    # unity remove-files
    rm_p = unity_sub.add_parser("remove-files", help="Remove files from a Unity package")
    rm_p.add_argument("name", help="Package name")
    rm_p.add_argument("--runtime", nargs="*", default=[], metavar="PATH",
                      help="File names (relative to Runtime/) to remove")
    rm_p.add_argument("--editor", nargs="*", default=[], metavar="PATH",
                      help="File names (relative to Editor/) to remove")

    # unity list
    unity_sub.add_parser("list", help="List all Unity packages")

    return parser

def resolve_repo_path(args) -> str:
    """Determine which repo path to use based on arguments, cwd, or focus."""
    # 1. Did the user explicitly pass --repo?
    if args.repo:
        return args.repo

    # 2. Is the current working directory a library? (Has .libmanrc or .git)
    cwd = Path.cwd()
    if (cwd / ".libmanrc").exists() or (cwd / ".git").is_dir():
        return str(cwd)

    # 3. Fallback to the globally focused library
    focused = get_focused_library()
    if focused and Path(focused).exists():
        return focused

    # 4. Give up and instruct the user
    print("ERROR: Could not determine which library to manage.", file=sys.stderr)
    print("Please do one of the following:", file=sys.stderr)
    print("  a) 'cd' into your library's directory", file=sys.stderr)
    print("  b) Run 'libman focus /path/to/my/lib' once", file=sys.stderr)
    print("  c) Append '--repo /path/to/my/lib' to your command", file=sys.stderr)
    sys.exit(1)

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Handle 'focus' command immediately (no config needed yet)
    if args.command == "focus":
        set_focused_library(args.path)
        return

    # Figure out the repo path to operate on
    repo_path = resolve_repo_path(args)

    # ── init (no git context needed) ─────────────────────────────────────────
    if args.command == "init":
        load_or_create_config(repo_path, force_create=True)
        return

    cfg = load_or_create_config(repo_path)
    dry_run: bool = args.dry_run
    use_git: bool = not args.no_git

    # ── unity list (read-only, no git needed) ────────────────────────────────
    if args.command == "unity" and args.unity_command == "list":
        cmd_unity_list(cfg)
        return

    # ── all mutating commands go through GitContext ───────────────────────────
    with GitContext(cfg, dry_run=dry_run, enabled=use_git) as git:

        if args.command == "unity":
            if args.unity_command == "create":
                cmd_unity_create(cfg, git, args.name, args.runtime, args.editor, dry_run)
                git.commit(f"feat(unity): add {args.name} package")

            elif args.unity_command == "delete":
                cmd_unity_delete(cfg, git, args.name, dry_run)
                git.commit(f"chore(unity): remove {args.name} package")

            elif args.unity_command == "add-files":
                cmd_unity_add_files(cfg, git, args.name, args.runtime, args.editor, dry_run)
                git.commit(f"feat(unity/{args.name}): add files")

            elif args.unity_command == "remove-files":
                cmd_unity_remove_files(cfg, git, args.name, args.runtime, args.editor, dry_run)
                git.commit(f"chore(unity/{args.name}): remove files")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
