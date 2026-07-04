"""
Unity naming conventions and JSON template generators.

All values are derived from a single PascalCase package name and the config.
"""

import json
from dataclasses import dataclass
from lib.config import Config


@dataclass
class UnityNames:
    """All derived identifiers for a Unity package."""
    name: str                 # raw PascalCase input, e.g. "Utils"
    folder_name: str          # "Utils"
    package_id: str           # "com.steph.unity.utils"
    display_name: str         # "Stefan's Utils"
    assembly_runtime: str     # "steph.Unity.Utils.Runtime"
    assembly_editor: str      # "steph.Unity.Utils.Editor"
    namespace_runtime: str    # "steph.Unity.Utils.Runtime"
    namespace_editor: str     # "steph.Unity.Utils.Editor"
    asmdef_runtime_file: str  # "steph.Unity.Utils.Runtime.asmdef"
    asmdef_editor_file: str   # "steph.Unity.Utils.Editor.asmdef"


def derive_names(cfg: Config, name: str) -> UnityNames:
    slug = name.lower()
    prefix_pkg = cfg.package_prefix       # e.g. "com.steph"
    prefix_asm = cfg.assembly_prefix      # e.g. "steph"
    author = cfg.author_name              # e.g. "Stefan Carpeliuc"
    first_name = author.split()[0]        # "Stefan"

    pkg_id = f"{prefix_pkg}.unity.{slug}"
    display = f"{first_name}'s {name}"
    asm_runtime = get_asm_runtime_name(cfg, name)
    asm_editor = get_asm_editor_name(cfg, name)

    return UnityNames(
        name=name,
        folder_name=name,
        package_id=pkg_id,
        display_name=display,
        assembly_runtime=asm_runtime,
        assembly_editor=asm_editor,
        namespace_runtime=asm_runtime,
        namespace_editor=asm_editor,
        asmdef_runtime_file=f"{asm_runtime}.asmdef",
        asmdef_editor_file=f"{asm_editor}.asmdef",
    )

def get_asm_runtime_name(cfg: Config, name: str) -> str:
  return f"{cfg.assembly_prefix}.Unity.{name}.Runtime"

def get_asm_editor_name(cfg: Config, name: str) -> str:
  return f"{cfg.assembly_prefix}.Unity.{name}.Editor"

# ── JSON template builders ────────────────────────────────────────────────────

def make_package_json(cfg: Config, names: UnityNames) -> str:
    doc = {
        "name": names.package_id,
        "version": "0.0.0",
        "displayName": names.display_name,
        "description": f"The {names.name} package.",
        "unity": cfg.unity_version,
        "author": {
            "name": cfg.author_name,
        },
    }
    if cfg.author_email:
        doc["author"]["email"] = cfg.author_email  # type: ignore[index]
    return json.dumps(doc, indent=4) + "\n"


def make_runtime_asmdef(names: UnityNames) -> str:
    doc = {
        "name": names.assembly_runtime,
        "rootNamespace": names.namespace_runtime,
        "references": [],
        "includePlatforms": [],
        "excludePlatforms": [],
        "allowUnsafeCode": False,
        "overrideReferences": False,
        "precompiledReferences": [],
        "autoReferenced": True,
        "defineConstraints": [],
        "versionDefines": [],
        "noEngineReferences": False,
    }
    return json.dumps(doc, indent=4) + "\n"


def make_editor_asmdef(names: UnityNames) -> str:
    doc = {
        "name": names.assembly_editor,
        "rootNamespace": names.namespace_editor,
        "references": [names.assembly_runtime],
        "includePlatforms": ["Editor"],
        "excludePlatforms": [],
        "allowUnsafeCode": False,
        "overrideReferences": False,
        "precompiledReferences": [],
        "autoReferenced": True,
        "defineConstraints": [],
        "versionDefines": [],
        "noEngineReferences": False,
    }
    return json.dumps(doc, indent=4) + "\n"
