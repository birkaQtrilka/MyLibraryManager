#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

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
import pyperclip
from pathlib import Path
from typing import Optional
from lib.autocomplete import package_name_completer, setup_powershell_autocomplete
from lib.config import create_config, get_valid_library, load_config, config_exists, set_focused_library, get_focused_library
from lib.git_ops import GitContext
from lib.recursive_help_formatter import RecursiveHelpFormatter
from lib.unity.package import (
    cmd_run_unity,
    cmd_unity_create,
    cmd_unity_delete,
    cmd_unity_add_files,
    cmd_unity_remove_files,
    cmd_unity_list,
    cmd_unity_structure,
)
import argcomplete
from argcomplete.completers import FilesCompleter

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="libman",
        description="Monorepo package manager",
        formatter_class=RecursiveHelpFormatter,
        epilog="""
Examples:
  libman focus /path/to/repo
  libman init
  libman unity create MyPackage --runtime src/ --editor editor/
  libman unity list
  libman unity add-files MyPackage --runtime newfile.cs
  libman unity remove-files MyPackage --runtime oldfile.cs
  libman unity delete MyPackage
  libman unity dir MyPackage
  libman unity dir MyPackage --files
        """
    )
    parser.add_argument(
        "--repo", default=None,
        help="Path to the target library repository (overrides focused library)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-git", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    # list_p = sub.add_parser("list", "lists all packages in focused library")

    # focus
    focus_p = sub.add_parser("focus", help="Remember a library path so you don't have to use --repo")
    focus_p.add_argument("path", help="Absolute or relative path to the library repository")

    # visit
    visit_p = sub.add_parser("visit", help="Go to the focused library")
    visit_p.add_argument("--copy", action="store_true", help="Copies to clipboard instead of visiting there")

    # init
    sub.add_parser("init", help="Create a .libmanrc config file in the repo root")

    # unity
    unity_p = sub.add_parser("unity", help="Manage Unity packages")
    unity_sub = unity_p.add_subparsers(dest="unity_command", required=True)

    # unity create
    create_p = unity_sub.add_parser("create", help="Create a new Unity package")
    create_p.add_argument("name", help="PascalCase package name, e.g. Utils"
        ).completer = lambda prefix, **kw: []
    create_p.add_argument("--runtime", nargs="+", default=[], metavar="PATH"
        ).completer = FilesCompleter()
    create_p.add_argument("--editor", nargs="+", default=[], metavar="PATH"
        ).completer = FilesCompleter()
    
    # unity start
    unity_sub.add_parser("start", help="Starts the unity executuble specified in the config file")

    # unity dir
    struct_p = unity_sub.add_parser("dir", help="Display folder (and optionally file) tree structure of a Unity package")
    struct_p.add_argument("name", help="Package name (folder under unity_root)").completer = package_name_completer
    struct_p.add_argument("--files", action="store_true", dest="with_files", help="Include individual file names in the tree view")

    # unity delete
    delete_p = unity_sub.add_parser("delete", help="Delete a Unity package")
    delete_p.add_argument("name", help="Package name to delete").completer = package_name_completer

    # unity add-files
    add_p = unity_sub.add_parser("add-files", help="Add files to an existing Unity package")
    add_p.add_argument("name", help="Package name").completer = package_name_completer
    add_p.add_argument("--runtime", nargs="+", default=[], metavar="PATH"
        ).completer = FilesCompleter()
    add_p.add_argument("--editor", nargs="+", default=[], metavar="PATH"
        ).completer = FilesCompleter()

    # unity remove-files
    rm_p = unity_sub.add_parser("remove-files", help="Remove files from a Unity package")
    rm_p.add_argument("name", help="Package name").completer = package_name_completer
    rm_p.add_argument("--runtime", nargs="+", default=[], metavar="PATH",
                      help="File names (relative to Runtime/) to remove"
        ).completer = FilesCompleter()
    rm_p.add_argument("--editor", nargs="+", default=[], metavar="PATH",
                      help="File names (relative to Editor/) to remove"
        ).completer = FilesCompleter()

    # unity list
    unity_sub.add_parser("list", help="List all Unity packages")

    return parser


def get_library(parsed_args) -> Optional[str]:
    # 1. Explicit --repo flag (matches resolve_repo_path priority)
        if hasattr(parsed_args, 'repo') and parsed_args.repo:
            return parsed_args.repo
        else:
            # 2. Path from terminal location
            cwd = Path.cwd()
            if (cwd / ".libmanrc").exists() or (cwd / ".git").is_dir():
                return str(cwd)
            # 3. Globally focused library
            else:
                return get_focused_library()

def do_visit(args, cfg):
    if args.copy:
      pyperclip.copy(cfg.root)
      print(f"copied {cfg.root} to clipboard")
      return
    if args.dry_run:
      print(f"should cd to {cfg.root}" )
    else:
        print(cfg.root) # code in $PROFILE to handle this command specifically 
    

def main():
    parser = build_parser()
    argcomplete.autocomplete(parser, exclude=['-h', '--help']) # code in $PROFILE to initialize autocomplete for each terminal session
    args = parser.parse_args()

    # focus is independent, doesn't need a repo
    if args.command == "focus":
        set_focused_library(args.path)
        return

    # Now resolve repo path – needed for init and unity commands
    repo_path = get_library(args)
    if(not repo_path):
        print("ERROR: Could not determine which library to manage.", file=sys.stderr)
        print("Please do one of the following:", file=sys.stderr)
        print("  a) 'cd' into your library's directory", file=sys.stderr)
        print("  b) Run 'libman focus /path/to/my/lib' once", file=sys.stderr)
        print("  c) Append '--repo /path/to/my/lib' to your command", file=sys.stderr)
        sys.exit(1)
        return

    if args.command == "init":
        create_config(repo_path, force_create=True)
        setup_powershell_autocomplete()
        return
    cfg = get_valid_library(repo_path)
    dry_run = args.dry_run
    use_git = not args.no_git
    if(args.command == "visit"):
        do_visit(args, cfg)
        return
    
    # unity list is read‑only
    if args.command == "unity":
        if args.unity_command == "list":
            cmd_unity_list(cfg)
            return
        elif args.unity_command == "dir":
            cmd_unity_structure(cfg, None, args.name, args.with_files, dry_run)
            return
        elif args.unity_command == "start":
            cmd_run_unity(cfg)
            return

    # All mutating commands use GitContext
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