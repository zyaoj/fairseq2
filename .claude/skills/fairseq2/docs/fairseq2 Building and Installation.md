---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - installation
  - build
---
# Building and Installation


This document provides comprehensive guidance for installing fairseq2 from pre-built packages or building from source. It covers installation options, build system architecture, and the CI/CD distribution pipeline. For architectural details about the package structure and dependencies, see fairseq2 Package System. For development workflows and contribution guidelines, see fairseq2 Development and CI-CD. For the broader system context, see fairseq2 Core Architecture.

## Installation Options Overview

fairseq2 can be installed via:

1. **PyPI packages**: Simplest option, compatible with PyPI PyTorch (currently CUDA 12.8)
2. **FAIR S3 repository**: Multiple PyTorch versions and CUDA variants
3. **Building from source**: Required for unsupported platforms or custom builds

fairseq2 consists of two packages:

* **fairseq2**: Pure Python package with models, recipes, and APIs
* **fairseq2n**: Native C++/CUDA extension with performance-critical operations

Both packages must match exactly in version and must be compatible with the installed PyTorch version due to PyTorch C++ API's lack of ABI compatibility between releases.

## Pre-built Package Installation

### System Dependencies

fairseq2 requires `libsndfile` for audio processing:

**Linux (Ubuntu/Debian):**

**Linux (Fedora):**

**macOS:**

**Sources:** README.md44-60 README.md167-173

### Installing from PyPI

The simplest installation for systems with standard configurations:

**Linux x86-64:**

**macOS ARM64 (Apple Silicon):**

This installs fairseq2 built for the PyTorch version hosted on PyPI (currently 2.9.1 with CUDA 12.8).

**Not supported:** ARM-based Linux (Raspberry Pi, NVIDIA Jetson), Intel-based macOS. These require building from source.

**Sources:** README.md62-67 README.md176-180 setup.py52-72

### Installing from FAIR's S3 Repository

FAIR hosts pre-built packages for multiple PyTorch and CUDA versions:

| fairseq2 Version | PyTorch Versions | Python Versions | Variants | Architecture |
| --- | --- | --- | --- | --- |
| `HEAD` (nightly) | 2.9.1, 2.8.0, 2.7.1 | 3.10, 3.11, 3.12 | cpu, cu126, cu128 | x86\_64 (Linux) |
| `HEAD` (nightly) | 2.9.1 | 3.10, 3.11, 3.12 | cpu | arm64 (macOS) |
| `0.6` (stable) | 2.8.0, 2.7.1 | 3.10, 3.11, 3.12 | cpu, cu126, cu128 | x86\_64 (Linux) |

**Variant naming:** `cuXYZ` refers to CUDA XY.Z (e.g., `cu128` = CUDA 12.8)

**Installation steps (example: PyTorch 2.9.1, CUDA 12.6):**

1. Install PyTorch following instructions at pytorch.org:
2. Install fairseq2:

**Critical Warning:** fairseq2 uses PyTorch's C++ API which has **no ABI compatibility** between releases. You must install the fairseq2 variant that **exactly matches** your PyTorch version. Mismatches cause immediate crashes or segfaults.

**Sources:** README.md77-150 README.md189-237

### Nightly Builds

For the latest development version:

**Linux (example: PyTorch 2.9.1, CUDA 12.8):**

**macOS ARM64 (example: PyTorch 2.9.1):**

**Sources:** README.md152-163 README.md239-248

### Windows Installation

fairseq2 does not have native Windows support. Use **Windows Subsystem for Linux (WSL 2)** with full CUDA support, then follow Linux installation instructions.

**Sources:** README.md251-257

## Building from Source

### Prerequisites

**Python Requirements:**

**Compiler Requirements:**

* **Linux:** GCC 11+ or Clang (GCC toolset 11 used in CI)
* **macOS:** Xcode command-line tools

**CUDA Requirements (optional):**

**Sources:** native/CMakeLists.txt7-9 native/CMakeLists.txt174-180 native/python/requirements-build.txt1-9

### Build Process Overview

### Step-by-Step Instructions

#### 1. Clone Repository

#### 2. Install Build Dependencies

This installs `cmake~=3.31`, `ninja~=1.11`, `numpy~=2.2`, `setuptools~=80.9`, `tbb-devel==2021.8` (x86\_64 only), `torch>=2.7`, and `wheel~=0.45`.

