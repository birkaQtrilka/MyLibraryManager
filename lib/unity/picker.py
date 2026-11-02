"""
Interactive fuzzy picker for the terminal (Windows console / PowerShell).

  type            filter live
  Up/Down         move          PgUp/PgDn  jump
  Tab             toggle multi-select
  Enter           open the action menu for the selection
  Esc             quit

Dependency-free: uses msvcrt for key input and ANSI codes for drawing.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

import pyperclip

from lib.unity.pull import copy_paths
from lib.unity.search import SearchResult, build_index, cmd_unity_find, rank

try:
    import msvcrt  # Windows only
except ImportError:
    msvcrt = None

DIM, BOLD, REV, RESET = "\x1b[2m", "\x1b[1m", "\x1b[7m", "\x1b[0m"
VISIBLE_ROWS = 12


def is_supported() -> bool:
    return msvcrt is not None and sys.stdin.isatty() and sys.stdout.isatty()


# ------------------------------------------------------------------ terminal

def _read_key() -> str:
    """Returns 'up','down','pgup','pgdn','enter','esc','backspace','tab' or a single char."""
    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):  # special-key prefix
        return {"H": "up", "P": "down", "I": "pgup", "Q": "pgdn"}.get(msvcrt.getwch(), "")
    if ch == "\r":
        return "enter"
    if ch == "\x1b":
        return "esc"
    if ch in ("\x08", "\x7f"):
        return "backspace"
    if ch == "\t":
        return "tab"
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch if ch.isprintable() else ""


class _Region:
    """Redraws a block of lines in place."""

    def __init__(self):
        os.system("")  # turns on ANSI escape handling in the Windows console
        self.height = 0

    def draw(self, lines: list[str]) -> None:
        width = shutil.get_terminal_size().columns - 1
        lines = [self._fit(l, width) for l in lines]
        out = ""
        if self.height:
            out += f"\x1b[{self.height}A"
        out += "\r\x1b[J" + "\n".join(lines) + "\n"
        sys.stdout.write(out)
        sys.stdout.flush()
        self.height = len(lines)

    def clear(self) -> None:
        if self.height:
            sys.stdout.write(f"\x1b[{self.height}A\r\x1b[J")
            sys.stdout.flush()
            self.height = 0

    @staticmethod
    def _fit(line: str, width: int) -> str:
        # Only truncate plain lines; styled lines are kept short by construction
        if "\x1b" not in line and len(line) > width:
            return line[: width - 1] + "…"
        return line


def _window(cursor: int, top: int, total: int) -> int:
    if cursor < top:
        top = cursor
    elif cursor >= top + VISIBLE_ROWS:
        top = cursor - VISIBLE_ROWS + 1
    return max(0, min(top, max(0, total - VISIBLE_ROWS)))


# ------------------------------------------------------------------ widgets

def pick_files(index: list[SearchResult], query: str = "") -> tuple[Optional[list[SearchResult]], str]:
    """Live fuzzy picker. Returns (chosen results or None if cancelled, final query)."""
    region = _Region()
    cursor, top = 0, 0
    selected: dict[Path, SearchResult] = {}

    try:
        while True:
            matches = rank(index, query, 500)
            cursor = max(0, min(cursor, len(matches) - 1))
            top = _window(cursor, top, len(matches))

            lines = [
                f"{BOLD}find>{RESET} {query}",
                f"{DIM}  {len(matches)}/{len(index)} files · {len(selected)} selected{RESET}",
            ]
            for i in range(top, min(top + VISIBLE_ROWS, len(matches))):
                m = matches[i]
                mark = "*" if m.abs_path in selected else " "
                text = f" {mark} [{m.package}] {m.rel_path}"
                lines.append(f"{REV}>{text}{RESET}" if i == cursor else f" {text}")
            if not matches:
                lines.append(f"{DIM}  no matches{RESET}")
            lines.append(f"{DIM}  ↑↓ move · Tab select · Enter actions · Esc quit{RESET}")
            region.draw(lines)

            key = _read_key()
            if key == "esc":
                return None, query
            elif key == "enter":
                if selected:
                    return list(selected.values()), query
                if matches:
                    return [matches[cursor]], query
            elif key == "up":
                cursor -= 1
            elif key == "down":
                cursor += 1
            elif key == "pgup":
                cursor -= VISIBLE_ROWS
            elif key == "pgdn":
                cursor += VISIBLE_ROWS
            elif key == "tab" and matches:
                p = matches[cursor].abs_path
                if p in selected:
                    del selected[p]
                else:
                    selected[p] = matches[cursor]
                cursor += 1
            elif key == "backspace":
                query = query[:-1]
                cursor = top = 0
            elif len(key) == 1:
                query += key
                cursor = top = 0
    finally:
        region.clear()


def pick_action(title: str, labels: list[str]) -> Optional[int]:
    """Small arrow-key menu. Returns the chosen index, or None on Esc."""
    region = _Region()
    cursor = 0
    try:
        while True:
            lines = [f"{BOLD}{title}{RESET}"]
            for i, label in enumerate(labels):
                lines.append(f"{REV}> {label}{RESET}" if i == cursor else f"  {label}")
            lines.append(f"{DIM}  ↑↓ move · Enter confirm · Esc back{RESET}")
            region.draw(lines)

            key = _read_key()
            if key == "esc":
                return None
            elif key == "enter":
                return cursor
            elif key == "up":
                cursor = (cursor - 1) % len(labels)
            elif key == "down":
                cursor = (cursor + 1) % len(labels)
    finally:
        region.clear()


# ------------------------------------------------------------------ actions

def _copy_here(res: list[SearchResult], dest: Path, dry_run: bool) -> None:
    n = copy_paths([r.abs_path for r in res], dest, dry_run=dry_run)
    print(f"  {n} file(s) {'would be ' if dry_run else ''}copied to {dest}")


def _copy_abs_path(res: list[SearchResult], dest: Path, dry_run: bool) -> None:
    pyperclip.copy("\n".join(str(r.abs_path) for r in res))
    print(f"  copied {len(res)} path(s) to clipboard")


def _copy_rel_path(res: list[SearchResult], dest: Path, dry_run: bool) -> None:
    pyperclip.copy("\n".join(f"{r.package}/{r.rel_path}" for r in res))
    print(f"  copied {len(res)} package-relative path(s) to clipboard")


def _show_in_explorer(res: list[SearchResult], dest: Path, dry_run: bool) -> None:
    for r in res[:5]:  # avoid spawning a flood of windows
        subprocess.run(["explorer", f"/select,{r.abs_path}"])  # explorer always returns 1


def _open_file(res: list[SearchResult], dest: Path, dry_run: bool) -> None:
    for r in res[:5]:
        os.startfile(r.abs_path)


ACTIONS: list[tuple[str, Callable]] = [
    ("Copy to current directory", _copy_here),
    ("Copy full path to clipboard", _copy_abs_path),
    ("Copy package-relative path to clipboard", _copy_rel_path),
    ("Show in Explorer", _show_in_explorer),
    ("Open with default app", _open_file),
]


# ------------------------------------------------------------------ command

def cmd_unity_browse(cfg, query: str, package: Optional[str], dest: Path, dry_run: bool) -> None:
    if not is_supported():
        if query:
            print("Interactive mode needs a Windows terminal; showing a plain list instead.")
            cmd_unity_find(cfg, query, package, 20, False, dest, dry_run)
        else:
            print("ERROR: interactive mode needs a Windows terminal. Pass a query instead.", file=sys.stderr)
        return

    index = build_index(cfg.unity_root, package)
    if not index:
        print("No files found in the library.")
        return

    while True:
        chosen, query = pick_files(index, query)
        if chosen is None:
            return

        names = chosen[0].rel_path if len(chosen) == 1 else f"{len(chosen)} files"
        choice = pick_action(f"{names}:", [label for label, _ in ACTIONS])
        if choice is None:
            continue  # back to the picker, keeping the query

        ACTIONS[choice][1](chosen, dest, dry_run)