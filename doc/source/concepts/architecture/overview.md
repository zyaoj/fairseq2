---
myst:
  html_meta:
    "description lang=en": "fairseq2 Overview"
    "keywords": "fairseq2, architecture, documentation"
---

# Overview


## Purpose and Scope

This page provides a high-level introduction to **fairseq2**, Meta's sequence modeling toolkit for training and deploying neural network models for content generation tasks. It covers the project's purpose, design philosophy, architectural organization, and key capabilities. For detailed information about specific subsystems, refer to the corresponding sections: Core Architecture (#2), Neural Network Components (#3), Model Architectures (#4), Data Management (#5), Training System (#6), Building and Installation (#7), and Development (#8).

**Sources:** README.md1-41

---

## What is fairseq2?

fairseq2 is a sequence modeling toolkit that enables researchers to train custom models for content generation tasks including language modeling, speech processing, and machine translation. It is built on PyTorch and provides:

* **Pre-built model architectures**: LLaMA, Wav2Vec 2.0, w2v-BERT, and transformer-based models
* **Distributed training infrastructure**: Multi-GPU and multi-node training with DDP, FSDP, and tensor parallelism (see fairseq2 Distributed Training)
* **High-performance data processing**: Streaming data pipeline with C++ backend
* **Asset management system**: Version-controlled access to models, tokenizers, and datasets
* **Training recipes**: Pre-configured workflows for instruction finetuning and preference optimization (see fairseq2 Recipes and CLI)

The project consists of two tightly coupled packages:

| Package | Language | Purpose |
| --- | --- | --- |
| `fairseq2` | Python | User-facing API, model definitions, training recipes |
| `fairseq2n` | C++/CUDA | Performance-critical operations, data pipeline implementation |

**Sources:** README.md5-38 CONTRIBUTING.md7-9

---

## Design Philosophy

fairseq2 represents a complete reboot of the original fairseq toolkit. The key design shift is from a **monolithic framework** to an **extensible, modular architecture**:

### Non-Intrusive Design

Rather than requiring researchers to fork or branch the library, fairseq2 uses setuptools extension mechanisms to allow independent project codebases. Researchers can register custom models, optimizers, learning rate schedulers, and trainer units without modifying fairseq2's source code.

### Composability Over Framework Lock-In

fairseq2 leverages modern PyTorch features like `torch.compile`, PyTorch FSDP, and process groups directly rather than wrapping them in opaque abstractions. This allows users to compose fairseq2 components with standard PyTorch code.

### Clean API Boundaries

The library is organized into distinct layers with clear responsibilities, enabling researchers to use only the components they need without pulling in the entire framework.

**Sources:** README.md24-27 README.md33

---

## Architecture Overview

fairseq2 is organized into a layered architecture with six major subsystems:

**Diagram: Core Architecture Layers and Code Entities**

This architecture separates concerns into distinct layers, each documented in detail in their respective sections of this wiki.

**Sources:** README.md29-38 Diagrams from architecture analysis

---

## Core Systems

### Asset Management

The AssetStore class (src/fairseq2/assets/store.py) provides version-controlled access to models, tokenizers, and datasets through `AssetCard` metadata files. Assets can be loaded from well-known locations, package-embedded cards, or custom paths. The `StandardDownloadManager` handles retrieval from HTTP/HTTPS sources, Hugging Face Hub, and local files with automatic caching.

**v0.7 Update**: Direct HuggingFace model import is now supported with native fairseq2 sharding and tensor parallelism. Models can be loaded directly from HF Hub (e.g., Qwen Omni 2.5) without manual checkpoint conversion.

### Distributed Processing

The Gang abstraction (src/fairseq2/gang.py) wraps PyTorch's `ProcessGroup` to provide a unified interface for distributed communication. Functions like `create_parallel_gangs()` and `create_fsdp_gangs()` construct gang hierarchies supporting data parallelism (`dp`), tensor parallelism (`tp`), pipeline parallelism (`pp`), sharded data parallelism (`sdp`), and replicated data parallelism (`rdp`). See fairseq2 Distributed Training for detailed strategies.

### Data Pipeline

The DataPipelineBuilder (src/fairseq2/data/data\_pipeline.py) provides a fluent API for constructing streaming data pipelines. Performance-critical operations are implemented in the C++ backend (native/src/fairseq2n/data/). Operations include `map`, `filter`, `shuffle`, `bucket_by_length`, `collate`, and `prefetch`, with distributed support via `shard`.

### Neural Network Components

Reusable building blocks include:

* **Embeddings**: `StandardEmbedding`, `VocabShardedEmbedding` for tensor parallelism (see fairseq2 Embeddings and Projections)
* **Position Encoders**: `SinusoidalPositionEncoder`, `RotaryEncoder` (RoPE) (see fairseq2 Position Encoders)
* **Attention**: `StandardMultiheadAttention`, `RelativePositionMultiheadAttention` (see fairseq2 Transformer Layers)
* **Transformer Layers**: `TransformerEncoderLayer`, `TransformerDecoderLayer`

### Model Families

The ModelFamily abstraction enables family-based organization. Each family (e.g., `LlamaFamily`, `Wav2Vec2Family`) knows how to load and configure models from asset cards. The `load_model()` function uses dependency injection to resolve the appropriate family. See fairseq2 Model Architectures for supported models.

### Training System

The recipe execution framework orchestrates training through structured configuration, gang initialization, asset loading, and training loops with checkpointing. The `fairseq2 lm` CLI provides entry points for instruction finetuning and preference optimization. See fairseq2 Training System for trainer and evaluator details.

**v0.7 Update**: Recipes are now kept **outside** the core library. For serious research projects, copy and customize recipes rather than using pip-installed versions. The library supports two usage modes: **Library** (pip-install for APIs) vs **Framework** (clone repo and hack recipes).

**Sources:** src/fairseq2/assets/store.py src/fairseq2/gang.py src/fairseq2/data/data\_pipeline.py src/fairseq2/models/loader.py

---

## Key Capabilities

### Multi-GPU and Multi-Node Training

fairseq2 supports distributed training strategies including:

* **DDP (DistributedDataParallel)**: Data parallelism with gradient synchronization
* **FSDP (Fully Sharded Data Parallel)**: Model parameter and optimizer state sharding
* **Tensor Parallelism**: Sharding model layers across devices using gang-aware components
* **Hybrid Strategies**: Combining FSDP with tensor parallelism for 70B+ parameter models

The gang system coordinates communication across all parallelism strategies.

### Streaming Data Processing

The C++ data pipeline backend provides:

* **Lazy evaluation**: Operations only execute during iteration
* **Memory efficiency**: Streaming processing without loading entire datasets
* **State management**: Checkpoint/restore capability for fault tolerance
* **Performance**: Native implementation of bottleneck operations

### Sequence Generation

Native support for vLLM along with built-in `SamplingSequenceGenerator` and `BeamSearchSequenceGenerator` classes for inference.

### Extensibility

Register custom components without forking:

**Sources:** README.md30-35 src/fairseq2/gang.py src/fairseq2/data/data\_pipeline.py

---

## Package Structure and Distribution

**Diagram: Build and Distribution Pipeline**

### Two-Tier Package Design

| Aspect | fairseq2 | fairseq2n |
| --- | --- | --- |
| **Language** | Pure Python | C++/CUDA with Python bindings |
| **Contents** | Models, recipes, high-level API | Data pipeline, custom ops |
| **Dependencies** | fairseq2n (strict version) | PyTorch, NCCL, oneTBB |
| **Platform** | Platform-independent | Platform-specific binaries |
| **Build System** | setuptools | CMake + pybind11 |

### Version Coordination

fairseq2 and fairseq2n must have **exactly matching versions** and both must match the **exact PyTorch version** due to PyTorch's C++ API having no ABI compatibility between releases. Mismatches cause immediate crashes or segfaults.

### Distribution Variants

**PyPI** (README.md62-67):

**FAIR S3 Repository** (README.md77-142):

### CI/CD Pipeline

The GitHub Actions workflow builds wheels for all variant combinations:

| Stage | Workflows | Purpose |
| --- | --- | --- |
| **Build** | `_build_wheel-linux.yaml`, `_build_wheel-macos.yaml` | Compile and package for each variant |
| **Test** | Integrated into build workflows | Run pytest and native tests |
| **Lint** | `_lint_py.yaml`, `_lint_cc.yaml`, `_lint_sh.yaml` | Code quality checks |
| **Publish** | `_publish_s3.yaml`, `_publish_pypi.yaml` | Upload to distribution channels |
| **Documentation** | `_build_doc.yaml`, `_publish_doc.yaml` | Generate and publish Sphinx docs |

**Sources:** README.md42-257 CONTRIBUTING.md6-60 .github/workflows/\_build\_wheels.yaml1-144 .github/workflows/\_publish.yaml1-129

---

## Development Workflow

### Setting Up a Development Environment

For Python-only development (CONTRIBUTING.md15-51):

For C++ development, see Building and Installation (#7).

### Testing

### Linting and Formatting

| Tool | Command | Purpose |
| --- | --- | --- |
| **isort** | `isort .` | Sort Python imports |
| **black** | `black .` | Format Python code |
| **flake8** | `flake8 .` | Python style checker |
| **mypy** | `mypy` | Python type checker |
| **clang-tidy** | `run-clang-tidy -p build` | C++ linter |

**Sources:** CONTRIBUTING.md61-161

---

## Getting Started

### Loading a Pre-trained Model

### Using the Data Pipeline

### Running a Training Recipe

For comprehensive tutorials, see the official documentation.

**Sources:** README.md39-40 README.md30

---

## Supported Research

fairseq2 has been used in recent Meta FAIR research including:

* **Omnilingual ASR**: 1600+ language speech recognition (README.md16)
* **Large Concept Models**: Language modeling in sentence representation space (README.md21)
* **Seamless**: Multilingual expressive and streaming speech translation (README.md22)
* **R.I.P.**: Better models by survival of the fittest prompts (README.md18)

For research foundations and implementation details, see Research Foundations (#9).

**Sources:** README.md15-22

---

## Summary

fairseq2 provides a modular, extensible toolkit for sequence modeling research with:

* **Clean architecture**: Six distinct layers with clear responsibilities
* **Performance**: C++ backend for data processing, multi-GPU training support
* **Flexibility**: Compose fairseq2 components with standard PyTorch code
* **Extensibility**: Register custom components without forking
* **Complete toolkit**: From data loading to model training to inference

The remainder of this wiki provides detailed documentation for each subsystem.


