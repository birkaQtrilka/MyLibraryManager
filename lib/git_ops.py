"""
Git operations — wraps all mutating commands in a safe pull→work→commit→push flow.

Flow:
  1. Check for uncommitted/unstaged files → ask to commit first (if any)
  2. git pull --rebase (fail fast if remote has diverged)
  3. git stash (save any pre-existing dirty state)
  4. yield (caller does its work)
  5. git add -A
  6. git commit -m <message>   (called explicitly by the caller)
  7. git push
  8. git stash pop             (restore pre-existing dirty state)

If anything fails after the work phase the context manager attempts to restore
the repo to the pre-operation state (stash pop + reset).
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from lib.config import Config


class GitError(Exception):
    pass


def _run(args: list[str], cwd: Path, capture: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() if capture else ""
        cmd = " ".join(args)
        raise GitError(f"Command failed: {cmd}\n{stderr}".strip())
    return result


class GitContext:
    """
    Context manager for git-safe mutating operations.

    Usage:
        with GitContext(cfg, dry_run=False) as git:
            # do file work here
            git.commit("feat: my message")
    """

    def __init__(self, cfg: Config, dry_run: bool = False, enabled: bool = True):
        self.cfg = cfg
        self.root = cfg.root
        self.remote = cfg.remote
        self.branch = cfg.branch
        self.dry_run = dry_run
        self.enabled = enabled
        self._stashed = False
        self._committed = False

    # ── public API ────────────────────────────────────────────────────────────

    def commit(self, message: str) -> None:
        """Stage all changes and create a commit. Called by the command after its work."""
        if not self.enabled or self.dry_run:
            print(f"[dry-run] Would commit: {message}")
            return
        print(f"  git add -A")
        _run(["git", "add", "-A"], cwd=self.root)
        print(f"  git commit -m '{message}'")
        try:
            _run(["git", "commit", "-m", message], cwd=self.root)
        except GitError:
            # Nothing to commit is not a real error
            print("  (nothing to commit)")
        self._committed = True

    # ── context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "GitContext":
        if not self.enabled:
            return self
        if self.dry_run:
            print("[dry-run] Would: check for uncommitted changes, then git pull --rebase")
            return self

        # Handle uncommitted/unstaged changes before pulling
        self._check_and_handle_dirty_state()

        self._pull()
        self._stash_save()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if not self.enabled:
            return False  # don't suppress exceptions

        if exc_type is not None:
            # Something went wrong — roll back
            print(f"\nERROR: {exc_val}", file=sys.stderr)
            self._rollback()
            print("Operation cancelled. Repository restored.", file=sys.stderr)
            sys.exit(1)

        if self.dry_run:
            print("[dry-run] Would: git push")
            return False

        if self._committed:
            self._push()

        self._stash_pop()
        return False

    # ── private helpers ───────────────────────────────────────────────────────

    def _check_and_handle_dirty_state(self) -> None:
        """Detect uncommitted/unstaged files and optionally commit them before pull."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.root, capture_output=True, text=True,
        )
        dirty = result.stdout.strip()
        if not dirty:
            return

        print("\nUncommitted or unstaged changes detected:")
        # Show a friendly list of changed files
        for line in dirty.splitlines():
            status = line[:2]
            file = line[3:]
            print(f"  {status} {file}")

        print()
        answer = input("Do you want to commit these changes before pulling? (y/n): ").strip().lower()
        if answer != 'y':
            print("Aborting operation. Please commit or stash your changes manually.", file=sys.stderr)
            sys.exit(1)

        # Ask for a commit message
        msg = input("Enter commit message (or press Enter for 'Pre-pull commit'): ").strip()
        if not msg:
            msg = "Pre-pull commit"

        print(f"  git add -A")
        _run(["git", "add", "-A"], cwd=self.root)
        print(f"  git commit -m '{msg}'")
        try:
            _run(["git", "commit", "-m", msg], cwd=self.root)
        except GitError as e:
            print(f"ERROR: Failed to commit changes: {e}", file=sys.stderr)
            sys.exit(1)

        print("Committed successfully. Continuing with pull.\n")

    def _pull(self) -> None:
        print(f"  git pull --rebase {self.remote} {self.branch}")
        try:
            _run(["git", "pull", "--rebase", self.remote, self.branch], cwd=self.root)
        except GitError as e:
            print(f"ERROR: Pull failed — resolve conflicts first.\n{e}", file=sys.stderr)
            sys.exit(1)

    def _stash_save(self) -> None:
        # Only stash if there is something dirty
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.root, capture_output=True, text=True,
        )
        if result.stdout.strip():
            print("  git stash (saving existing changes)")
            _run(["git", "stash", "push", "-m", "libman: pre-operation stash"], cwd=self.root)
            self._stashed = True

    def _stash_pop(self) -> None:
        if self._stashed:
            print("  git stash pop (restoring previous changes)")
            try:
                _run(["git", "stash", "pop"], cwd=self.root)
            except GitError as e:
                print(f"WARNING: Could not pop stash automatically: {e}", file=sys.stderr)
                print("Run 'git stash pop' manually.", file=sys.stderr)

    def _push(self) -> None:
        print(f"  git push {self.remote} {self.branch}")
        try:
            _run(["git", "push", self.remote, self.branch], cwd=self.root)
        except GitError as e:
            print(f"ERROR: Push failed.\n{e}", file=sys.stderr)
            print("Your commit is local. Resolve the issue and push manually.", file=sys.stderr)
            self._stash_pop()
            sys.exit(1)

    def _rollback(self) -> None:
        """Best-effort rollback to pre-operation state."""
        print("  Rolling back changes...", file=sys.stderr)
        try:
            _run(["git", "reset", "--hard", "HEAD"], cwd=self.root)
        except GitError:
            pass
        self._stash_pop()