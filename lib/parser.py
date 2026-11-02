
import argparse

from lib.autocomplete import file_completer, package_files_completer, package_name_completer
from lib.recursive_help_formatter import RecursiveHelpFormatter
from lib.unity.pull import package_item_completer

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="libman",
        description="Monorepo package manager",
        formatter_class=RecursiveHelpFormatter,
        epilog="""
Examples:

  > libman focus /path/to/repo
  > libman unity create MyPackage --runtime Assets/Scripts/MyRuntime.cs --editor Assets/Editor/MyEditor.cs
  Run 'libman examples' for more examples and common workflows.
"""
    )
    parser.add_argument(
        "--repo", default=None,
        help="Path to the target library repository (overrides focused library)"
    )
    parser.add_argument("--dry-run", action="store_true", help="goes through each step only describing operations")
    parser.add_argument("--no-git", action="store_true", help="does not commit changes made to the library")
    

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "examples",
        help="Show common workflows and example commands"
    )

    # focus
    focus_p = sub.add_parser("focus", help="Remember a library path so you don't have to use --repo")
    focus_p.add_argument("path", help="Absolute or relative path to the library repository")

    # visit
    visit_p = sub.add_parser("visit", help="Go to the focused library")
    visit_p.add_argument("--copy", action="store_true", help="Copies to clipboard instead of visiting there")

    # init
    sub.add_parser("init", help="Create a .libmanrc config file in the repo root")

    # commit
    sub.add_parser("commit", help="Manually commits all changes")

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
        ).completer = file_completer
    create_p.add_argument("--editor", nargs="+", default=[], metavar="PATH"
        ).completer = file_completer
    
    # unity start
    unity_sub.add_parser("start", help="Starts the unity executuble specified in the config file")

    # unity dir
    struct_p = unity_sub.add_parser("dir", help="Display folder (and optionally file) tree structure of a Unity package")
    struct_p.add_argument("name", help="Package name (folder under unity_root)").completer = package_name_completer
    struct_p.add_argument("--files", action="store_true", dest="with_files", help="Include individual file names in the tree view")

    git_link_p = unity_sub.add_parser("gitl", help="Copy git link to clipboard, so you can easily add the package in unity")
    git_link_p.add_argument("name", help="Package name (folder under unity_root)").completer = package_name_completer

    # unity delete
    delete_p = unity_sub.add_parser("delete", help="Delete a Unity package")
    delete_p.add_argument("name", help="Package name to delete").completer = package_name_completer

    # unity add-files
    add_p = unity_sub.add_parser("add-files", help="Add files to an existing Unity package")
    add_p.add_argument("name", help="Package name").completer = package_name_completer
    add_p.add_argument("--runtime", nargs="+", default=[], metavar="PATH"
        ).completer = file_completer
    add_p.add_argument("--editor", nargs="+", default=[], metavar="PATH"
        ).completer = file_completer

    # unity remove-files
    rm_p = unity_sub.add_parser("remove-files", help="Remove files from a Unity package")
    rm_p.add_argument("name", help="Package name").completer = package_name_completer
    rm_p.add_argument("--runtime", nargs="+", default=[], metavar="PATH",
                      help="File names (relative to Runtime/) to remove"
        ).completer = package_files_completer
    rm_p.add_argument("--editor", nargs="+", default=[], metavar="PATH",
                      help="File names (relative to Editor/) to remove"
        ).completer = package_files_completer

        # unity pull  (copy files/dirs out of a package into the current directory)
    pull_p = unity_sub.add_parser("pull", help="Copy files/directories from a package into the current directory")
    pull_p.add_argument("name", help="Package name").completer = package_name_completer
    pull_p.add_argument("items", nargs="*", metavar="PATH",
                        help="Files/dirs relative to the package root, or a bare name to search for. "
                             "Omit to copy the whole package."
        ).completer = package_item_completer
    pull_p.add_argument("--flat", action="store_true", help="Copy a directory's contents directly, without the directory itself")
    pull_p.add_argument("--force", action="store_true", help="Overwrite existing files")
    pull_p.add_argument("--meta", action="store_true", help="Also copy Unity .meta files")

    # unity find  (fuzzy search across all packages)
    find_p = unity_sub.add_parser("find", help="Fuzzy-search files across all packages")
    find_p.add_argument("query", nargs="*", help="Search terms; omit to open the interactive picker")
    find_p.add_argument("-i", "--interactive", action="store_true", help="Open the interactive picker (default when no query is given)")
    find_p.add_argument("-p", "--package", default=None, help="Limit search to one package").completer = package_name_completer
    find_p.add_argument("-n", "--limit", type=int, default=20, help="Max results (default 20)")
    find_p.add_argument("--pull", action="store_true", help="Pick results to copy into the current directory")

    # unity list
    unity_sub.add_parser("list", help="List all Unity packages")

    return parser