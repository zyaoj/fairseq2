#!/usr/bin/env python3
"""
Link and breadcrumb maintenance for fairseq2 skill.

Validates and fixes documentation links, breadcrumbs, and navigation.

Usage:
    python scripts/update_links.py --check all
    python scripts/update_links.py --check breadcrumbs
    python scripts/update_links.py --fix breadcrumbs --apply
    python scripts/update_links.py --output reports/link_health.md
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

from config import load_config, get_docs_dir
from utils import (
    Issue, Severity, iter_markdown_files,
    extract_markdown_links, format_report_header, format_issues_section
)


BREADCRUMB_PATTERN = r'^> 📍 \[Index\]\([^)]+\) › \[([^\]]+)\]\([^)]+\) › \*\*([^*]+)\*\*$'


def generate_breadcrumb(file_path: Path, docs_dir: Path, config) -> str:
    """Generate correct breadcrumb for a doc file."""
    rel_path = file_path.relative_to(docs_dir)
    parts = rel_path.parts
    
    if len(parts) < 2:
        return ""
    
    phase_dir = parts[0]
    file_name = parts[-1]
    
    title = file_name[3:-3].replace("_", " ").title() if file_name[:2].isdigit() else file_name[:-3].replace("_", " ").title()
    if file_name.startswith("00_quickstart"):
        title = "Quick Start (15 min)"
    
    phase_name = config.phase_names.get(phase_dir, phase_dir.replace("_", " ").title())
    
    return f'> 📍 [Index](../00_index.md) › [{phase_name}](./) › **{title}**'


def validate_breadcrumb(file_path: Path, docs_dir: Path, config) -> Issue | None:
    """Validate breadcrumb in a doc file."""
    rel_path = file_path.relative_to(docs_dir)
    if len(rel_path.parts) < 2:
        return None
    
    content = file_path.read_text()
    first_line = content.split('\n')[0] if content else ""
    
    if not first_line.startswith('> 📍'):
        expected = generate_breadcrumb(file_path, docs_dir, config)
        return Issue(
            severity=Severity.LOW,
            category="missing_breadcrumb",
            message=f"Missing breadcrumb",
            file_path=str(rel_path),
            suggestion=f"Add: {expected}"
        )
    
    if not re.match(BREADCRUMB_PATTERN, first_line):
        return Issue(
            severity=Severity.LOW,
            category="malformed_breadcrumb",
            message="Breadcrumb format is incorrect",
            file_path=str(rel_path)
        )
    
    return None


def validate_links(file_path: Path, docs_dir: Path) -> list[Issue]:
    """Validate all links in a doc file."""
    issues = []
    content = file_path.read_text()
    
    for link in extract_markdown_links(content):
        target = link['target']
        
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        
        target_path = (file_path.parent / target).resolve()
        if not target_path.exists():
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category="broken_link",
                message=f"Broken link: {target}",
                file_path=str(file_path.relative_to(docs_dir)),
                line_number=link['line_number'],
                suggestion="Update link target or remove"
            ))
    
    return issues


def detect_orphan_docs(docs_dir: Path, index_file: str) -> list[Issue]:
    """Detect docs not linked from index."""
    issues = []
    index_path = docs_dir / index_file
    
    if not index_path.exists():
        return issues
    
    index_content = index_path.read_text()
    linked_docs = set()
    
    for link in extract_markdown_links(index_content):
        target = link['target']
        if target.endswith('.md'):
            linked_docs.add(target)
    
    for doc_path in iter_markdown_files(docs_dir):
        rel_path = str(doc_path.relative_to(docs_dir))
        if rel_path == index_file:
            continue
        
        if rel_path not in linked_docs and f"./{rel_path}" not in linked_docs:
            is_linked = any(rel_path in link or rel_path.split('/')[-1] in link for link in linked_docs)
            if not is_linked:
                issues.append(Issue(
                    severity=Severity.LOW,
                    category="orphan_doc",
                    message=f"Document not linked from index",
                    file_path=rel_path,
                    suggestion=f"Add link to {index_file}"
                ))
    
    return issues


def fix_breadcrumbs(docs_dir: Path, config, apply: bool = False) -> list[str]:
    """Fix missing/malformed breadcrumbs."""
    fixed = []
    
    for doc_path in iter_markdown_files(docs_dir):
        rel_path = doc_path.relative_to(docs_dir)
        if len(rel_path.parts) < 2:
            continue
        
        content = doc_path.read_text()
        expected = generate_breadcrumb(doc_path, docs_dir, config)
        
        if not expected:
            continue
        
        lines = content.split('\n')
        first_line = lines[0] if lines else ""
        
        if first_line.startswith('> 📍'):
            if first_line != expected:
                lines[0] = expected
                fixed.append(str(rel_path))
        else:
            lines.insert(0, expected)
            lines.insert(1, "")
            fixed.append(str(rel_path))
        
        if apply and str(rel_path) in fixed:
            doc_path.write_text('\n'.join(lines))
    
    return fixed


def main():
    parser = argparse.ArgumentParser(description="Link and breadcrumb maintenance")
    parser.add_argument("--check", choices=["all", "breadcrumbs", "links", "orphans"], default="all")
    parser.add_argument("--fix", choices=["breadcrumbs"])
    parser.add_argument("--apply", action="store_true", help="Apply fixes")
    parser.add_argument("--preview", action="store_true", help="Preview fixes")
    parser.add_argument("--output", type=str, help="Output report file")
    args = parser.parse_args()
    
    config = load_config()
    docs_dir = get_docs_dir()
    
    all_issues = []
    
    if args.fix:
        if args.fix == "breadcrumbs":
            fixed = fix_breadcrumbs(docs_dir, config, apply=args.apply)
            print(f"\n{'Applied' if args.apply else 'Would fix'} {len(fixed)} breadcrumbs")
            for f in fixed:
                print(f"  - {f}")
        return 0
    
    if args.check in ["all", "breadcrumbs"]:
        for doc_path in iter_markdown_files(docs_dir):
            issue = validate_breadcrumb(doc_path, docs_dir, config)
            if issue:
                all_issues.append(issue)
    
    if args.check in ["all", "links"]:
        for doc_path in iter_markdown_files(docs_dir):
            issues = validate_links(doc_path, docs_dir)
            all_issues.extend(issues)
    
    if args.check in ["all", "orphans"]:
        issues = detect_orphan_docs(docs_dir, config.index_file)
        all_issues.extend(issues)
    
    print(f"\n📊 Link Health Summary")
    print(f"   Issues found: {len(all_issues)}")
    
    by_category = {}
    for issue in all_issues:
        by_category.setdefault(issue.category, []).append(issue)
    
    for category, issues in by_category.items():
        print(f"   - {category}: {len(issues)}")
    
    if args.output:
        report = format_report_header(f"{config.skill_name} Link Health Report", datetime.now().isoformat())
        for category, issues in by_category.items():
            report += format_issues_section(category.replace("_", " ").title(), issues)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"\n📝 Report written to: {output_path}")
    
    return 0 if len(all_issues) == 0 else 1


if __name__ == "__main__":
    exit(main())
