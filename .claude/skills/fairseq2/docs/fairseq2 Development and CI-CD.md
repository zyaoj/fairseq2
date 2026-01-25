---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - development
  - ci-cd
---
# Development and CI/CD


This document covers the development workflow, testing infrastructure, and CI/CD pipeline for fairseq2. It provides guidance for contributors on setting up a development environment, running tests, and understanding the automated build and release process.

For information about building and installing fairseq2 from source, see fairseq2 Building and Installation. For details about the training infrastructure and recipes, see fairseq2 Training System. For the broader system context, see fairseq2 Core Architecture.

## Development Workflow

fairseq2 development requires setting up both Python and native (C++/CUDA) components. The project supports two development modes: editable Python-only installation for contributors working on Python code, and full source builds for contributors working on native components.

### Setting Up Development Environment

**Python-Only Development (Editable Installation)**

For contributors working exclusively on Python code, fairseq2 provides an editable installation mode that uses pre-built `fairseq2n` nightly packages:

1. Install the nightly `fairseq2n` package matching your PyTorch version:
2. Clone the repository:
3. Install fairseq2 in editable mode:
4. Install development tools:

**Full Source Build**

For contributors working on C++ or CUDA code, or when pre-built packages are unavailable, follow the instructions in Building and Installation to build both `fairseq2` and `fairseq2n` from source.

**Version Compatibility Warning**

The `fairseq2n` package uses PyTorch's C++ API, which has no ABI compatibility between releases. The installed `fairseq2n` version must exactly match the PyTorch version, or the process may crash with segmentation faults. When upgrading PyTorch, always upgrade `fairseq2n` to the corresponding version.

**Development Environment Diagram**

Sources: CONTRIBUTING.md6-59 README.md145-150

### Development Iteration Cycle

When working with an editable installation, Python code changes are immediately reflected without reinstallation. However, when pulling updates from the repository, re-run the `fairseq2n` installation command to get the latest nightly binaries, as they may contain breaking changes or new features required by updated Python code.

Sources: CONTRIBUTING.md54-59

## Testing Infrastructure

fairseq2 has comprehensive testing infrastructure covering both Python and native code, with support for multiple test categories and debugging tools.

### Test Execution

**Python Tests**

Run the full Python test suite using `pytest`:

By default, tests run on CPU. To run tests on a specific device:

**Native C++ Tests**

After building from source, run native tests:

**Integration Tests**

The test suite includes integration tests that are run in CI but can be skipped locally. Use the `--integration` flag to include them:

### Test Categories and CI Configuration

| Test Type | Command | CI Trigger |
| --- | --- | --- |
| Python unit tests | `pytest` | All commits |
| Native C++ tests | `native/build/tests/run-tests` | All commits |
| Integration tests | `pytest --integration` | Selected matrix configurations |
| Sanitizer builds | Build with `-DFAIRSEQ2N_SANITIZERS=asan;ubsan` | Commented out in CI (LSAN issues) |

**Test Execution Flow**

Sources: CONTRIBUTING.md61-86 .github/workflows/\_build\_wheel-linux.yaml227-262 .github/workflows/ci\_build\_wheels.yaml37-43

### Sanitizer Builds

The build system supports Address Sanitizer (ASAN), Undefined Behavior Sanitizer (UBSAN), and Leak Sanitizer (LSAN) for debugging memory issues and undefined behavior in native code.

To build with sanitizers, configure with:

The CI pipeline includes sanitizer configurations but they are currently disabled due to false positives in non-instrumented dependencies. Leak detection uses a suppression file at native/LSan.supp to filter known benign leaks from Python itself.

Sources: .github/workflows/\_build\_wheel-linux.yaml86-110 .github/workflows/\_build\_wheel-linux.yaml198-225 .github/workflows/\_build\_wheel-linux.yaml250-262

## Code Quality and Linting

fairseq2 enforces code quality standards through automated linting and formatting tools for Python, C++, and shell scripts.

### Python Code Quality

**Formatting Tools**

* `isort`: Import statement sorting
* `black`: Code formatting

Run formatters:

**Linting Tools**

* `flake8`: Style guide enforcement
* `mypy`: Static type checking

Run linters:

### C++ Code Quality

**clang-tidy Linting**

For C++ and CUDA code, use `clang-tidy` with the project's configuration:

Alternatively:

The project uses an up-to-date version of the clang toolkit and treats warnings as errors in CI.

### Shell Script Linting

Shell scripts are linted using `shellcheck`:

### CI Problem Matchers

The CI system uses GitHub Actions problem matchers to automatically annotate code with linting issues. Problem matcher configurations are located in ci/problem-matchers/:

* `isort.json`: Import ordering issues
* `black.json`: Formatting issues
* `flake8.json`: Style violations
* `mypy.json`: Type errors
* `gcc.json`: C++ compiler warnings (also used for clang-tidy and shellcheck)

**Code Quality Workflow**

Sources: CONTRIBUTING.md113-161 .github/workflows/\_lint\_py.yaml57-109 .github/workflows/\_lint\_cc.yaml44-70 .github/workflows/\_lint\_sh.yaml36-48

## Contributing Guidelines

While specific contributing guidelines are not directly visible in the provided files, the project structure and configuration suggest standard practices for open-source Python projects.

### Code Quality Standards

The organized module structure with proper `__init__.py` files indicates adherence to Python packaging standards. The comprehensive `.gitignore` configuration shows attention to keeping the repository clean and focused on source code.

### Development Best Practices

* **Modular Design**: Code is organized into logical modules with clear boundaries
* **Clean Repository**: Build artifacts and temporary files are properly excluded
* **Cross-Platform Support**: Configuration accounts for different operating systems (`.DS_Store` for macOS)
* **Native Code Integration**: Support for C/C++ extensions with proper build artifact management

The development infrastructure supports both rapid Python development and performance-critical native code development, reflecting the dual nature of fairseq2 as both a research toolkit and a production-ready system.

Sources: .gitignore1-24 src/fairseq2/models/utils/\_\_init\_\_.py1

---

## Related

- fairseq2 Core Architecture
- fairseq2 Package System
- fairseq2 Building and Installation
- fairseq2 Training System
- fairseq2 Runtime Infrastructure