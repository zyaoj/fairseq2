#!/usr/bin/env python3
"""Tests for utility functions."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from utils import (
    Severity, Issue, extract_line_references,
    extract_function_signatures, extract_markdown_links,
    format_report_header, format_issues_section
)


class TestSeverity(unittest.TestCase):
    """Test Severity enum."""
    
    def test_severity_values(self):
        """Test all severity values exist."""
        self.assertEqual(Severity.CRITICAL.value, "critical")
        self.assertEqual(Severity.HIGH.value, "high")
        self.assertEqual(Severity.MEDIUM.value, "medium")
        self.assertEqual(Severity.LOW.value, "low")


class TestIssue(unittest.TestCase):
    """Test Issue dataclass."""
    
    def test_basic_issue(self):
        """Test basic issue creation."""
        issue = Issue(
            severity=Severity.HIGH,
            category="test",
            message="Test message"
        )
        self.assertEqual(issue.severity, Severity.HIGH)
        self.assertEqual(issue.category, "test")
    
    def test_to_markdown(self):
        """Test markdown formatting."""
        issue = Issue(
            severity=Severity.MEDIUM,
            category="test",
            message="Test message",
            file_path="test.md",
            line_number=10
        )
        md = issue.to_markdown()
        self.assertIn("[MEDIUM]", md)
        self.assertIn("test.md", md)


class TestExtractLineReferences(unittest.TestCase):
    """Test line reference extraction."""
    
    def test_single_line(self):
        """Test extracting single line reference."""
        refs = extract_line_references("See file.py:L27")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0], ("file.py", 27, 27))
    
    def test_line_range(self):
        """Test extracting line range."""
        refs = extract_line_references("See file.py:L27-50")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0], ("file.py", 27, 50))
    
    def test_no_L_prefix(self):
        """Test extracting without L prefix."""
        refs = extract_line_references("See file.py:27-50")
        self.assertEqual(len(refs), 1)


class TestExtractFunctionSignatures(unittest.TestCase):
    """Test function signature extraction."""
    
    def test_def_pattern(self):
        """Test def pattern extraction."""
        sigs = extract_function_signatures("`def my_function(`")
        self.assertEqual(len(sigs), 1)
        self.assertEqual(sigs[0], ("function", "my_function"))
    
    def test_class_pattern(self):
        """Test class pattern extraction."""
        sigs = extract_function_signatures("`class MyClass(`")
        self.assertEqual(len(sigs), 1)
        self.assertEqual(sigs[0], ("class", "MyClass"))


class TestExtractMarkdownLinks(unittest.TestCase):
    """Test markdown link extraction."""
    
    def test_basic_link(self):
        """Test basic link extraction."""
        links = extract_markdown_links("[Text](link.md)")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["text"], "Text")
        self.assertEqual(links[0]["target"], "link.md")


if __name__ == "__main__":
    unittest.main()
