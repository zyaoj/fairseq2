#!/usr/bin/env python3
"""Tests for configuration management."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import SkillConfig, load_config, get_skill_dir, get_docs_dir


class TestSkillConfig(unittest.TestCase):
    """Test SkillConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SkillConfig(
            skill_name="fairseq2",
            codebase_root="/storage/home/yaoj/projects/fairseq2/src/fairseq2"
        )
        self.assertEqual(config.docs_path, "docs")
        self.assertEqual(config.index_file, "00_index.md")
        self.assertIn("hands_on_exercises.md", config.skip_signature_check_files)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SkillConfig(
            skill_name="test_skill",
            codebase_root="test/path",
            docs_path="documentation",
            index_file="index.md"
        )
        self.assertEqual(config.skill_name, "test_skill")
        self.assertEqual(config.docs_path, "documentation")


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading functions."""

    def test_get_skill_dir(self):
        """Test skill directory detection."""
        skill_dir = get_skill_dir()
        self.assertTrue(skill_dir.exists())
        self.assertTrue((skill_dir / "scripts").exists())

    def test_load_config(self):
        """Test loading configuration from YAML."""
        config = load_config()
        self.assertEqual(config.skill_name, "fairseq2")
        self.assertIsInstance(config.phase_names, dict)

    def test_get_docs_dir(self):
        """Test documentation directory path."""
        docs_dir = get_docs_dir()
        self.assertTrue(docs_dir.name == "docs")


class TestParseSimpleYaml(unittest.TestCase):
    """Test the _parse_simple_yaml static method for YAML parsing without dependencies."""

    def test_simple_key_value_pairs(self):
        """Test parsing simple key-value pairs."""
        content = """skill_name: myskill
codebase_root: path/to/code
docs_path: docs"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["skill_name"], "myskill")
        self.assertEqual(result["codebase_root"], "path/to/code")
        self.assertEqual(result["docs_path"], "docs")

    def test_quoted_values(self):
        """Test parsing values with single and double quotes."""
        content = """name: "double quoted"
path: 'single quoted'
plain: no quotes"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["name"], "double quoted")
        self.assertEqual(result["path"], "single quoted")
        self.assertEqual(result["plain"], "no quotes")

    def test_list_items(self):
        """Test parsing list items with dash syntax."""
        content = """items:
  - first
  - second
  - third"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertIsInstance(result["items"], list)
        self.assertEqual(len(result["items"]), 3)
        self.assertEqual(result["items"][0], "first")
        self.assertEqual(result["items"][1], "second")
        self.assertEqual(result["items"][2], "third")

    def test_list_with_quoted_items(self):
        """Test parsing list items with quotes."""
        content = """patterns:
  - "^my_"
  - '^test_'
  - plain_item"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["patterns"][0], "^my_")
        self.assertEqual(result["patterns"][1], "^test_")
        self.assertEqual(result["patterns"][2], "plain_item")

    def test_nested_dictionary(self):
        """Test parsing nested dictionary entries."""
        content = """phase_names:
  phase1: Phase 1: Foundation
  phase2: Phase 2: Model
  phase3: Phase 3: Training"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertIsInstance(result["phase_names"], dict)
        self.assertEqual(len(result["phase_names"]), 3)
        self.assertEqual(result["phase_names"]["phase1"], "Phase 1: Foundation")
        self.assertEqual(result["phase_names"]["phase2"], "Phase 2: Model")
        self.assertEqual(result["phase_names"]["phase3"], "Phase 3: Training")

    def test_nested_dict_with_quotes(self):
        """Test parsing nested dictionary with quoted values."""
        content = """mappings:
  key1: "Value One"
  key2: 'Value Two'"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["mappings"]["key1"], "Value One")
        self.assertEqual(result["mappings"]["key2"], "Value Two")

    def test_comments_are_ignored(self):
        """Test that comment lines are ignored."""
        content = """# This is a comment
skill_name: test
# Another comment
codebase_root: path"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["skill_name"], "test")
        self.assertEqual(result["codebase_root"], "path")
        self.assertNotIn("#", str(result))

    def test_empty_lines_are_ignored(self):
        """Test that empty lines are ignored."""
        content = """skill_name: test

codebase_root: path

docs_path: docs"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["skill_name"], "test")

    def test_mixed_content(self):
        """Test parsing mixed content with scalars, lists, and dicts."""
        content = """skill_name: myskill
