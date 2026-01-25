---
myst:
  html_meta:
    "description lang=en": "fairseq2 Core Architecture"
    "keywords": "fairseq2, architecture, documentation"
---

# Core Architecture


This document provides an overview of the fundamental architectural components that make up fairseq2. The architecture follows a modular design with several core subsystems that enable distributed training, efficient data processing, and comprehensive model management.

## System Overview

Fairseq2's architecture consists of interconnected components designed for scalability, modularity, and ease of use. The system enables working with large-scale sequence models across distributed environments.

**Core Architecture Layers**

The architecture is organized into the following main areas:

* **Package System**: Two-package architecture (`fairseq2` and `fairseq2n`) with Python and native components
* **Runtime Infrastructure**: Dependency injection, device/dtype management, and thread-local context
* **Distributed Processing with Gang**: Abstraction layer for distributed communication
* **Data Processing Pipeline**: Streaming data processing with native backend
* **Asset Management**: Centralized management of models, tokenizers, and datasets

Sources:

## Package System Overview

Fairseq2 follows a two-package architecture that separates Python interfaces from high-performance native implementations. This design enables efficient computation while maintaining Python's ease of use. The system is distributed via PyPI (stable releases) and S3 (nightly builds with multiple CUDA variants). See fairseq2 Package System for complete details.

**Package Architecture and Distribution**

### Package Components

| Package | Purpose | Key Modules | Build System |
| --- | --- | --- | --- |
| `fairseq2` | Python interface and high-level APIs | `models/`, `recipes/`, `data/`, `nn/`, `assets/` | setuptools |
| `fairseq2n` | Native implementations | C++ pipeline, CUDA kernels, bindings | CMake + setuptools |

### Version Compatibility

**Critical**: fairseq2 and fairseq2n versions must exactly match the PyTorch version due to C++ API/ABI incompatibility between PyTorch releases. The build matrix supports:

The package version is set via tools/set-project-version.sh1-100 which updates version strings across both packages.

Sources:

* .github/workflows/\_publish.yaml1-129
* .github/workflows/\_build\_wheels.yaml1-144
## Runtime Infrastructure Overview

Before discussing distributed processing and other systems, it's important to understand fairseq2's runtime infrastructure, which provides foundational services used throughout the codebase.

**Runtime Infrastructure Components**

### Dependency Injection System

The `DependencyContainer` in src/fairseq2/runtime/dependency.py provides service registration and resolution. All major components are registered in src/fairseq2/composition/lib.py115-260. See Dependency Injection (§ Dependency Injection System) for implementation details. Key registrations include:

### Device and DataType Management

The `DeviceContext` (src/fairseq2/device.py106-139) and `DataTypeContext` (src/fairseq2/data\_type.py87-128) provide thread-local management of PyTorch devices and data types through context managers. See Device Management (§ Device Context Management) and DataType Management (§ Data Type Context Management) for complete documentation:

The device detection logic (src/fairseq2/device.py141-247) checks environment variables in this order:

1. `FAIRSEQ2_DEVICE` - explicit device override
2. `CUDA_VISIBLE_DEVICES` - if single device
3. `LOCAL_RANK` - for distributed jobs
4. CPU fallback

### Thread-Local Storage

The `ThreadLocalStorage` interface (src/fairseq2/utils/threading.py23-42) provides thread-safe storage for context stacks. The `_DataTypeModeStack` (src/fairseq2/data\_type.py130-187) uses PyTorch's `TorchFunctionMode` to intercept tensor constructors and apply the current dtype.

Sources:

## Distributed Processing Overview

The Gang system provides fairseq2's foundation for distributed computing. Detailed documentation is provided in fairseq2 Gang System and fairseq2 Distributed Training.

**Gang System Architecture**

### Gang Components

* **`Gang` (ABC)**: Abstract interface defining collective operations (src/fairseq2/gang.py36-126)
* **`ProcessGroupGang`**: PyTorch ProcessGroup wrapper (src/fairseq2/gang.py147-266)
* **`FakeGang`**: Single-process simulation for testing (src/fairseq2/gang.py269-491)
* **`Gangs`**: Container organizing gangs for different parallelism strategies (src/fairseq2/gang.py504-667)

The Gang system is managed via `GangContext` (src/fairseq2/gang.py796-812), which provides thread-local gang access similar to device and dtype contexts.

Sources:

## Data Processing Overview

Fairseq2's data processing system provides efficient streaming data processing through the DataPipeline architecture. The system has a Python API backed by high-performance C++ implementations in fairseq2n. Detailed documentation is in fairseq2 Data Pipeline.

**Data Pipeline Architecture**

### Pipeline Components

