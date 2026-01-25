#!/usr/bin/env python3
"""
Skill validation and edge case tests for fairseq2.

Tests the overall skill functionality including routing,
gap detection, and self-evolution mechanisms.
"""

import sys
import unittest
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import load_config, get_skill_dir, get_docs_dir


class TestResult(Enum):
    """Test result status."""
    PASS = "✅ PASS"
    PARTIAL = "🟡 PARTIAL"
    FAIL = "❌ FAIL"


@dataclass
class SkillTest:
    """Definition of a skill validation test."""
    id: str
    category: str
    description: str
    expected_behavior: str
    files_to_check: list[str] = None
    
    def __post_init__(self):
        if self.files_to_check is None:
            self.files_to_check = []


class TestSkillLoading(unittest.TestCase):
    """Test that the skill loads correctly."""
    
    def test_skill_md_exists(self):
        """Test SKILL.md exists."""
        skill_dir = get_skill_dir()
        skill_md = skill_dir / "SKILL.md"
        self.assertTrue(skill_md.exists(), "SKILL.md should exist")
    
    def test_skill_has_frontmatter(self):
        """Test SKILL.md has valid YAML frontmatter."""
        skill_dir = get_skill_dir()
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()
        self.assertTrue(content.startswith("---"), "SKILL.md should start with ---")
        self.assertIn("oncalls:", content, "Should have oncalls field")
        self.assertIn("description:", content, "Should have description field")
    
    def test_docs_directory_exists(self):
        """Test docs directory exists."""
        docs_dir = get_docs_dir()
        self.assertTrue(docs_dir.exists(), "docs/ directory should exist")


class TestSkillStructure(unittest.TestCase):
    """Test skill directory structure."""
    
    def test_scripts_directory(self):
        """Test scripts directory exists."""
        skill_dir = get_skill_dir()
        scripts_dir = skill_dir / "scripts"
        self.assertTrue(scripts_dir.exists())
    
    def test_config_yaml_exists(self):
        """Test config.yaml exists."""
        skill_dir = get_skill_dir()
        config_yaml = skill_dir / "scripts" / "config.yaml"
        self.assertTrue(config_yaml.exists())
    
    def test_required_scripts_exist(self):
        """Test required maintenance scripts exist."""
        skill_dir = get_skill_dir()
        scripts_dir = skill_dir / "scripts"
        
        required_scripts = [
            "config.py",
            "utils.py",
            "check_staleness.py",
            "update_index.py",
            "update_links.py",
        ]
        
        for script in required_scripts:
            self.assertTrue(
                (scripts_dir / script).exists(),
                f"{script} should exist in scripts/"
            )


class TestDocumentationGaps(unittest.TestCase):
    """Test documentation gap tracking."""
    
    def test_gaps_file_exists(self):
        """Test DOCUMENTATION_GAPS.md exists."""
        skill_dir = get_skill_dir()
        gaps_file = skill_dir / "DOCUMENTATION_GAPS.md"
        self.assertTrue(gaps_file.exists())
    
    def test_gaps_file_has_structure(self):
        """Test DOCUMENTATION_GAPS.md has required sections."""
        skill_dir = get_skill_dir()
        gaps_file = skill_dir / "DOCUMENTATION_GAPS.md"
        content = gaps_file.read_text()
        
        required_sections = [
            "Active Gaps",
            "Resolved Gaps",
            "Gap Statistics",
        ]
        
        for section in required_sections:
            self.assertIn(section, content, f"Should have '{section}' section")


def run_tests_with_summary():
    """Run all tests and print summary."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("SKILL VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All skill validation tests passed!")
    else:
        print("\n❌ Some tests failed. Please review above.")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests_with_summary())
