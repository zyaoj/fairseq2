#!/usr/bin/env python3
"""
Documentation staleness checker for fairseq2 skill.

Validates that documentation references (line numbers, function signatures,
import statements) match the actual codebase state.

Usage:
    python scripts/check_staleness.py --summary
    python scripts/check_staleness.py --output reports/staleness.md
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

from config import load_config, get_docs_dir, get_codebase_root
from utils import (
    Issue, Severity, iter_markdown_files,
    extract_line_references, extract_function_signatures,
    extract_import_statements, validate_import_module, validate_import_symbol,
    format_report_header, format_issues_section
)


def check_line_reference(
    filename: str,
    start_line: int,
    end_line: int,
    codebase_root: Path
) -> Issue | None:
    """Check if a line reference is valid."""
    matches = list(codebase_root.rglob(f"**/{filename}"))
    if not matches:
        return Issue(
            severity=Severity.HIGH,
            category="missing_file",
            message=f"Referenced file not found: {filename}",
            suggestion="Update reference or remove if file was deleted"
        )

    file_path = matches[0]
    try:
        lines = file_path.read_text().split('\n')
        if end_line > len(lines):
            return Issue(
                severity=Severity.MEDIUM,
                category="line_out_of_range",
                message=f"Line {end_line} exceeds file length ({len(lines)} lines)",
                file_path=str(file_path),
                suggestion="Update line reference to valid range"
            )
    except Exception as e:
        return Issue(
            severity=Severity.LOW,
            category="read_error",
            message=f"Could not read file: {e}",
            file_path=str(file_path)
        )
    return None


def check_signature(
    sig_type: str,
    name: str,
    codebase_root: Path,
    config
) -> Issue | None:
    """Check if a function/class signature exists in codebase."""
    for pattern in config.example_signature_patterns:
        if re.match(pattern, name):
            return None

    search_pattern = f"def {name}" if sig_type == "function" else f"class {name}"
    for py_file in codebase_root.rglob("**/*.py"):
        try:
            if search_pattern in py_file.read_text():
                return None
        except Exception:
            pass

    return Issue(
        severity=Severity.MEDIUM,
        category="signature_not_found",
        message=f"{sig_type.capitalize()} '{name}' not found in codebase",
        suggestion="Verify the signature exists or update documentation"
    )


def check_import(
    import_info: dict,
    codebase_root: Path,
    config
) -> list[Issue]:
    """Check if an import statement is valid for the target codebase.

    Args:
        import_info: Dict with keys: module, symbols, line_number, full_statement
        codebase_root: Path to the codebase root
        config: Skill configuration

    Returns:
        List of issues found (empty if valid)
    """
    issues = []
    module = import_info['module']
    symbols = import_info['symbols']
    line_number = import_info['line_number']

    # Only validate imports from the target package
    package_name = config.skill_name
    if not module.startswith(package_name):
        return issues

    # Check if module matches example patterns to skip
    for pattern in getattr(config, 'example_import_module_patterns', []):
        if re.match(pattern, module):
            return issues

    # Check if module exists
    if not validate_import_module(module, codebase_root, package_name):
        issues.append(Issue(
            severity=Severity.HIGH,
            category="invalid_import_module",
            message=f"Module '{module}' does not exist in {package_name} v0.7.0",
            line_number=line_number,
            suggestion=f"Check if the module was renamed or removed. Statement: {import_info['full_statement']}"
        ))
        return issues  # No point checking symbols if module doesn't exist

    # Check if symbols exist in the module
    for symbol in symbols:
        # Skip symbols matching example patterns
        skip_symbol = False
        for pattern in getattr(config, 'example_import_symbol_patterns', []):
            if re.match(pattern, symbol):
                skip_symbol = True
                break

        if skip_symbol:
            continue

        if not validate_import_symbol(module, symbol, codebase_root, package_name):
            issues.append(Issue(
                severity=Severity.HIGH,
                category="invalid_import_symbol",
                message=f"Symbol '{symbol}' not found in module '{module}'",
                line_number=line_number,
                suggestion=f"Check if '{symbol}' was renamed or moved. Statement: {import_info['full_statement']}"
            ))

    return issues


def check_doc_staleness(doc_path: Path, codebase_root: Path, config) -> list[Issue]:
    """Check a single documentation file for staleness."""
    issues = []

    # Skip signature checks for specified files
    if any(skip in doc_path.name for skip in config.skip_signature_check_files):
        return issues

    content = doc_path.read_text()

    # Check line references
    for filename, start, end in extract_line_references(content):
        issue = check_line_reference(filename, start, end, codebase_root)
        if issue:
            issue.file_path = str(doc_path)
            issues.append(issue)

    # Check function/class signatures
    if "exercise" not in doc_path.name.lower():
        for sig_type, name in extract_function_signatures(content):
            issue = check_signature(sig_type, name, codebase_root, config)
            if issue:
                issue.file_path = str(doc_path)
                issues.append(issue)

    # Check import statements (skip for specified files)
    skip_import_files = getattr(config, 'skip_import_check_files', [])
    if not any(skip in doc_path.name for skip in skip_import_files):
        for import_info in extract_import_statements(content):
            import_issues = check_import(import_info, codebase_root, config)
            for issue in import_issues:
                issue.file_path = str(doc_path)
                issues.append(issue)

    return issues


def main():
    parser = argparse.ArgumentParser(description="Check documentation staleness")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--output", type=str, help="Output report file path")
    args = parser.parse_args()

    config = load_config()
    docs_dir = get_docs_dir()
    codebase_root = get_codebase_root()

    all_issues = []
    docs_checked = 0

    for doc_path in iter_markdown_files(docs_dir):
        issues = check_doc_staleness(doc_path, codebase_root, config)
        all_issues.extend(issues)
        docs_checked += 1

    print(f"\n📊 Staleness Check Summary")
    print(f"   Docs checked: {docs_checked}")
    print(f"   Issues found: {len(all_issues)}")

    by_severity = {}
    for issue in all_issues:
        by_severity.setdefault(issue.severity, []).append(issue)

    for severity in Severity:
        count = len(by_severity.get(severity, []))
        if count > 0:
            print(f"   - {severity.value.upper()}: {count}")

    if args.output:
        report = format_report_header(
            f"{config.skill_name} Staleness Report",
            datetime.now().isoformat()
        )
        for severity in Severity:
            issues = by_severity.get(severity, [])
            report += format_issues_section(f"{severity.value.upper()} Issues", issues)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"\n📝 Report written to: {output_path}")

    return 0 if len(all_issues) == 0 else 1


if __name__ == "__main__":
    exit(main())
