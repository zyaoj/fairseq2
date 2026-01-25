---
myst:
  html_meta:
    "description lang=en": "fairseq2 Package System"
    "keywords": "fairseq2, architecture, documentation"
---

# Package System


This document describes the two-tier package architecture of fairseq2, consisting of the user-facing `fairseq2` Python package and the performance-critical `fairseq2n` native extension. It covers package structure, version coordination, the build system, dependencies, and distribution channels. For information about building from source, see fairseq2 Building and Installation. For deployment and CI/CD details, see fairseq2 Development and CI-CD. For the broader system context, see fairseq2 Core Architecture.

## Overview

fairseq2 employs a dual-package architecture that separates user-facing Python code from performance-critical native implementations:

**Sources:** setup.py1-82 native/python/setup.py1-173 src/fairseq2/\_\_init\_\_.py1-58 native/python/src/fairseq2n/\_\_init\_\_.py1-196

The separation provides:

* **Clean API**: Python package offers intuitive interfaces for models, data pipelines, and training
* **High performance**: Native package implements compute-intensive operations in C++ and CUDA
* **Modularity**: Users modify Python code without recompiling native components (when using pre-built binaries)
* **ABI safety**: Strict version coordination prevents crashes from binary incompatibilities

## Package Structure

### fairseq2 Python Package

The `fairseq2` package is implemented in pure Python and provides the user-facing API:

| Directory | Purpose |
| --- | --- |
| `src/fairseq2/` | Main package root |
| `src/fairseq2/models/` | Model architecture definitions (LLaMA, Wav2Vec2, etc.) |
| `src/fairseq2/data/` | Data pipeline Python wrappers and utilities |
| `src/fairseq2/nn/` | Neural network building blocks |
| `src/fairseq2/recipes/` | Training recipes and CLI framework |
| `src/fairseq2/assets/` | Asset management system |
| `src/fairseq2/assets/cards/` | Built-in asset metadata (YAML files) |

The package is configured via `setup.py`:

**Sources:** setup.py23-82

#### Version Specification for fairseq2n Dependency

The dependency on `fairseq2n` uses special logic to handle development vs. release versions:

* **Development builds** (`.dev0`): Allow any nightly `fairseq2n` from the same base version up to the next release
* **Release builds**: Require exact version match (excluding local labels after `+`)

This ensures development flexibility while maintaining strict version coordination for releases.

**Sources:** setup.py11-21

### fairseq2n Native Package

The `fairseq2n` package contains C++/CUDA implementations and Python bindings:

| Component | Location | Purpose |
| --- | --- | --- |
| Python bindings | `fairseq2n/bindings.so` | pybind11-generated Python extension module |
| Shared library | `fairseq2n/lib/libfairseq2n.so` (Linux) `fairseq2n/lib/libfairseq2n.dylib` (macOS) | Core C++ implementation |
| Headers | `fairseq2n/include/` | C++ headers for extension development |
| CMake config | `fairseq2n/lib/cmake/` | CMake package configuration |

The package uses a custom `install_cmake` command to integrate CMake artifacts into the Python distribution:

**Sources:** native/python/setup.py18-130

The `install_cmake` command:

1. Reads `FAIRSEQ2N_INSTALL_STANDALONE` from CMake cache to determine whether to bundle the shared library
2. Invokes `cmake --install` to copy artifacts to the installation directory
3. Extracts file lists from CMake install manifests for setuptools bookkeeping

**Sources:** native/python/setup.py43-129

## Version Coordination and ABI Compatibility

### Critical Importance of Version Matching

fairseq2n depends on PyTorch's C++ API (`libtorch`), which has **no ABI compatibility between releases**. This means:

**Sources:** native/python/setup.py163-172 native/python/src/fairseq2n/\_\_init\_\_.py172-195 README.md144-150

### Runtime Version Verification

fairseq2n checks version compatibility at import time:

The version check compares:

* **Major.minor.patch** versions (ignoring local labels after `+`)
* **CUDA variant** (CPU-only, CUDA 12.6, CUDA 12.8, etc.)

This prevents silent failures by failing fast at import time.

**Sources:** native/python/src/fairseq2n/\_\_init\_\_.py172-195

### Version Specification in Dependencies

fairseq2n's `setup.py` enforces exact PyTorch version matching:

The version is extracted from the PyTorch package used during the build process, ensuring the installed PyTorch matches the build-time PyTorch.

**Sources:** native/python/setup.py163-172

## Build System Architecture

### CMake for fairseq2n

fairseq2n uses CMake as its primary build system, providing extensive configurability:

**Sources:** native/CMakeLists.txt1-334

#### Key Build Options