items:
  - item1
  - item2
mappings:
  key1: value1
  key2: value2
final_key: final_value"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["skill_name"], "myskill")
        self.assertIsInstance(result["items"], list)
        self.assertEqual(result["items"], ["item1", "item2"])
        self.assertIsInstance(result["mappings"], dict)
        self.assertEqual(result["mappings"]["key1"], "value1")
        self.assertEqual(result["final_key"], "final_value")

    def test_multiple_lists(self):
        """Test parsing multiple sequential lists."""
        content = """list1:
  - a
  - b
list2:
  - c
  - d"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["list1"], ["a", "b"])
        self.assertEqual(result["list2"], ["c", "d"])

    def test_multiple_dicts(self):
        """Test parsing multiple sequential dictionaries."""
        content = """dict1:
  k1: v1
  k2: v2
dict2:
  k3: v3
  k4: v4"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["dict1"], {"k1": "v1", "k2": "v2"})
        self.assertEqual(result["dict2"], {"k3": "v3", "k4": "v4"})

    def test_value_with_colon(self):
        """Test parsing values that contain colons."""
        content = """phase_names:
  phase1: Phase 1: Foundation
  phase2: Phase 2: Advanced: Topics"""
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["phase_names"]["phase1"], "Phase 1: Foundation")
        self.assertEqual(result["phase_names"]["phase2"], "Phase 2: Advanced: Topics")

    def test_whitespace_handling(self):
        """Test that trailing whitespace is handled correctly."""
        content = """skill_name: test
codebase_root: path  """
        result = SkillConfig._parse_simple_yaml(content)
        self.assertEqual(result["skill_name"], "test")
        self.assertEqual(result["codebase_root"], "path")

    def test_real_config_yaml_structure(self):
        """Test parsing a structure similar to the actual config.yaml."""
        content = """# Configuration file
skill_name: "fairseq2"
codebase_root: "/path/to/fairseq2"
docs_path: "docs"
index_file: "00_index.md"

skip_signature_check_files:
  - "hands_on_exercises.md"
  - "08_hands_on_exercises.md"

example_signature_patterns:
  - "^my_"
  - "^test_"

phase_names:
  phase1_foundation: "Phase 1: Foundation"
  phase2_model: "Phase 2: Model Architecture"

reports_dir: "reports"
"""
        result = SkillConfig._parse_simple_yaml(content)

        # Verify scalars
        self.assertEqual(result["skill_name"], "fairseq2")
        self.assertEqual(result["codebase_root"], "/path/to/fairseq2")
        self.assertEqual(result["docs_path"], "docs")
        self.assertEqual(result["index_file"], "00_index.md")
        self.assertEqual(result["reports_dir"], "reports")

        # Verify list
        self.assertIsInstance(result["skip_signature_check_files"], list)
        self.assertEqual(len(result["skip_signature_check_files"]), 2)
        self.assertIn("hands_on_exercises.md", result["skip_signature_check_files"])

        # Verify second list
        self.assertIsInstance(result["example_signature_patterns"], list)
        self.assertEqual(result["example_signature_patterns"][0], "^my_")

        # Verify dict
        self.assertIsInstance(result["phase_names"], dict)
        self.assertEqual(result["phase_names"]["phase1_foundation"], "Phase 1: Foundation")
        self.assertEqual(result["phase_names"]["phase2_model"], "Phase 2: Model Architecture")

    def test_load_actual_config_phase_names(self):
        """Test that actual config.yaml phase_names are loaded correctly as dict."""
        config = load_config()
        self.assertIsInstance(config.phase_names, dict)
        self.assertIn("phase1_foundation", config.phase_names)
        self.assertEqual(config.phase_names["phase1_foundation"], "Phase 1: Foundation")
        # Ensure no spurious empty key
        self.assertNotIn("phase_names", config.phase_names)
        self.assertNotIn("", config.phase_names)


if __name__ == "__main__":
    unittest.main()
