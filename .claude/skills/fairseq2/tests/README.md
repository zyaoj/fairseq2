# fairseq2 Skill Tests

This directory contains tests for the skill maintenance scripts.

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_config.py -v

# Run with coverage
python -m pytest tests/ --cov=scripts --cov-report=html
```

## Test Files

| File | Purpose |
|------|---------|
| `test_config.py` | Configuration loading tests |
| `test_utils.py` | Utility function tests |
| `test_update_index.py` | Index synchronization tests |
| `test_update_links.py` | Link maintenance tests |
| `test_edge_cases.py` | Skill validation tests |

## Adding New Tests

1. Create a new test file following the `test_*.py` naming convention
2. Import from `scripts/` using relative imports
3. Use pytest fixtures for common setup
4. Run tests to verify they pass

## Test Coverage Goals

- Configuration loading: 100%
- Utility functions: 90%+
- Script functionality: 80%+
