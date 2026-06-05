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
    cmd_unity_structure,
)


# ---------- Custom formatter to show nested subcommands ----------
class RecursiveHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Shows subcommands of subcommands in the main help output."""
    def _format_action(self, action):
        # For a subparsers action, we walk through its subparsers and
        # recursively show their subcommands as well.
        if isinstance(action, argparse._SubParsersAction):
            parts = []
            # Header line (e.g., "positional arguments:")
            parts.append(self._format_action_invocation(action))
            parts.append('')
            # Get the dict of subparsers: name -> ArgumentParser
            subparsers = action._name_parser_map
            for name, subparser in sorted(subparsers.items()):
                # Show subcommand name and its short help
                help_line = f"  {name:<15} {subparser.description or ''}"
                parts.append(help_line)
                # If this subparser itself has subparsers, repeat the process
                sub_actions = [a for a in subparser._actions if isinstance(a, argparse._SubParsersAction)]
                if sub_actions:
                    for sub_action in sub_actions:
                        sub_subparsers = sub_action._name_parser_map
                        for sub_name, sub_subparser in sorted(sub_subparsers.items()):
                            sub_help = f"    {sub_name:<13} {sub_subparser.description or ''}"
                            parts.append(sub_help)
                parts.append('')
            return '\n'.join(parts)
        return super()._format_action(action)


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

    # focus
    focus_p = sub.add_parser("focus", help="Remember a library path so you don't have to use --repo")
    focus_p.add_argument("path", help="Absolute or relative path to the library repository")

    # init
    sub.add_parser("init", help="Create a .libmanrc config file in the repo root")

    # unity
    unity_p = sub.add_parser("unity", help="Manage Unity packages")
    unity_sub = unity_p.add_subparsers(dest="unity_command", required=True)

    # unity create
    create_p = unity_sub.add_parser("create", help="Create a new Unity package")
    create_p.add_argument("name", help="PascalCase package name, e.g. Utils")
    create_p.add_argument("--runtime", nargs="*", default=[], metavar="PATH")
    create_p.add_argument("--editor", nargs="*", default=[], metavar="PATH")

    # unity structure
    struct_p = unity_sub.add_parser("dir", help="Display folder (and optionally file) tree structure of a Unity package")
    struct_p.add_argument("name", help="Package name (folder under unity_root)")
    struct_p.add_argument("--files", action="store_true", dest="with_files",help="Include individual file names in the tree view")

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
    if args.repo:
        return args.repo
    cwd = Path.cwd()
    if (cwd / ".libmanrc").exists() or (cwd / ".git").is_dir():
        return str(cwd)
    focused = get_focused_library()
    if focused and Path(focused).exists():
        return focused
    print("ERROR: Could not determine which library to manage.", file=sys.stderr)
    print("Please do one of the following:", file=sys.stderr)
    print("  a) 'cd' into your library's directory", file=sys.stderr)
    print("  b) Run 'libman focus /path/to/my/lib' once", file=sys.stderr)
    print("  c) Append '--repo /path/to/my/lib' to your command", file=sys.stderr)
    sys.exit(1)


def main():
    parser = build_parser()
    args = parser.parse_args()

    # focus is independent, doesn't need a repo
    if args.command == "focus":
        set_focused_library(args.path)
        return

    # Now resolve repo path – needed for init and unity commands
    repo_path = resolve_repo_path(args)

    if args.command == "init":
        load_or_create_config(repo_path, force_create=True)
        return

    cfg = load_or_create_config(repo_path)
    dry_run = args.dry_run
    use_git = not args.no_git

    # unity list is read‑only
    if args.command == "unity":
        if args.unity_command == "list":
            cmd_unity_list(cfg)
            return
        elif args.unity_command == "dir":
            cmd_unity_structure(cfg, None, args.name, args.with_files, dry_run)
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