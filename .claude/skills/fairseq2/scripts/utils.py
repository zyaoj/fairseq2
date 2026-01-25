#!/usr/bin/env python3
"""
Shared utilities for fairseq2 skill maintenance scripts.

Provides common functions for file operations, pattern matching,
and report generation.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Issue:
    """Represents a detected issue."""
    severity: Severity
    category: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

    def to_markdown(self) -> str:
        """Format issue as markdown."""
        parts = [f"- **[{self.severity.value.upper()}]** {self.message}"]
        if self.file_path:
            parts.append(f"  - File: `{self.file_path}`")
        if self.line_number:
            parts.append(f"  - Line: {self.line_number}")
        if self.suggestion:
            parts.append(f"  - Suggestion: {self.suggestion}")
        return "\n".join(parts)


def iter_markdown_files(directory: Path) -> Iterator[Path]:
    """Iterate over all markdown files in a directory recursively.

    Filters out hidden directories/files, but only checks the relative path
    from the given directory (not the full absolute path).
    """
    for path in directory.rglob("*.md"):
        # Get relative path from the search directory to check for hidden items
        try:
            rel_path = path.relative_to(directory)
            if not any(part.startswith(".") for part in rel_path.parts):
                yield path
        except ValueError:
            # If relative_to fails, still yield the file
            yield path


def extract_line_references(content: str) -> list[tuple[str, int, int]]:
    """
    Extract line references from markdown content.

    Matches patterns like:
    - file.py:L27
    - file.py:L27-302
    - file.py:27-302

    Returns list of (filename, start_line, end_line) tuples.
    """
    pattern = r'([a-zA-Z0-9_/]+\.py):L?(\d+)(?:-(\d+))?'
    matches = []
    for match in re.finditer(pattern, content):
        filename = match.group(1)
        start_line = int(match.group(2))
        end_line = int(match.group(3)) if match.group(3) else start_line
        matches.append((filename, start_line, end_line))
    return matches


def extract_function_signatures(content: str) -> list[tuple[str, str]]:
    """
    Extract function/class signatures mentioned in markdown.

    Returns list of (signature_type, name) tuples.
    """
    patterns = [
        (r'`def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', 'function'),
        (r'`class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]', 'class'),
        (r'`([a-zA-Z_][a-zA-Z0-9_]*)\(\)`', 'function'),
    ]
    signatures = []
    for pattern, sig_type in patterns:
        for match in re.finditer(pattern, content):
            signatures.append((sig_type, match.group(1)))
    return signatures


def extract_markdown_links(content: str) -> list[dict]:
    """
    Extract all markdown links from content.

    Returns list of dicts with keys: text, target, line_number
    """
    links = []
    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', line):
            links.append({
                'text': match.group(1),
                'target': match.group(2),
                'line_number': line_num,
            })
    return links


def extract_import_statements(content: str) -> list[dict]:
    """
    Extract Python import statements from markdown content (code blocks).

    Matches patterns like:
    - from fairseq2.config import ConfigRegistry
    - from fairseq2.models import load_model
    - import fairseq2.device

    Returns list of dicts with keys:
    - module: the module path (e.g., 'fairseq2.config')
    - symbols: list of imported symbols (e.g., ['ConfigRegistry'])
    - line_number: line number in the document
    - full_statement: the full import statement
    """
    imports = []
    lines = content.split('\n')

    # Pattern for "from X import Y, Z"
    from_import_pattern = r'^from\s+([\w.]+)\s+import\s+(.+)$'
    # Pattern for "import X" or "import X as Y"
    import_pattern = r'^import\s+([\w.]+)(?:\s+as\s+\w+)?$'

    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()

        # Check "from X import Y" pattern
        match = re.match(from_import_pattern, line_stripped)
        if match:
            module = match.group(1)
            symbols_str = match.group(2)
            # Parse symbols (handle "X, Y, Z" and "X as alias")
            symbols = []
            for sym in symbols_str.split(','):
                sym = sym.strip()
                # Handle "X as Y" - just take X
                if ' as ' in sym:
                    sym = sym.split(' as ')[0].strip()
                # Handle continuation with parentheses
                sym = sym.strip('()')
                if sym and sym not in ('\\', ''):
                    symbols.append(sym)

            if symbols:
                imports.append({
                    'module': module,
                    'symbols': symbols,
                    'line_number': line_num,
                    'full_statement': line_stripped,
                })
            continue

        # Check "import X" pattern
        match = re.match(import_pattern, line_stripped)
        if match:
            module = match.group(1)
            imports.append({
                'module': module,
                'symbols': [],  # No specific symbols, importing the module itself
                'line_number': line_num,
                'full_statement': line_stripped,
            })

    return imports


def validate_import_module(module: str, codebase_root: Path, package_name: str = "fairseq2") -> bool:
    """
    Validate that a module path exists in the codebase.

    Args:
        module: Module path like 'fairseq2.config' or 'fairseq2.models.transformer'
        codebase_root: Root path to the codebase (e.g., /path/to/fairseq2/src/fairseq2)
        package_name: The package name to validate (default: 'fairseq2')

    Returns:
        True if the module exists, False otherwise
    """
    if not module.startswith(package_name):
        # Not a package import, skip validation
        return True

    # Convert module path to file path
    # e.g., 'fairseq2.config' -> 'config.py' or 'config/__init__.py'
    parts = module.split('.')
    if len(parts) < 2:
        return True  # Just the package name itself

    # Remove the package name prefix to get relative path
    rel_parts = parts[1:]  # e.g., ['config'] or ['models', 'transformer']

    # Check if it's a module file (X.py) or a package (X/__init__.py)
    rel_path = Path(*rel_parts)

    # Try as a .py file
    py_file = codebase_root / f"{rel_path}.py"
    if py_file.exists():
        return True

    # Try as a package directory with __init__.py
    pkg_dir = codebase_root / rel_path
    if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
        return True

    return False


def validate_import_symbol(module: str, symbol: str, codebase_root: Path, package_name: str = "fairseq2") -> bool:
    """
    Validate that a symbol exists in a module.

    Args:
        module: Module path like 'fairseq2.config'
        symbol: Symbol name like 'ConfigRegistry'
        codebase_root: Root path to the codebase
        package_name: The package name to validate

    Returns:
        True if the symbol likely exists, False otherwise
    """
    if not module.startswith(package_name):
        return True  # Not a package import, skip validation

    # Convert module path to file path
    parts = module.split('.')
    if len(parts) < 2:
        return True

    rel_parts = parts[1:]
    rel_path = Path(*rel_parts)

    # Find the module file
    py_file = codebase_root / f"{rel_path}.py"
    pkg_init = codebase_root / rel_path / "__init__.py"

    files_to_check = []
    if py_file.exists():
        files_to_check.append(py_file)
    if pkg_init.exists():
        files_to_check.append(pkg_init)

    if not files_to_check:
        return False  # Module doesn't exist

    # Search for the symbol in the module files
    # Look for: class Symbol, def symbol, Symbol = , __all__ containing symbol
    patterns = [
        rf'\bclass\s+{re.escape(symbol)}\b',
        rf'\bdef\s+{re.escape(symbol)}\b',
        rf'^{re.escape(symbol)}\s*[=:]',
        rf'"{re.escape(symbol)}"',  # In __all__
        rf"'{re.escape(symbol)}'",  # In __all__
    ]

    for file_path in files_to_check:
        try:
            content = file_path.read_text()
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    return True
        except Exception:
            pass

    # Also check if it's re-exported from submodules (common in __init__.py)
    # This is a heuristic - symbol might be imported from elsewhere
    if pkg_init.exists():
        try:
            content = pkg_init.read_text()
            # Check for "from .submodule import symbol"
            if f'import {symbol}' in content or f'import {symbol},' in content:
                return True
        except Exception:
            pass

    return False


def format_report_header(title: str, timestamp: str) -> str:
    """Format a report header."""
    return f"""# {title}

Generated: {timestamp}

---

"""


def format_issues_section(title: str, issues: list[Issue]) -> str:
    """Format a section of issues."""
    if not issues:
        return f"## {title}\n\n✅ No issues found.\n\n"

    lines = [f"## {title}", "", f"Found {len(issues)} issue(s):", ""]
    for issue in issues:
        lines.append(issue.to_markdown())
        lines.append("")
    return "\n".join(lines)