* **`DataPipelineBuilder`**: Fluent API for pipeline construction with method chaining
* **Source operations**: `read_sequence()`, `read_iterator()`, `list_files()`, `read_zipped_records()`
* **Transform operations**: `map()`, `filter()`, `shuffle()`, `bucket()`, `collate()`, `prefetch()`
* **Combination strategies**: `concat()` (sequential), `round_robin()` (alternating), `sample()` (weighted), `zip()` (parallel)
* **Distributed support**: `shard()` for data parallelism, `repeat()` for multi-epoch training
* **Native backend**: C++ implementation in fairseq2n for performance, with state management for checkpointing

The pipeline is lazily evaluated (operations execute only during iteration) and supports state persistence for fault tolerance.

Sources:

## Asset Management Overview

Fairseq2 provides a comprehensive asset management system for models, tokenizers, and datasets through the `AssetStore` and family-based abstraction. This system handles discovery, downloading, caching, and loading of pretrained resources. Detailed documentation is in fairseq2 Asset Management.

**Asset Discovery and Loading Pipeline**

### Asset Components

* **`AssetStore`**: Central registry for asset discovery from multiple providers
* **Asset Metadata Providers**: `WellKnownAssetMetadataProvider`, `PackageAssetMetadataProvider`, `FileAssetMetadataProvider`, `InMemoryAssetMetadataProvider`
* **Family Abstraction**: `ModelFamily`, `TokenizerFamily`, `DatasetFamily` provide type-specific loading logic
* **Download Manager**: `StandardDownloadManager` with HTTP/HTTPS and Hugging Face Hub support
* **Checkpoint Loading**: `ModelCheckpointLoader` with converters for framework compatibility (e.g., `_LLaMACheckpointLoader`)
* **Model Sharder**: `ModelSharder` distributes models across gangs for tensor parallelism

The system supports environment-based configuration (e.g., `model_name@cuda` vs `model_name@cpu`) and hierarchical config overrides.

Sources:

## CLI and Recipe Execution

Fairseq2 provides a CLI framework for executing training and inference recipes with comprehensive error handling and configuration management.

**v0.7 Update**: The recipe system has evolved significantly. Recipes are now kept **outside** the core library for better modularity. Users should copy and customize recipes for research projects rather than relying on pip-installed versions. The library supports two usage modes: **Library** (pip-install for APIs) vs **Framework** (clone repo and hack recipes).

**Recipe Execution Flow**

### Recipe Components

* **`main(recipe)`**: Entry point at src/fairseq2/recipe/cli.py154-183
* **`_parse_args()`**: Parses `--config-file`, `--config`, `--output-dir`, `--dump-config` arguments (src/fairseq2/recipe/cli.py235-288)
* **`_register_library()`**: Registers all core services in `DependencyContainer` (src/fairseq2/composition/lib.py115-260)
* **`_RecipeConfigLoader`**: Loads and merges YAML config files with command-line overrides (src/fairseq2/recipe/cli.py384-488)
* **`_handle_errors()`**: Comprehensive exception handling with 20+ specific error types (src/fairseq2/recipe/cli.py291-359)
* **Error handlers**: Registered at src/fairseq2/recipe/cli.py510-563 for recipe-specific exceptions

The framework supports:

Sources:

## Design Patterns

Fairseq2 uses several key design patterns throughout its architecture:

### Thread-Local Context Management

The runtime infrastructure uses thread-local context managers for device, dtype, and gang management (see Thread-Local Storage (§ Thread-Local Storage)). This pattern eliminates the need to pass these objects through function calls:

Implementation via `ThreadLocalStorage` (src/fairseq2/utils/threading.py23-42) and context-specific stacks (src/fairseq2/data\_type.py130-187).

### Dependency Injection

All major services are registered in a `DependencyContainer` (see Dependency Injection (§ Dependency Injection System)) (src/fairseq2/composition/lib.py115-260):

This enables flexible composition and testing without tight coupling.

### Family-Based Abstraction

Models, tokenizers, and datasets use a family-based abstraction pattern where each asset type has:

This enables extensibility through registration rather than modification.

### Native Backend with Python Wrapper

Performance-critical code (data pipeline, custom ops) is implemented in C++/CUDA (fairseq2n) with Python bindings via pybind11. The Python layer provides type hints and documentation while C++ handles execution. See fairseq2 Package System for build architecture.

### Fluent API Design

The DataPipelineBuilder uses method chaining for pipeline construction:

This provides an intuitive API while maintaining lazy evaluation.

Sources:

## Integration and Workflow

The various components of fairseq2's architecture come together to support the end-to-end workflow for model training, evaluation, and inference (see fairseq2 Training System and fairseq2 Recipes and CLI).

This integration is orchestrated by the recipes system, which provides high-level APIs for common workflows while leveraging the underlying architecture for efficient execution.

When building applications with fairseq2, most developers will interact primarily with these higher-level APIs, with the core architecture providing the foundation for efficient, distributed model operations.

Sources:
