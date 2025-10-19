#!/usr/bin/env python3
"""
Test script for ConfigCLI utility.

This script tests the ConfigCLI functionality with various scenarios:
1. Default configuration loading
2. YAML file loading
3. Command-line overrides
4. Configuration dumping
5. Error handling
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from unittest.mock import Mock

from fairseq2.utils.config_cli import ConfigCLI, ConfigLoadError, ConfigDumpError


@dataclass(kw_only=True)
class TestConfig:
    """Test configuration for validation."""
    name: str = "test"
    value: int = 42
    enabled: bool = True
    items: list[str] = field(default_factory=lambda: ["a", "b", "c"])
    nested: dict[str, int] = field(default_factory=lambda: {"x": 1, "y": 2})


def test_default_config() -> None:
    """Test loading default configuration."""
    print("Testing default configuration loading...")
    
    cli = ConfigCLI(TestConfig)
    args = Mock()
    args.config_file = None
    args.config_overrides = None
    
    config = cli.load_config(args)
    
    assert config.name == "test"
    assert config.value == 42
    assert config.enabled is True
    assert config.items == ["a", "b", "c"]
    assert config.nested == {"x": 1, "y": 2}
    
    print("✓ Default configuration test passed")


def test_yaml_file_loading() -> None:
    """Test loading configuration from YAML file."""
    print("Testing YAML file loading...")
    
    # Create temporary YAML file
    yaml_content = """
name: "from_file"
value: 100
enabled: false
items: ["d", "e", "f"]
nested:
  x: 10
  y: 20
  z: 30
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_file = Path(f.name)
    
    try:
        cli = ConfigCLI(TestConfig)
        args = Mock()
        args.config_file = temp_file
        args.config_overrides = None
        
        config = cli.load_config(args)
        
        assert config.name == "from_file"
        assert config.value == 100
        assert config.enabled is False
        assert config.items == ["d", "e", "f"]
        assert config.nested == {"x": 10, "y": 20, "z": 30}
        
        print("✓ YAML file loading test passed")
        
    finally:
        temp_file.unlink()


def test_command_line_overrides() -> None:
    """Test command-line configuration overrides."""
    print("Testing command-line overrides...")
    
    cli = ConfigCLI(TestConfig)
    
    # Test with overrides
    from collections.abc import Iterator
    from typing import Mapping
    
    overrides: Iterator[Mapping[str, object]] = iter([
        {
            "name": "override_test",
            "value": 999,
            "enabled": False,
            "items": ["override1", "override2"],
            "nested.x": 100,
        }
    ])
    
    args = Mock()
    args.config_file = None
    args.config_overrides = overrides
    
    config = cli.load_config(args)
    
    assert config.name == "override_test"
    assert config.value == 999
    assert config.enabled is False
    assert config.items == ["override1", "override2"]
    assert config.nested == {"x": 100, "y": 2}  # y should remain from default
    
    print("✓ Command-line overrides test passed")


def test_config_dumping() -> None:
    """Test configuration dumping to YAML."""
    print("Testing configuration dumping...")
    
    cli = ConfigCLI(TestConfig)
    config = TestConfig()
    
    # Test dumping to string
    import io
    output = io.StringIO()
    cli.dump_config(config, output)
    
    dumped_content = output.getvalue()
    assert "name: test" in dumped_content
    assert "value: 42" in dumped_content
    assert "enabled: true" in dumped_content
    
    print("✓ Configuration dumping test passed")


def test_error_handling() -> None:
    """Test error handling scenarios."""
    print("Testing error handling...")
    
    cli = ConfigCLI(TestConfig)
    
    # Test non-existent file
    args = Mock()
    args.config_file = Path("/non/existent/file.yaml")
    args.config_overrides = None
    
    try:
        cli.load_config(args)
        assert False, "Should have raised ConfigLoadError"
    except ConfigLoadError:
        print("✓ Non-existent file error handling passed")
    
    # Test invalid YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_file = Path(f.name)
    
    try:
        args.config_file = temp_file
        try:
            cli.load_config(args)
            assert False, "Should have raised ConfigLoadError"
        except ConfigLoadError:
            print("✓ Invalid YAML error handling passed")
    finally:
        temp_file.unlink()


def test_argument_parsing() -> None:
    """Test argument parsing functionality."""
    print("Testing argument parsing...")
    
    cli = ConfigCLI(TestConfig)
    
    # Test with various argument combinations
    test_cases = [
        ["--dump-config"],
        ["--config-file", "test.yaml", "--dump-config"],
        ["--config", "name=test_override", "--config", "value=123"],
        ["--config-file", "test.yaml", "--config", "enabled=false"],
    ]
    
    for args in test_cases:
        parsed_args = cli.parse_args(args)
        assert parsed_args is not None
        print(f"✓ Parsed args: {args}")
    
    print("✓ Argument parsing test passed")


def main() -> None:
    """Run all tests."""
    print("=== ConfigCLI Test Suite ===\n")
    
    try:
        test_default_config()
        test_yaml_file_loading()
        test_command_line_overrides()
        test_config_dumping()
        test_error_handling()
        test_argument_parsing()
        
        print("\n=== All Tests Passed! ===")
        
    except Exception as ex:
        print(f"\n✗ Test failed: {ex}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
