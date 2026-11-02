"""
Fuzzy file search across all packages in the library (no external deps).

Scoring is fzf-like: query characters must appear in order; consecutive
matches, word/camelCase boundaries and filename matches score higher.
Multiple space-separated tokens must ALL match.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lib.unity.pull import SKIP_DIRS, copy_paths

_SEPARATORS = "/\\_-. "


@dataclass
class SearchResult:
    package: str
    rel_path: str      # relative to the package root, posix style
    abs_path: Path
    score: float


# ------------------------------------------------------------------ scoring

def _is_boundary(text: str, i: int) -> bool:
    if i == 0 or text[i - 1] in _SEPARATORS:
        return True
    return text[i].isupper() and text[i - 1].islower()  # camelCase


def fuzzy_score(query: str, text: str) -> Optional[float]:
    """Score `query` against `text`; None if it is not a subsequence match."""
    q, t = query.lower(), text.lower()
    if not q:
        return 0.0

    score = 0.0
    pos = 0        # where to resume scanning
    prev = -2      # index of previous matched char

    for ch in q:
        first = t.find(ch, pos)
        if first == -1:
            return None

        # Prefer a consecutive or boundary hit over a random earlier one
        chosen = first
        k = first
        while k != -1:
            if k == prev + 1 or _is_boundary(text, k):
                chosen = k
                break
            k = t.find(ch, k + 1)

        score += 10
        if chosen == prev + 1:
            score += 15
        if _is_boundary(text, chosen):
            score += 10
        score -= min(chosen - pos, 5)   # small gap penalty

        prev = chosen
        pos = chosen + 1

    if t.startswith(q):
        score += 20
    return score - len(text) * 0.1       # prefer shorter paths on ties


def score_path(query: str, rel_path: str) -> Optional[float]:
    """Every whitespace-separated token must match; filename matches count double."""
    name = rel_path.rsplit("/", 1)[-1]
    total = 0.0
    for token in query.split():
        s_name = fuzzy_score(token, name)
        s_path = fuzzy_score(token, rel_path)
        if s_name is None and s_path is None:
            return None
        total += max(s_name * 2 if s_name is not None else -1e9, s_path if s_path is not None else -1e9)
    return total


# ------------------------------------------------------------------ indexing

def iter_package_files(unity_root: Path, package: Optional[str] = None):
    """Yield (package_name, package_dir, file_path) for every non-.meta file."""
    if not unity_root.is_dir():
        return
    for pkg_dir in sorted(p for p in unity_root.iterdir() if p.is_dir()):
        if package and pkg_dir.name != package:
            continue
        for dirpath, dirnames, filenames in os.walk(pkg_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(".meta"):
                    continue
                yield pkg_dir.name, pkg_dir, Path(dirpath) / fn


def build_index(unity_root: Path, package: Optional[str] = None) -> list[SearchResult]:
    """Walk the library once; reuse the result for many queries."""
    return [
        SearchResult(pkg_name, f.relative_to(pkg_dir).as_posix(), f, 0.0)
        for pkg_name, pkg_dir, f in iter_package_files(unity_root, package)
    ]


def rank(index: list[SearchResult], query: str, limit: int = 20) -> list[SearchResult]:
    """Score every entry against `query`. An empty query returns the index in order."""
    if not query.strip():
        return index[:limit]
    results = []
    for entry in index:
        s = score_path(query, entry.rel_path)
        if s is not None:
            results.append(SearchResult(entry.package, entry.rel_path, entry.abs_path, s))
    results.sort(key=lambda r: -r.score)
    return results[:limit]


def search(unity_root: Path, query: str, package: Optional[str] = None, limit: int = 20) -> list[SearchResult]:
    return rank(build_index(unity_root, package), query, limit)


# ------------------------------------------------------------------- command

def cmd_unity_find(
    cfg,
    query: str,
    package: Optional[str],
    limit: int,
    pull: bool,
    dest: Path,
    dry_run: bool,
) -> None:
    results = search(cfg.unity_root, query, package, limit)

    if not results:
        print(f"No files matching '{query}'.")
        return

    width = len(str(len(results)))
    print()
    for i, r in enumerate(results, 1):
        print(f"  {str(i).rjust(width)}. [{r.package}] {r.rel_path}")
    print()

    if not pull:
        return

    raw = input(f"Copy to {dest}? Enter number(s) (e.g. 1 3), or press Enter to skip: ").strip()
    if not raw:
        return

    picked = []
    for tok in re.split(r"[,\s]+", raw):
        if tok.isdigit() and 1 <= int(tok) <= len(results):
            picked.append(results[int(tok) - 1].abs_path)
        else:
            print(f"  WARNING: ignoring invalid selection '{tok}'", file=sys.stderr)

    if picked:
        n = copy_paths(picked, dest, dry_run=dry_run)
        print(f"Done. {n} file(s) {'would be ' if dry_run else ''}copied.\n")