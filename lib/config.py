"""
Config management — reads/writes .libmanrc (JSON) at the repo root.

Example .libmanrc:
{
    "author_name": "Stefan Carpeliuc",
    "author_email": "stefan@example.com",
    "package_prefix": "com.steph",
    "assembly_prefix": "steph",
    "unity_version": "6000",
    "unity_folder": "Unity",
    "remote": "origin",
    "branch": "main"
}
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional
CONFIG_FILENAME = ".libmanrc"

DEFAULTS: dict[str, Any] = {
    "author_name": "Stefan Carpeliuc",
    "author_email": "",
    "package_prefix": "com.steph",
    "assembly_prefix": "steph",
    "unity_version": "6000",
    "unity_folder": "Unity",
    "remote": "origin",
    "branch": "main",
    "unity_exe_path": "C:/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe"
}

GLOBAL_CONFIG_PATH = Path.home() / ".libman_global.json"

def set_focused_library(path: str):
    """Saves the target library path globally on this machine."""
    target = Path(path).resolve()
    
    if not target.is_dir():
        print(f"ERROR: Directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    if not (target / ".git").is_dir():
        print(f"WARNING: '{target}' is not a git repository. You might need to run 'git init' there.")
        
    GLOBAL_CONFIG_PATH.write_text(json.dumps({"currentFocusedLibrary": str(target)}, indent=4))
    print(f"Focused library set to: {target}")

def get_focused_library() -> Optional[str]:
    """Reads the globally focused library path, if it exists."""
    if GLOBAL_CONFIG_PATH.exists():
        try:
            data = json.loads(GLOBAL_CONFIG_PATH.read_text())
            return data.get("currentFocusedLibrary")
        except json.JSONDecodeError:
            pass
    return None



class Config:
    def __init__(self, data: dict[str, Any], root: Path):
        self._data = data
        self.root = root

    def __getattr__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"Config has no key '{key}'")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def unity_root(self) -> Path:
        return self.root / self._data["unity_folder"]


def load_config(repo_path: str) -> Config:
    root = Path(repo_path).resolve()
    
    if not (root / ".git").is_dir():
        print(f"ERROR: '{root}' is not a git repository. Run 'git init' there first.", file=sys.stderr)
        sys.exit(1)

    config_path = root / CONFIG_FILENAME

    try:
        data = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: Malformed {CONFIG_FILENAME}: {e}", file=sys.stderr)
        sys.exit(1)

    # Fill in any keys missing from older config files
    updated = False
    for key, default in DEFAULTS.items():
        if key not in data:
            data[key] = default
            updated = True
    if updated:
        config_path.write_text(json.dumps(data, indent=4) + "\n")

    return Config(data, root)

def config_exists(repo_path: str) -> Config:
    root = Path(repo_path).resolve()
    config_path = root / CONFIG_FILENAME
    return config_path.exists()

def create_config(repo_path: str) -> Config:
    root = Path(repo_path).resolve()
    config_path = root / CONFIG_FILENAME
        
    if config_path.exists() :
        print(f"Config already exists at {config_path}. Overwrite? [y/N] ", end="")
        if input().strip().lower() != "y":
            print("Aborted.")
            sys.exit(0)
    print(f"Creating {CONFIG_FILENAME} at {root}")
    print("Press Enter to accept defaults shown in [brackets]. or 'q' to cancel \n")

    try: 
        data: dict[str, Any] = {}
        for key, default in DEFAULTS.items():
            prompt = f"  {key} [{default}]: " if default else f"  {key}: "
            val = input(prompt).strip()
            if val == 'q':
              print(f"Canceled")
              sys.exit(1)
            data[key] = val if val else default    
    except NameError as e:
        print(f"Canceled: {e}", file=sys.stderr)
        sys.exit(1)
    
    config_path.write_text(json.dumps(data, indent=4) + "\n")
    print(f"\nSaved to {config_path}\n")
    return Config(data, root)

def get_valid_library(repo_path: str) -> Config:
    if config_exists(repo_path):
        return load_config(repo_path)
    print(f"> There is no config file at path: {repo_path}")
    print("> You need to run 'libman init' to initialize library")
    print("\tTrying to get focused library...")
    repo_path = get_focused_library()
    if(config_exists(repo_path)): return load_config(repo_path)
    print("\tERROR: No focused library. run 'libman' focus while in an initialized library to focus", file=sys.stderr)
    sys.exit(1)

def get_valid_library_path(repo_path) -> str:
    if config_exists(repo_path):
        return repo_path
    repo_path = get_focused_library()
    if(config_exists(repo_path)): return repo_path
    print("\tERROR: No focused library. run 'libman' focus while in an initialized library to focus", file=sys.stderr)
    sys.exit(1)

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