**Sources:** native/python/requirements-build.txt1-9

#### 3. Configure fairseq2n with CMake

**Key CMake Options:**

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `CMAKE_BUILD_TYPE` | `Release`, `Debug`, `RelWithDebInfo` | `RelWithDebInfo` | Build configuration |
| `FAIRSEQ2N_USE_CUDA` | `ON`, `OFF` | `OFF` | Build CUDA kernels |
| `FAIRSEQ2N_PERFORM_LTO` | `ON`, `OFF` | `OFF` | Link-time optimization |
| `FAIRSEQ2N_PYTHON_DEVEL` | `ON`, `OFF` | `ON` | Copy extension to source tree |
| `FAIRSEQ2N_BUILD_FOR_NATIVE` | `ON`, `OFF` | `OFF` | Optimize for host CPU |
| `FAIRSEQ2N_THREAD_LIB` | `""`, `"tbb"` | `"tbb"` (x86\_64) | Threading library |
| `FAIRSEQ2N_SANITIZERS` | `""`, `"asan"`, `"ubsan"`, `"tsan"` | `""` | Enable sanitizers |
| `FAIRSEQ2N_SUPPORT_IMAGE` | `ON`, `OFF` | `ON` | JPEG/PNG decoding |
| `FAIRSEQ2N_TREAT_WARNINGS_AS_ERRORS` | `ON`, `OFF` | `OFF` | Fail build on warnings |
| `CMAKE_CUDA_ARCHITECTURES` | CUDA arch list | `70-real 70-virtual` | Target GPU architectures |

**Notes:**

**Sources:** native/CMakeLists.txt42-152 native/CMakeLists.txt221-225

#### 4. Build fairseq2n

For parallel builds:

**Sources:** .github/workflows/\_build\_wheel-linux.yaml85-125

#### 5. Package fairseq2n

The `install_cmake` command (defined at native/python/setup.py43-130) integrates CMake artifacts into the Python package.

For Linux, specify platform tag:

**Sources:** .github/workflows/\_build\_wheel-linux.yaml126-136 .github/workflows/\_build\_wheel-macos.yaml71-79

#### 6. Install fairseq2n

#### 7. Package fairseq2

**Sources:** .github/workflows/\_build\_wheel-linux.yaml137-139 .github/workflows/\_build\_wheel-macos.yaml80-82

#### 8. Install fairseq2

### Development Installation

For active development, use editable installations to avoid rebuilding after Python changes:

#### Option 1: Python-only Development

If only modifying Python code (not C++/CUDA):

**Sources:** CONTRIBUTING.md6-60

#### Option 2: Full Development (C++/CUDA)

If modifying native code:

With `FAIRSEQ2N_PYTHON_DEVEL=ON`, CMake copies the extension module to `native/python/src/fairseq2n/`, enabling `pip install -e` to work.

**Development tools** (requirements-devel.txt1-14):

* `black~=25.1`: Code formatter
* `isort~=6.0`: Import sorter
* `flake8~=7.1`: Linter
* `mypy~=1.15`: Type checker
* `pytest~=8.4`: Test framework

**Sources:** CONTRIBUTING.md6-60 native/CMakeLists.txt143-152

## Build System Architecture

### Two-Tier Package Structure

**fairseq2** (pure Python):

**fairseq2n** (native extension):

**Sources:** setup.py23-82 native/python/setup.py132-173 native/CMakeLists.txt1-334

### CMake Build Configuration

The native build is orchestrated by native/CMakeLists.txt1-334:

#### Project Definition

Version must be synchronized with Python packages using tools/set-project-version.sh1-100

**Sources:** native/CMakeLists.txt7-9

#### Build Options

All configurable options at native/CMakeLists.txt42-152:

#### Dependency Resolution

Dependencies found at native/CMakeLists.txt164-216:

1. **Iconv**: Character encoding (required)
2. **SndFile**: Audio I/O (required)
3. **Threads**: pthread support (required)
4. **TBB**: Intel oneTBB ≥2021.8 (x86\_64 only, if `FAIRSEQ2N_THREAD_LIB="tbb"`)
5. **Torch**: PyTorch C++ API ≥1.13 (required)
6. **Python3**: CPython ≥3.8 with development headers (if bindings enabled)

Third-party libraries built from source:

**Sources:** native/CMakeLists.txt164-216

#### CUDA Configuration

