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
import os
import sys
import pyperclip
from pathlib import Path
from typing import Optional
from lib.autocomplete import setup_powershell_autocomplete
from lib.config import create_config, get_valid_library, set_focused_library, get_focused_library
from lib.git_ops import GitContext
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
from lib.parser import build_parser

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

def do_visit(args, path):
    if args.copy:
      pyperclip.copy(path)
      print(f"copied {path} to clipboard")
      return
    if args.dry_run:
      print(f"should cd to {path}" )
    else:
        print(path) # code in $PROFILE to handle this command specifically 
    

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
        do_visit(args, cfg.root)
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
        elif args.unity_command == "visit":
            do_visit(args, os.path.join(cfg.unity_root, args.name) )
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