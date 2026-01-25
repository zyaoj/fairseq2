#!/usr/bin/env python3
"""Tests for index synchronization."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from update_index import DocEntry, extract_title, scan_docs


class TestDocEntry(unittest.TestCase):
    """Test DocEntry dataclass."""
    
    def test_basic_entry(self):
        """Test basic entry creation."""
        entry = DocEntry(
            path=Path("phase1/doc.md"),
            title="Test Doc",
            phase="phase1",
            order=1
        )
        self.assertEqual(entry.title, "Test Doc")
        self.assertEqual(entry.phase, "phase1")


class TestExtractTitle(unittest.TestCase):
    """Test title extraction."""
    
    def test_extract_from_header(self):
        """Test extracting title from # header."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# My Title\n\nContent here")
            f.flush()
            title = extract_title(Path(f.name))
            self.assertEqual(title, "My Title")
    
    def test_extract_from_filename(self):
        """Test extracting title from filename when no header."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("No header here\nJust content")
            f.flush()
            path = Path(f.name)
            title = extract_title(path)
            self.assertIsNotNone(title)


class TestScanDocs(unittest.TestCase):
    """Test document scanning."""
    
    def test_scan_empty_dir(self):
        """Test scanning empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = scan_docs(Path(tmpdir))
            self.assertEqual(len(entries), 0)
    
    def test_scan_with_docs(self):
        """Test scanning directory with docs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "01_test.md"
            doc_path.write_text("# Test\n\nContent")
            entries = scan_docs(Path(tmpdir))
            self.assertEqual(len(entries), 1)


if __name__ == "__main__":
    unittest.main()