CUDA support configured at native/CMakeLists.txt221-248:

CI builds for architectures: `70-real;80-real;80-virtual` (Volta + Ampere).

**Sources:** native/CMakeLists.txt221-248 .github/workflows/\_build\_wheel-linux.yaml92-94

#### Installation Configuration

Installation paths at native/CMakeLists.txt254-263:

Standalone mode (default) uses relative rpaths for bundled distribution.

**Sources:** native/CMakeLists.txt254-263

### Python Packaging Integration

#### fairseq2n Setup

Custom `install_cmake` command at native/python/setup.py43-130 bridges setuptools and CMake:

Installs CMake-built artifacts into Python package directory.

**Strict PyTorch version dependency** at native/python/setup.py163-172:

**Sources:** native/python/setup.py43-173

#### fairseq2 Setup

Version coordination at setup.py11-21:

Development versions allow range for nightly fairseq2n; release versions require exact match.

**Package data** includes asset cards at setup.py46-49:

**Sources:** setup.py11-82

### Version Synchronization

Version must be synchronized across 6 files. The tools/set-project-version.sh1-100 script automates this:

Updates:

1. VERSION1 - Single source of truth
2. setup.py11 - `version = "..."`
3. src/fairseq2/\_\_init\_\_.py17 - `__version__ = "..."`
4. native/CMakeLists.txt9 - `project(... VERSION ...)`
5. native/python/setup.py139 - `version="..."`
6. native/python/src/fairseq2n/\_\_init\_\_.py9 - `__version__ = "..."`

For variant-specific native versions:

Updates only native package files (items 4-6 above).

**Sources:** tools/set-project-version.sh1-100

## CI/CD Distribution Pipeline

### Build Matrix

CI builds wheels for multiple configurations:

**Linux x86\_64 combinations:** 3 PyTorch × 3 Python × 3 Variants = 27 wheels per build
**macOS arm64 combinations:** 1 PyTorch × 3 Python × 1 Variant = 3 wheels per build

**Sources:** .github/workflows/\_build\_wheels.yaml1-144 .github/workflows/\_publish.yaml1-129

### Build Workflow (Linux)

The Linux build workflow at .github/workflows/\_build\_wheel-linux.yaml1-263 executes:

**Key steps:**

1. **Environment setup** .github/workflows/\_build\_wheel-linux.yaml52-67:

   * manylinux\_2\_28 container with GCC toolset 11
   * Python venv creation
   * PyTorch installation from pytorch.org
2. **Version management** .github/workflows/\_build\_wheel-linux.yaml68-84:

   * Apply version override if provided
   * Label native package with variant (e.g., `0.8.0+cu128`)
3. **CMake configuration** .github/workflows/\_build\_wheel-linux.yaml85-125:
4. **Packaging** .github/workflows/\_build\_wheel-linux.yaml126-139:

   * manylinux wheel with platform tag `manylinux_2_28_x86_64`
   * Both fairseq2n and fairseq2 packages created

**Sources:** .github/workflows/\_build\_wheel-linux.yaml1-149

### Build Workflow (macOS)

The macOS workflow at .github/workflows/\_build\_wheel-macos.yaml1-140 differs:

**Sources:** .github/workflows/\_build\_wheel-macos.yaml1-92

### Testing Workflow

Tests run after build in .github/workflows/\_build\_wheel-linux.yaml150-263:

1. **Native tests** .github/workflows/\_build\_wheel-linux.yaml226-233:
2. **Python tests** .github/workflows/\_build\_wheel-linux.yaml234-249:
3. **Sanitizer checks** .github/workflows/\_build\_wheel-linux.yaml250-262:

   * Check LSan output for memory leaks
   * Grep for "fairseq2" symbols (Python leaks ignored)

**Integration tests** enabled only for one configuration per PyTorch version (controlled by matrix).

**Sources:** .github/workflows/\_build\_wheel-linux.yaml150-263

### Docker Build Environment

Containers defined in ci/docker/manylinux\_x86\_64/:

**Base image:** manylinux\_2\_28 (glibc 2.28)
**GCC Toolset:** 11
**Variants:** cpu, cu124, cu126, cu128

CUDA installation script ci/docker/manylinux\_x86\_64/build-scripts/install-cuda-12.8.sh1-23:

Container build script ci/docker/build-manylinux-images.sh1-32:

