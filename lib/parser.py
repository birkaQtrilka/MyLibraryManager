
import argparse

from lib.autocomplete import package_name_completer
from lib.recursive_help_formatter import RecursiveHelpFormatter
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

    u_visit_p = unity_sub.add_parser("visit", help="Visit a Unity package")
    u_visit_p.add_argument("name", help="Package name (folder under unity_root)").completer = package_name_completer
    u_visit_p.add_argument("--copy", action="store_true", help="Copies to clipboard instead of visiting there")

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