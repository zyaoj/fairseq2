#!/usr/bin/env python3
"""Tests for link and breadcrumb maintenance."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from update_links import (
    generate_breadcrumb, validate_breadcrumb,
    validate_links, detect_orphan_docs
)
from config import load_config


class TestGenerateBreadcrumb(unittest.TestCase):
    """Test breadcrumb generation."""
    
    def setUp(self):
        self.config = load_config()
    
    def test_phase1_doc(self):
        """Test generating breadcrumb for phase1 doc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            phase_dir = docs_dir / "phase1_foundation"
            phase_dir.mkdir()
            doc_path = phase_dir / "01_test_doc.md"
            doc_path.touch()
            
            breadcrumb = generate_breadcrumb(doc_path, docs_dir, self.config)
            self.assertIn("📍", breadcrumb)
            self.assertIn("Index", breadcrumb)


class TestValidateBreadcrumb(unittest.TestCase):
    """Test breadcrumb validation."""
    
    def setUp(self):
        self.config = load_config()
    
    def test_valid_breadcrumb(self):
        """Test validating a correct breadcrumb."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            phase_dir = docs_dir / "phase1_foundation"
            phase_dir.mkdir()
            doc_path = phase_dir / "01_test.md"
            doc_path.write_text("> 📍 [Index](../00_index.md) › [Phase 1: Foundation](./) › **Test**\n\n# Content")
            
            issue = validate_breadcrumb(doc_path, docs_dir, self.config)
            # Should have no issue for valid breadcrumb or low severity if format differs


class TestValidateLinks(unittest.TestCase):
    """Test link validation."""
    
    def test_valid_links(self):
        """Test validating valid internal links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            doc1 = docs_dir / "doc1.md"
            doc2 = docs_dir / "doc2.md"
            doc1.write_text("[Link to doc2](doc2.md)")
            doc2.write_text("# Doc 2")
            
            issues = validate_links(doc1, docs_dir)
            self.assertEqual(len(issues), 0)
    
    def test_broken_link(self):
        """Test detecting broken links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            doc1 = docs_dir / "doc1.md"
            doc1.write_text("[Broken link](nonexistent.md)")
            
            issues = validate_links(doc1, docs_dir)
            self.assertEqual(len(issues), 1)


if __name__ == "__main__":
    unittest.main()