**Sources:** ci/docker/build-manylinux-images.sh1-32 ci/docker/manylinux\_x86\_64/Dockerfile.cu1281-15

### Distribution to S3

S3 publishing workflow at .github/workflows/\_publish\_s3.yaml1-84:

**URL structure:**

**Process:**

1. Download wheel artifacts from staging
2. Configure AWS credentials (OIDC)
3. Upload to S3 bucket
4. Update PEP 503 index with `ci/scripts/update_pep503_index.py`

**Sources:** .github/workflows/\_publish\_s3.yaml1-84

### Distribution to PyPI

PyPI publishing workflow at .github/workflows/\_publish\_pypi.yaml1-59:

**Restrictions:**

* `skip-existing: true` handles duplicate uploads

**Publishing sequence:**

1. Linux wheels (fairseq2n + fairseq2)
2. macOS wheels (fairseq2n + fairseq2)
3. Digital attestation disabled (plugin issue)

**Sources:** .github/workflows/\_publish\_pypi.yaml1-59 .github/workflows/\_publish.yaml79-118

## Troubleshooting

### PyTorch Version Mismatch

The most common issue is ABI incompatibility between PyTorch and fairseq2n.

**Detection:** fairseq2n checks at import native/python/src/fairseq2n/\_\_init\_\_.py172-195:

**Error symptoms:**

* "Symbol not found" errors

**Solution:**

1. Check PyTorch version: `python -c "import torch; print(torch.__version__)"`
2. Install matching fairseq2 variant
3. Or rebuild fairseq2n with current PyTorch

**Sources:** native/python/src/fairseq2n/\_\_init\_\_.py172-195

### Shared Library Loading Failures

fairseq2n loads required libraries at import native/python/src/fairseq2n/\_\_init\_\_.py79-169

**Missing libsndfile:**

```python
OSError: fairseq2 requires libsndfile
```

**Solutions:**

* **Conda:** `conda install -c conda-forge libsndfile==1.0.31`
* **Ubuntu/Debian:** `sudo apt install libsndfile1`
* **macOS:** `brew install libsndfile`

**Missing Intel oneTBB (x86\_64):**

```python
OSError: fairseq2 requires Intel oneTBB
```

**Solution:** `pip install tbb>=2021.8`

**Library search order:**

1. System library paths (LD\_LIBRARY\_PATH, dyld paths)
2. Homebrew paths (macOS): `/usr/local/lib`, `/opt/homebrew/lib`
3. Python site-packages

**Sources:** native/python/src/fairseq2n/\_\_init\_\_.py79-169

### Build Failures

#### CUDA Version Mismatch

CMake enforces CUDA compatibility native/CMakeLists.txt237-247:

**Solution:** Install CUDA Toolkit matching PyTorch:

**Sources:** native/CMakeLists.txt237-247

#### Missing Conda Compilers

In Conda environments native/CMakeLists.txt15-19:

**Solution:**

**Sources:** native/CMakeLists.txt15-19

#### Link-Time Optimization Failures

LTO and sanitizers conflict. CI disables LTO when sanitizers enabled .github/workflows/\_build\_wheel-linux.yaml100-110:

**Solution:** Set `FAIRSEQ2N_PERFORM_LTO=OFF` when using sanitizers.

**Sources:** .github/workflows/\_build\_wheel-linux.yaml100-110

### Development Environment Issues

#### Nightly Package Unavailable

After pulling latest commits, nightlies might not be published CONTRIBUTING.md53-59

**Solution:**

#### Editable Install Not Working

With `FAIRSEQ2N_PYTHON_DEVEL=OFF`, extension module not copied to source tree.

**Solution:** Rebuild with `FAIRSEQ2N_PYTHON_DEVEL=ON`:

**Sources:** native/CMakeLists.txt143-152 CONTRIBUTING.md6-44

---

**Sources:**

* .github/workflows/\_build\_wheels.yaml1-144
* .github/workflows/\_build\_wheel-linux.yaml1-263
* .github/workflows/\_build\_wheel-macos.yaml1-140
* .github/workflows/\_publish.yaml1-129
* .github/workflows/\_publish\_s3.yaml1-84
* .github/workflows/\_publish\_pypi.yaml1-59

---

## Related

- fairseq2 Core Architecture
- fairseq2 Package System
- fairseq2 Development and CI-CD
- fairseq2 Runtime Infrastructure