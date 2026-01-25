#!/usr/bin/env python3
"""
Configuration management for fairseq2 skill maintenance scripts.

Loads configuration from config.yaml and provides typed access to settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
import os
import sys
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    import json


def detect_venv() -> dict:
    """Detect if running in a virtual environment.

    Returns:
        dict with keys:
            - in_venv: bool - True if in a virtual environment
            - venv_type: str - Type of venv ('venv', 'conda', 'poetry', 'pipenv', 'none')
            - venv_path: str | None - Path to the venv if detected
            - python_path: str - Path to the Python executable
    """
    result = {
        "in_venv": False,
        "venv_type": "none",
        "venv_path": None,
        "python_path": sys.executable,
    }

    # Check for standard venv/virtualenv
    if hasattr(sys, 'real_prefix'):
        # virtualenv < 20
        result["in_venv"] = True
        result["venv_type"] = "virtualenv"
        result["venv_path"] = sys.prefix
    elif hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        # venv or virtualenv >= 20
        result["in_venv"] = True
        result["venv_type"] = "venv"
        result["venv_path"] = sys.prefix

    # Check for conda
    if os.environ.get('CONDA_DEFAULT_ENV') or os.environ.get('CONDA_PREFIX'):
        result["in_venv"] = True
        result["venv_type"] = "conda"
        result["venv_path"] = os.environ.get('CONDA_PREFIX', sys.prefix)

    # Check for poetry
    if os.environ.get('POETRY_ACTIVE'):
        result["in_venv"] = True
        result["venv_type"] = "poetry"

    # Check for pipenv
    if os.environ.get('PIPENV_ACTIVE'):
        result["in_venv"] = True
        result["venv_type"] = "pipenv"

    return result


def check_venv_status(verbose: bool = False) -> bool:
    """Check and optionally print venv status.

    Args:
        verbose: If True, print venv information

    Returns:
        True if in a virtual environment
    """
    info = detect_venv()
    if verbose:
        if info["in_venv"]:
            print(f"✅ Running in {info['venv_type']} environment")
            if info["venv_path"]:
                print(f"   Path: {info['venv_path']}")
        else:
            print("⚠️  Not running in a virtual environment")
            print(f"   Using system Python: {info['python_path']}")
    return info["in_venv"]


@dataclass
class SkillConfig:
    """Configuration for skill maintenance."""

    skill_name: str
    codebase_root: str
    docs_path: str = "docs"
    index_file: str = "00_index.md"

    skip_signature_check_files: list[str] = field(default_factory=lambda: [
        "hands_on_exercises.md",
    ])
    example_signature_patterns: list[str] = field(default_factory=lambda: [
        r"^my_", r"^test_", r"^custom_", r"^build_my_",
        r"^example_", r"^MyCustom", r"^My[A-Z]",
    ])

    # Import filtering config
    skip_import_check_files: list[str] = field(default_factory=lambda: [
        "hands_on_exercises.md", "00_quickstart.md",
    ])
    example_import_symbol_patterns: list[str] = field(default_factory=lambda: [
        r"^my_", r"^My[A-Z]", r"^example_", r"^Example",
        r"^test_", r"^Test[A-Z]", r"^custom_", r"^Custom",
    ])
    example_import_module_patterns: list[str] = field(default_factory=lambda: [])

    phase_names: dict[str, str] = field(default_factory=dict)
    reports_dir: str = "reports"

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "SkillConfig":
        """Load configuration from YAML file."""
        with open(yaml_path) as f:
            if HAS_YAML:
                data = yaml.safe_load(f)
            else:
                # Fallback: parse simple YAML manually
                data = cls._parse_simple_yaml(f.read())
        return cls(**data)

    @staticmethod
    def _parse_simple_yaml(content: str) -> dict:
        """Parse simple YAML without external dependencies.

        Handles:
        - Simple key: value pairs
        - Lists with - items
        - Nested dicts (one level deep with 2-space indentation)
        - Comments (lines starting with # at any indentation level)
        """
        result = {}
        current_key = None
        current_collection = None  # Can be list or dict
        collection_type = None  # 'list' or 'dict'

        for line in content.split('\n'):
            line = line.rstrip()
            # Skip empty lines and comments (at any indentation level)
            if not line or line.lstrip().startswith('#'):
                continue

            # Check for list item (2-space indent + dash)
            if line.startswith('  - '):
                if collection_type == 'list' and current_collection is not None:
                    value = line[4:].strip().strip('"').strip("'")
                    current_collection.append(value)
                elif current_key and current_collection is None:
                    # First list item - initialize the list
                    current_collection = []
                    collection_type = 'list'
                    value = line[4:].strip().strip('"').strip("'")
                    current_collection.append(value)
                continue

            # Check for nested dict item (2-space indent + key: value)
            if line.startswith('  ') and ':' in line and not line.startswith('  - '):
                nested_line = line[2:]  # Remove 2-space indent
                if collection_type == 'dict' and current_collection is not None:
                    nested_key, _, nested_value = nested_line.partition(':')
                    nested_key = nested_key.strip()
                    nested_value = nested_value.strip().strip('"').strip("'")
                    current_collection[nested_key] = nested_value
                elif current_key and current_collection is None:
                    # First dict item - initialize the dict
                    current_collection = {}
                    collection_type = 'dict'
                    nested_key, _, nested_value = nested_line.partition(':')
                    current_collection[nested_key.strip()] = nested_value.strip().strip('"').strip("'")
                continue

            # Check for top-level key-value pair
            if ':' in line and not line.startswith(' '):
                # Save previous collection
                if current_collection is not None:
                    result[current_key] = current_collection
                    current_collection = None
                    collection_type = None

                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if not value:
                    current_key = key
                    # We don't know yet if it's a list or dict
                    # Will be determined by the first nested item
                    current_collection = None
                    collection_type = None
                else:
                    result[key] = value
                    current_key = None

        if current_collection is not None:
            result[current_key] = current_collection

        return result


def get_skill_dir() -> Path:
    """Get the skill directory path."""
    return Path(__file__).parent.parent


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_skill_dir() / "scripts" / "config.yaml"


def load_config() -> SkillConfig:
    """Load the skill configuration."""
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    return SkillConfig.from_yaml(config_path)


def get_docs_dir() -> Path:
    """Get the documentation directory path."""
    config = load_config()
    return get_skill_dir() / config.docs_path


def get_codebase_root() -> Path:
    """Get the codebase root path.

    If codebase_root in config is an absolute path, returns it directly.
    Otherwise, resolves it relative to the repo root.
    """
    config = load_config()
    codebase_path = Path(config.codebase_root)

    # If it's already an absolute path, use it directly
    if codebase_path.is_absolute():
        return codebase_path

    # Otherwise, resolve relative to repo root
    repo_root = get_skill_dir().parent.parent.parent
    return repo_root / config.codebase_root


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Configuration management for fairseq2 skill")
    parser.add_argument("--check-venv", action="store_true", help="Check virtual environment status")
    args = parser.parse_args()

    if args.check_venv:
        check_venv_status(verbose=True)
    else:
        config = load_config()
        print(f"Skill: {config.skill_name}")
        print(f"Codebase root: {config.codebase_root}")
        print(f"Docs path: {get_docs_dir()}")
        print()
        check_venv_status(verbose=True)