| Option | Default | Description |
| --- | --- | --- |
| `FAIRSEQ2N_BUILD_FOR_NATIVE` | OFF | Enable processor-specific optimizations (e.g., AVX-512) |
| `FAIRSEQ2N_INSTALL_STANDALONE` | ON | Install with relative rpaths for bundled dependencies |
| `FAIRSEQ2N_PERFORM_LTO` | OFF | Enable link-time optimization (disabled with sanitizers) |
| `FAIRSEQ2N_SANITIZERS` | "" | Enable sanitizers: `asan`, `ubsan`, `tsan` |
| `FAIRSEQ2N_USE_CUDA` | OFF | Build CUDA kernels (requires CUDA Toolkit) |
| `FAIRSEQ2N_THREAD_LIB` | `tbb` (x86\_64) | Threading library (Intel oneTBB for x86\_64) |
| `FAIRSEQ2N_BUILD_PYTHON_BINDINGS` | ON | Build Python extension module |
| `FAIRSEQ2N_PYTHON_DEVEL` | ON | Copy extension to source tree for editable installs |

**Sources:** native/CMakeLists.txt42-152

#### CUDA Support

When `FAIRSEQ2N_USE_CUDA=ON`:

The build system:

1. Verifies installed PyTorch has CUDA support
2. Checks CUDA Toolkit version matches PyTorch's CUDA version (major.minor)
3. Enables CUDA language in CMake
4. Builds CUDA kernels for specified architectures

**Sources:** native/CMakeLists.txt221-248

### setuptools Integration

The Python packages use setuptools, with `fairseq2n` wrapping CMake:

**Sources:** setup.py23-82 native/python/setup.py18-173

For fairseq2n, the `install_cmake` command bridges setuptools and CMake:

1. **Pre-build**: CMake must be run externally (or by CI/build scripts)
2. **Installation**: `install_cmake` reads the CMake build directory and installs artifacts
3. **Manifest tracking**: Extracts installed file lists from CMake manifests for setuptools

This approach allows:

**Sources:** native/python/setup.py43-129

## Dependencies

### fairseq2 Python Dependencies

The `fairseq2` package has ~30 direct dependencies:

| Category | Packages |
| --- | --- |
| **Core** | `fairseq2n` (exact version), `torch` (via fairseq2n) |
| **Data/Text** | `editdistance`, `sacrebleu`, `tiktoken`, `sentencepiece` (via fairseq2n) |
| **ML Ecosystem** | `huggingface_hub`, `transformers`, `safetensors`, `torcheval` |
| **Configuration** | `ruamel.yaml`, `mypy-extensions`, `packaging`, `typing_extensions` |
| **Monitoring** | `tensorboard`, `wandb`, `rich` |
| **Utilities** | `psutil`, `importlib_metadata`, `importlib_resources` |
| **Optional (arrow)** | `pyarrow`, `pandas`, `polars`, `xxhash`, `retrying` |

**Sources:** setup.py52-81

### fairseq2n Native Dependencies

#### Required System Libraries

**Sources:** native/CMakeLists.txt164-215 native/python/setup.py163-172

#### Shared Library Loading

fairseq2n implements custom library loading logic to handle non-standard installation locations:

The loading order ensures:

1. **PyTorch first**: libtorch and libtorch\_python must be in the process before fairseq2n
2. **Global namespace**: Libraries loaded with `RTLD_GLOBAL` to share symbols
3. **Fallback search**: Checks system, Homebrew, and site-packages directories
4. **Error messages**: Provides actionable guidance for missing libraries

**Sources:** native/python/src/fairseq2n/\_\_init\_\_.py79-165

## Distribution Channels

fairseq2 and fairseq2n are distributed through two channels:

### PyPI (Stable Releases Only)

PyPI hosts stable releases for mainstream configurations:

| Package | PyTorch Version | Python Versions | CUDA Variant | Platform |
| --- | --- | --- | --- | --- |
| fairseq2 | 2.9.1 | 3.10, 3.11, 3.12 | cu128 only | Linux x86\_64 |
| fairseq2 | 2.9.1 | 3.10, 3.11, 3.12 | CPU | macOS ARM64 |
| fairseq2n | 2.9.1 | 3.10, 3.11, 3.12 | cu128 only | Linux x86\_64 |
| fairseq2n | 2.9.1 | 3.10, 3.11, 3.12 | CPU | macOS ARM64 |

Installation:

This installs the cu128 variant on Linux (matching PyPI's PyTorch package) or CPU variant on macOS.

**Sources:** README.md62-68 .github/workflows/\_publish.yaml79-118

#### PyPI Publishing Workflow

**Sources:** .github/workflows/\_publish\_pypi.yaml1-59

Key aspects:

* **GitHub OIDC**: Uses trusted publishing (no API tokens)
* **Skip existing**: Multiple CUDA variants attempt to publish the same `fairseq2` package; only the first succeeds
* **Separate packages**: `fairseq2n` and `fairseq2` published independently
* **Attestations disabled**: Digital attestation feature has compatibility issues as of this implementation

**Sources:** .github/workflows/\_publish\_pypi.yaml42-58

### FAIR S3 Repository (All Variants)

FAIR's S3-backed package repository hosts:

* **Nightly builds**: Development versions with `.dev0` suffix
* **Stable releases**: Same as PyPI but with additional CUDA variants
* **Multiple variants**: CPU, CUDA 12.6, CUDA 12.8

**Sources:** .github/workflows/\_publish.yaml15-78 .github/workflows/\_publish\_s3.yaml1-84

Installation from S3:

**Sources:** README.md139-162

#### S3 Publishing Workflow

**Sources:** .github/workflows/\_publish\_s3.yaml30-84

The index update script (`update_pep503_index.py`) maintains PEP 503-compliant simple repository indexes, allowing `pip` to discover available versions.

**Sources:** .github/workflows/\_publish\_s3.yaml78-83

## Version Management

### Version File and Synchronization

All version numbers originate from the `VERSION` file:

```text
VERSION
  → setup.py (version = ...)
  → src/fairseq2/__init__.py (__version__ = ...)
  → native/CMakeLists.txt (project(... VERSION ...))
  → native/python/setup.py (version = ...)
  → native/python/src/fairseq2n/__init__.py (__version__ = ...)
```

**Sources:** VERSION1

The `tools/set-project-version.sh` script synchronizes all version declarations:

**Sources:** tools/set-project-version.sh1-100

### Version Labeling in CI

The CI system applies local version labels to differentiate build variants:

This produces versions like:

* `0.8.0.dev0+cpu` (CPU variant)
* `0.8.0.dev0+cu128` (CUDA 12.8 variant)
* `0.8.0.dev0+cu126.asan_ubsan` (CUDA 12.6 with sanitizers)

**Sources:** .github/workflows/\_build\_wheel-linux.yaml72-84

## Build Variants and Configuration

### CI Build Matrix

The CI system builds multiple configurations:

**Sources:** .github/workflows/\_build\_wheels.yaml1-144 .github/workflows/\_publish.yaml15-78

### Docker Images for Linux Builds

Linux builds use custom manylinux-based Docker images:

| Image | Base | CUDA | Purpose |
| --- | --- | --- | --- |
| `fairseq2-ci-manylinux_x86_64:3-cpu` | manylinux\_2\_28 | None | CPU builds, linting |
| `fairseq2-ci-manylinux_x86_64:3-cu126` | CPU image | 12.6 | CUDA 12.6 builds |
| `fairseq2-ci-manylinux_x86_64:3-cu128` | CPU image | 12.8 | CUDA 12.8 builds |

Each image includes:

**Sources:** ci/docker/build-manylinux-images.sh1-32 ci/docker/manylinux\_x86\_64/Dockerfile.cu1281-15

### Build Configuration Examples

**Release Build (Default for CI):**

**CUDA Build:**

**Development Build (Editable Install):**

**Sources:** .github/workflows/\_build\_wheel-linux.yaml85-125 .github/workflows/\_build\_wheel-macos.yaml56-70

## Installation Workflow

### User Installation Flow

**Sources:** setup.py52-73 src/fairseq2/\_\_init\_\_.py23-57 native/python/src/fairseq2n/\_\_init\_\_.py79-195

### Editable Installation (Development)

For development, fairseq2 supports editable installations:

This allows modifying Python code without reinstalling, while using pre-built native binaries.

**Sources:** CONTRIBUTING.md6-44

For native development:

When `FAIRSEQ2N_PYTHON_DEVEL=ON`, CMake copies the built extension module to the source tree, enabling `pip install -e` without reinstallation after rebuilds.

**Sources:** native/CMakeLists.txt143-152 CONTRIBUTING.md6-14

## Summary

The fairseq2 package system employs a two-tier architecture that balances developer productivity with performance requirements:

| Aspect | fairseq2 | fairseq2n |
| --- | --- | --- |
| **Language** | Pure Python | C++/CUDA |
| **Build System** | setuptools | CMake + setuptools |
| **Distribution** | PyPI + S3 | PyPI + S3 |
| **Variants** | Single (depends on fairseq2n) | Multiple (cpu, cu126, cu128) |
| **Version Coordination** | Requires exact fairseq2n version | Requires exact PyTorch version |
| **Update Frequency** | High (user-facing API) | Low (binary compatibility) |

Critical success factors:

1. **Strict version matching** prevents ABI incompatibilities between fairseq2n and PyTorch
2. **Local version labels** differentiate CUDA variants while maintaining base version
3. **Dual distribution** (PyPI + S3) balances ease of use with flexibility
4. **CMake integration** provides configurability while maintaining standard Python packaging

This architecture enables rapid iteration on model implementations and training recipes (in Python) while maintaining high-performance data pipelines and custom operators (in C++/CUDA).

**Sources:** setup.py1-82 native/python/setup.py1-173 native/CMakeLists.txt1-334 README.md1-286

---

## Related

- fairseq2 Core Architecture
- fairseq2 Building and Installation
- fairseq2 Development and CI-CD
- fairseq2 Runtime Infrastructure
