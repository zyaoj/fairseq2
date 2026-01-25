#!/usr/bin/env python3
"""
Index synchronization script for fairseq2 skill.

Scans the documentation directory and updates the index file
to reflect the current structure.

Usage:
    python scripts/update_index.py --preview
    python scripts/update_index.py --apply
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re

from config import load_config, get_docs_dir


@dataclass
class DocEntry:
    """Represents a documentation file entry."""
    path: Path
    title: str
    phase: str | None
    order: int


def extract_title(doc_path: Path) -> str:
    """Extract title from markdown file."""
    content = doc_path.read_text()
    for line in content.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    name = doc_path.stem
    if name.startswith(('00_', '01_', '02_', '03_', '04_', '05_', '06_', '07_', '08_', '09_')):
        name = name[3:]
    return name.replace('_', ' ').title()


def scan_docs(docs_dir: Path) -> list[DocEntry]:
    """Scan documentation directory for all markdown files."""
    entries = []
    for md_file in sorted(docs_dir.rglob("*.md")):
        if md_file.name.startswith('.'):
            continue
        rel_path = md_file.relative_to(docs_dir)
        parts = rel_path.parts
        phase = parts[0] if len(parts) > 1 else None
        try:
            order = int(md_file.stem[:2])
        except (ValueError, IndexError):
            order = 99
        entries.append(DocEntry(
            path=rel_path,
            title=extract_title(md_file),
            phase=phase,
            order=order
        ))
    return entries


def generate_index_content(entries: list[DocEntry], config) -> str:
    """Generate index markdown content."""
    lines = [
        f"# {config.skill_name} Documentation Index",
        "",
        "## Quick Navigation",
        "",
    ]
    
    by_phase = {}
    for entry in entries:
        phase = entry.phase or "root"
        by_phase.setdefault(phase, []).append(entry)
    
    for phase in sorted(by_phase.keys()):
        phase_entries = sorted(by_phase[phase], key=lambda e: e.order)
        phase_name = config.phase_names.get(phase, phase.replace('_', ' ').title())
        lines.append(f"### {phase_name}")
        lines.append("")
        for entry in phase_entries:
            lines.append(f"- [{entry.title}]({entry.path})")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Synchronize documentation index")
    parser.add_argument("--preview", action="store_true", help="Preview changes only")
    parser.add_argument("--apply", action="store_true", help="Apply changes to index")
    args = parser.parse_args()
    
    config = load_config()
    docs_dir = get_docs_dir()
    
    entries = scan_docs(docs_dir)
    new_content = generate_index_content(entries, config)
    
    index_path = docs_dir / config.index_file
    
    if args.preview or not args.apply:
        print("📋 Preview of index content:")
        print("-" * 40)
        print(new_content)
        print("-" * 40)
        print(f"\nTotal docs found: {len(entries)}")
    
    if args.apply:
        index_path.write_text(new_content)
        print(f"\n✅ Index updated: {index_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
