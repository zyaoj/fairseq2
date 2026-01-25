# fairseq2 Knowledge Base

This document consolidates all fairseq2 learning resources, architecture analysis, and development guides.

**Last Updated**: 2026-01-02
**Version**: v0.7+
**Repository**: https://github.com/facebookresearch/fairseq2
**Documentation**: https://facebookresearch.github.io/fairseq2/stable/

---

## Table of Contents

1. [What's New in v0.7](#whats-new-in-v07)
2. [Quick Start](#quick-start)
3. [Architecture Overview](#architecture-overview)
4. [Learning Plan](#learning-plan)
5. [Design Patterns](#design-patterns)
6. [Key Systems Deep Dives](#key-systems-deep-dives)
7. [Development Workflows](#development-workflows)
8. [Critical Files Reference](#critical-files-reference)
9. [Reference Documentation](#reference-documentation)

---

## What's New in v0.7

> See 2026-01-02 fairseq2 v0.7 updates for full details.

### API Changes
- `setup_fairseq2` → `init_fairseq2` (renamed)
- Direct HuggingFace model import now supported (e.g., Qwen Omni 2.5)
- Native fairseq2 sharding and tensor parallelism for HF models

### Architecture Evolution
- **Recipes split from core library** - Copy/paste for research, don't fork
- **Library vs Framework mode** - pip-install for APIs, or clone for customization
- Every module has runtime-configurable interfaces

### New Features
- **Async evaluation hooks** - Arbitrary callbacks after checkpointing for SLURM jobs
- **OLMo2 model support** - 1B/7B/13B with custom RMSNorm, post-norm layers
- **On-policy RL training** - Unified modeling code for training/inference

### Performance
- 20%+ speedup in SeamlessNext training
- Sequence generation target: <5x slowdown vs. vLLM
- Optimized sharding for models larger than single-device memory

### Hardware Support
- Migration to fair-sc(-3) clusters
- GB200 and ARM support added

---

## Quick Start

### Development Environment Setup

**Python-only development** (recommended if not modifying C++/CUDA):
```bash
# Install matching fairseq2n nightly (example for PyTorch 2.9.1, CUDA 12.8)
pip install fairseq2n --pre --upgrade --extra-index-url https://fair.pkg.atmeta.com/fairseq2/whl/nightly/pt2.9.1/cu128

# Install fairseq2 in editable mode
pip install -e .

# Install development tools
pip install -r requirements-devel.txt
```

**Full C++/CUDA development**:
```bash
# Clone with submodules
git submodule update --init --recursive

# Install system dependencies (Ubuntu)
sudo apt install libsndfile-dev

# Install Python build dependencies
pip install -r native/python/requirements-build.txt

# Build fairseq2n (CPU-only)
cd native
cmake -GNinja -B build
cmake --build build

# Build fairseq2n (with CUDA)
cmake -GNinja -DFAIRSEQ2N_USE_CUDA=ON -B build
cmake --build build

# For specific CUDA architectures (example: Ampere/A100)
cmake -GNinja -DCMAKE_CUDA_ARCHITECTURES="80-real;80-virtual" -DFAIRSEQ2N_USE_CUDA=ON -B build

# Install packages in editable mode
cd native/python
pip install -e .
cd ../..
pip install -e .
```

### Common Commands

```bash
# Testing
pytest                          # Run all tests (CPU)
pytest --device cuda:0          # Run tests on GPU
native/build/tests/run-tests    # Run C++ tests

# Linting and Formatting
mypy && flake8 .               # Lint Python code
isort . && black .             # Format Python code

# Run Recipes
python -m recipes.lm.sft --config-file recipes/lm/sft/configs/llama3_2_1b_gsm8k.yaml
python -m recipes.chatbot
python -m recipes.lm.generate

# Documentation
cd doc
pip install -r requirements.txt
make html
cd build/html && python -m http.server 8084
# Visit http://localhost:8084
```

---

## Architecture Overview

### Dual Package Architecture

fairseq2 consists of two interconnected packages:

1. **fairseq2** (`src/fairseq2/`): Pure Python package
   - Recipe framework
   - Configuration system
   - Model architectures
   - Training/evaluation/generation workflows
   - Asset management

2. **fairseq2n** (`native/`): Native C++ and CUDA implementation
   - High-performance data pipeline
   - Custom CUDA kernels
   - Zero-copy memory operations
   - Python bindings via pybind11

**Critical Constraint**: PyTorch version must exactly match fairseq2n due to C++ ABI incompatibility.

### Package Structure

```
src/fairseq2/
├── assets/          # Asset card system for versioned access to models/datasets/tokenizers
├── checkpoint/      # Checkpoint management
├── data/           # Data pipeline API (C++-based, streaming, high-throughput)
├── datasets/       # Dataset implementations
├── generation/     # Sequence generators (sampling, beam search)
├── metrics/        # Training and evaluation metrics
├── models/         # Model architectures (LLaMA, Mistral, NLLB, Wav2vec2, etc.)
├── nn/             # Neural network modules and utilities
├── ops/            # Custom operations
├── optim/          # Optimizers and LR schedulers
├── recipe/         # Recipe framework for training/evaluation/generation
└── runtime/        # Runtime extensions and plugin system

native/
├── src/fairseq2n/  # C++ implementation
├── python/         # Python bindings for fairseq2n
└── tests/          # Native tests

recipes/
├── lm/             # Language model recipes (training, SFT, generation)
├── chatbot/        # Chatbot inference
└── wav2vec2/       # Wav2vec2 pretraining and ASR
```

---

## Learning Plan

### Progressive Learning Path (16-18 Weeks)

#### Phase 1: Foundation (Week 1-2)
**Goal**: Understand dual-package architecture, build system, and configuration fundamentals

**Key Files**:
- `/src/fairseq2/recipe/config.py` - Configuration dataclasses (1373 lines)
- `/native/CMakeLists.txt` - Build system
- `/pyproject.toml` - Tool configurations

**Exercises**:
- Build fairseq2n from source
- Run first recipe
- Create custom config section with validation

#### Phase 2: Dependency Injection (Week 3)
**Goal**: Master the dependency injection pattern

**Key Files**:
- `/src/fairseq2/runtime/dependency.py` - DependencyContainer
- `/src/fairseq2/recipe/component.py` - Component registration
- `/src/fairseq2/composition/extensions.py` - Extension mechanism

**Exercises**:
- Create custom extension
- Register custom optimizer component
- Trace dependency resolution

#### Phase 3: Recipe Framework (Week 4-5)
**Goal**: Understand recipe orchestration

**Key Files**:
- `/src/fairseq2/recipe/base.py` - Recipe, RecipeContext
- `/recipes/lm/train/recipe.py` - Training recipe example
- `/recipes/lm/generate/` - Generation recipe example

**Exercises**:
- Implement custom recipe
- Add custom hook to training loop
- Compare training vs generation recipes

#### Phase 4: Data Pipeline (Week 6-7)
**Goal**: Master streaming data pipeline

**Key Files**:
- `/src/fairseq2/data/data_pipeline.py` - Python API
- `/native/src/fairseq2n/data/data_pipeline.{h,cc}` - C++ implementation
- `/src/fairseq2/data/parquet/fragment_streaming/builder.py` - Parquet integration

**Exercises**:
- Build multi-modal pipeline
- Analyze packing efficiency
- Save/restore pipeline state

#### Phase 5: Asset System (Week 8)
**Goal**: Understand versioned model/dataset management

**Key Files**:
- `/src/fairseq2/assets/card.py` - AssetCard architecture
- `/src/fairseq2/assets/store.py` - Asset retrieval
- `/src/fairseq2/assets/download_manager.py` - HuggingFace integration

**Exercises**:
- Create custom asset card
- Download from HuggingFace Hub
- Set up environment-specific overrides

#### Phase 6: Distributed Training (Week 9-11)
**Goal**: Master FSDP, tensor parallelism, gang abstraction

**Key Files**:
- `/src/fairseq2/nn/fsdp/unified.py` - FSDP facade
- `/src/fairseq2/nn/sharded.py` - Tensor parallelism interface
- `/src/fairseq2/nn/data_parallel.py` - Data parallel facade

**Exercises**:
- Run FSDP experiments (v1 vs v2)
- Configure mixed FSDP+TP
- Visualize gang structure

#### Phase 7: Model Architecture (Week 12-13)
**Goal**: Understand model patterns using LLaMA

**Key Files**:
- `/src/fairseq2/models/llama/config.py` - Configuration-driven architecture
- `/src/fairseq2/models/llama/factory.py` - Factory pattern
- `/src/fairseq2/nn/transformer/attention.py` - Attention mechanisms

**Exercises**:
- Create architecture variant
- Profile attention backends
- Trace model loading

#### Phase 8: Training Loop (Week 14)
**Goal**: Understand trainer and metrics

**Key Files**:
- `/src/fairseq2/trainer.py` - Trainer implementation
- `/src/fairseq2/metrics/` - Metric system

**Exercises**:
- Implement custom metric
- Analyze checkpoints
- Track gradient statistics

#### Phase 9: Evaluation & Generation (Week 15)
**Goal**: Master evaluation and text generation

**Key Files**:
- `/src/fairseq2/evaluator.py` - Evaluator
- `/src/fairseq2/generator.py` - Generator
- `/recipes/lm/generate/` - Generation recipe

**Exercises**:
- Implement custom evaluation
- Compare sampling vs beam search
- Optimize generation throughput

#### Phase 10: Advanced Topics (Week 16-18)
**Goal**: Explore multimodal, custom ops, profiling

**Areas**:
- Multimodal model architectures
- CUDA kernel development
- Memory/compute profiling
- Testing strategies

---

## Design Patterns

fairseq2 employs several key architectural patterns:

### 1. Dependency Injection

**Every component** is registered and resolved through `DependencyContainer`:

```python
# Registration
container.register(Optimizer, create_optimizer, singleton=True)
register_component(container, Optimizer, "adamw", AdamWConfig, factory)

# Resolution
optimizer = resolver.resolve(Optimizer)
```

**Benefits**:
- Late binding: Components discovered at runtime
- Composability: Easy to swap implementations
- Testing: Can mock dependencies

### 2. Configuration as Data

All configuration is **strongly typed dataclasses** with validation:

```python
@dataclass(kw_only=True)
class MyConfig(Validatable):
    lr: float = 1e-3

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if self.lr <= 0.0:
            result.add_error("`lr` must be positive.")
        return result
```

**Benefits**:
- Type safety (IDE autocomplete)
- YAML serialization
- Validation at construction time

### 3. Builder Pattern (Data Pipeline)

Fluent API with method chaining:

```python
pipeline = (
    read_sequence(data)
    .map(preprocess, num_parallel_calls=4)
    .shuffle(shuffle_window=1000, seed=42)
    .bucket_by_length(bucket_sizes)
    .collate(pad_value=0)
    .prefetch(num_examples=4)
    .and_return()
)
```

**Benefits**:
- Deferred execution
- Composable transformations
- Type-safe composition

### 4. Factory Pattern

Components created via factory functions:

```python
class LLaMAFactory:
    def create_model(self) -> TransformerLM:
        embed = self.create_embedding()
        decoder = self.create_decoder()
        final_proj = self.create_final_projection(embed)
        return TransformerLM(decoder, final_proj, ...)
```

**Benefits**:
- Consistent initialization
- Config-driven construction
- Dependency injection compatible

### 5. Facade Pattern

Version-agnostic wrappers:

```python
# FSDP Facade - works with v1 or v2
def to_fsdp(module, gangs, applier, version="v1"/"v2"):
    if version == "v1":
        return to_fsdp1(module, gangs, applier)
    else:
        return to_fsdp2(module, gangs, applier)
```

**Benefits**:
- Consistent API across implementations
- Easy migration between versions
- Simplified client code

### 6. Recipe Extension Points

Well-defined hooks for customization:

```python
class Recipe(ABC):
    def register(self, container: DependencyContainer) -> None:
        # Register custom components (datasets, metrics, etc.)
        pass

    def setup_model(self, context, model, newly_initialized) -> Module:
        # Customize model after initialization
        return model

    def create_task(self, context: RecipeContext) -> Task:
        # Main recipe logic
        pass
```

### 7. Gang-Based Distributed Abstraction

Hierarchical process groups:

```python
# Four gang types
gangs.dp   # Data Parallel: All ranks
gangs.sdp  # Sharded Data Parallel: FSDP sharding dimension
gangs.rdp  # Replica Data Parallel: Model replica dimension
gangs.tp   # Tensor Parallel: Tensor sharding dimension
```

**Benefits**:
- Composable parallelism strategies (e.g., TP4 × FSDP16)
- Centralized rank/device info
- Simplified distributed communication

### 8. Asset Card Inheritance

Hierarchical metadata:

```yaml
name: llama3_8b
base: llama3_base  # Inherits from base card
model_type: llama
checkpoint: "hg://meta-llama/Meta-Llama-3-8B"
```

**Benefits**:
- Configuration reuse
- Environment-specific overrides
- Lazy field resolution

---

## Key Systems Deep Dives

### Recipe System

The recipe system orchestrates training, evaluation, and generation workflows through a dependency injection framework.

#### Core Abstractions

**Recipe Base Class**:
```python
class Recipe(ABC):
    def register(self, container: DependencyContainer) -> None:
        """Optional: register custom components."""
        pass

    @abstractmethod
    def create_task(self, context: RecipeContext) -> Task:
        """Create Trainer, Evaluator, or Generator."""

    def setup_model(self, context, model, newly_initialized) -> Module:
        """Optional: apply model transformations."""
        return model

    @property
    @abstractmethod
    def config_kls(self) -> type[object]:
        """Configuration class this recipe expects."""
```

**RecipeContext** (Facade over DependencyResolver):
```python
context.get_config_as(MyConfig)           # Type-safe config access
context.get_model_as(SequenceModel)       # Model retrieval
context.get_dataset_as(MyDataset)         # Dataset retrieval
context.get_tokenizer()                   # Tokenizer retrieval
context.create_trainer(unit, data_reader) # Factory methods
context.gangs                             # Distributed process groups
context.device                            # Device info
context.output_dir                        # Output directory
```

#### Configuration System

**Type-safe dataclasses with validation**:

```python
@dataclass(kw_only=True)
class ModelSection(Validatable):
    name: str | None = None           # Named model from asset store
    path: Path | None = None          # Local checkpoint path
    family: str | None = None         # Model family
    arch: str | None = None           # Architecture variant
    dtype: DataType = torch.float32
    compile: bool = False

    def validate(self) -> ValidationResult:
        # Ensures name or family is specified
```

**Dynamic structuring**:

```python
class OptimizerSection(SupportsStructure):
    name: str = "adamw"
    config: object = field(default_factory=AdamWConfig)

    def structure(self, resolver: DependencyResolver) -> None:
        # Look up optimizer component and validate config
        self.config = structure_component_config(
            resolver, Optimizer, self.name, self.config
        )
```

#### Component Registration

**Register components with type-safe factories**:

```python
register_component(
    container,
    Optimizer,              # Interface
    "adamw",               # Name
    config_kls=AdamWConfig,
    factory=create_adamw,
)

# Factory signature
def create_adamw(resolver: DependencyResolver, config: AdamWConfig) -> Optimizer:
    optimizer_factory = resolver.resolve(_AdamWFactory)
    return optimizer_factory.create(config)
```

#### Extension Mechanism

**Entry point system**:

```python
# setup.py in extension package
setup(
    name="my-fairseq2-extension",
    entry_points={
        "fairseq2.extension": [
            "my_extension = my_package:register_extension",
        ]
    }
)

# Extension function
def register_extension(container: DependencyContainer) -> None:
    register_component(
        container,
        MyComponentType,
        "my_component",
        config_kls=MyConfig,
        factory=my_factory,
    )
```

### Data Pipeline System

High-performance, streaming-based data processing with C++ core.

#### Core Differences from PyTorch DataLoader

| Feature | fairseq2 | PyTorch DataLoader |
|---------|----------|-------------------|
| **Language** | C++ core + Python | Pure Python |
| **State Persistence** | Native (`state_dict`) | Manual |
| **Streaming** | Native | Limited |
| **Composition** | Fluent API | Chaining |
| **Parallelism** | Built-in (`num_parallel_calls`) | Via `num_workers` |
| **Bucketing** | Multiple strategies | Custom required |

#### Pipeline Operations

**Sources**:
```python
read_sequence([1, 2, 3, 4])           # Python sequence
read_iterator(iter, reset_fn)         # Python iterator
list_files(Path("/data"), "*.txt")    # File listing
DataPipeline.count(start=0, step=1)   # Infinite counter
DataPipeline.constant(0)              # Infinite constant
```

**Transformations**:
```python
.map(fn, num_parallel_calls=4)        # Parallel mapping
.filter(predicate)                    # Filtering
.shuffle(shuffle_window=1000, seed=42) # Shuffle buffer
.shard(shard_idx=0, num_shards=8)     # Distributed sharding
.bucket(bucket_size=32)               # Fixed bucketing
.dynamic_bucket(threshold, cost_fn)   # Dynamic batching
.bucket_by_length(bucket_sizes)       # Length-based batching
```

**Batching**:
```python
.collate(pad_value=0, pad_to_multiple=8)  # Pad and concatenate
# Output: {"is_ragged": bool, "seqs": Tensor, "seq_lens": [...]}
```

**Combination**:
```python
DataPipeline.concat([pipe1, pipe2])              # Sequential
DataPipeline.round_robin([pipe1, pipe2])         # Interleave
DataPipeline.sample([pipe1, pipe2], weights)     # Weighted sampling
DataPipeline.zip([pipe1, pipe2], names=["a", "b"]) # Parallel
```

**Performance**:
```python
.prefetch(num_examples=4)             # Background loading
.pack(num_elements=2048, max_seq_len=512)  # Sequence packing
```

#### State Management

```python
# Save state
state = pipeline.state_dict(strict=True)
torch.save(state, "checkpoint.pt")

# Resume
pipeline.load_state_dict(state)

# Reset
pipeline.reset(reset_rng=True)
```

### Asset System

Versioned access to models, datasets, and tokenizers.

#### AssetCard Architecture

**Hierarchical metadata with inheritance**:

```python
class AssetCard:
    def __init__(self, name, metadata, base: AssetCard | None = None):
        self._name = name
        self._metadata = metadata
        self._base = base  # Inheritance chain

    def maybe_get_field(self, name: str) -> AssetCardField | None:
        # Walks up inheritance chain
        card = self
        while card is not None:
            try:
                value = card.metadata[name]
                return AssetCardField(name, self, value)
            except KeyError:
                card = card.base
        return None
```

#### Asset Store and Retrieval

**Environment resolution**:
- `llama3_1_8b@awscluster` - environment-specific
- `llama3_1_8b@` - skip environment lookup
- `llama3_1_8b` - use default environment

**Metadata providers**:
1. `FileAssetMetadataLoader` - YAML files on disk
2. `PackageAssetMetadataLoader` - Python package resources
3. `InMemoryAssetMetadataSource` - Programmatic registration

#### Download Managers

**Multi-scheme support**:
- `file://` - Local filesystem
- `hg://` - Hugging Face Hub
- `http://` / `https://` - Web downloads

**HuggingFace integration**:
```python
# hg://user/repo → snapshot_download(repo_id)
path = snapshot_download(
    repo_id="meta-llama/Meta-Llama-3-8B",
    allow_patterns="*.safetensors",  # Filter to safetensors
)
```

### Distributed Training Infrastructure

#### Gang Abstraction

**Hierarchical process groups**:

```python
gangs.dp    # Data Parallel: All ranks
gangs.sdp   # Sharded Data Parallel: FSDP sharding dimension
gangs.rdp   # Replica Data Parallel: Model replica dimension
gangs.tp    # Tensor Parallel: Tensor sharding dimension
```

**Example**: 64 GPUs = TP4 × FSDP16
- 4 tensor parallel ranks per model
- 16 FSDP shards per tensor parallel group

#### FSDP Unified Interface

**Version-agnostic API**:

```python
model = to_fsdp(
    module,
    gangs,
    applier,
    version="v1",  # or "v2"
    mixed_precision_dtype=torch.bfloat16,
    reshard_after_forward=True,
    cpu_offload=False,
)
```

**Sharding strategies**:
- `FULL_SHARD` - Standard FSDP (rdp.size == 1)
- `HYBRID_SHARD` - HSDP (rdp.size > 1)

#### Tensor Parallelism

**Sharded interface**:

```python
class Sharded(ABC):
    @abstractmethod
    def get_shard_dims(self) -> list[tuple[Parameter, int]]:
        """Returns (parameter, shard_dimension) for each sharded parameter."""
```

**Implementations**:
- `ColumnShardedLinear` - Output dimension sharding
- `VocabShardedEmbedding` - Vocabulary dimension sharding

#### Data Parallelism Facade

**Unified interface for DDP/FSDP**:

```python
class DataParallelFacade(ABC):
    @abstractmethod
    def state_dict(self) -> dict[str, object]: ...
    @abstractmethod
    def load_state_dict(self, state_dict) -> None: ...
    @abstractmethod
    def no_sync(self) -> ContextManager[None]: ...
    @abstractmethod
    def clip_grad_norm(self, max_norm) -> Tensor: ...
```

---

## Development Workflows

### Creating a Custom Recipe

1. **Define configuration**:

```python
@dataclass(kw_only=True)
class MyTrainConfig:
    model: ModelSection = field(default_factory=ModelSection)
    dataset: DatasetSection = field(default_factory=DatasetSection)
    trainer: TrainerSection = field(default_factory=TrainerSection)
    # ... other sections
```

2. **Implement recipe**:

```python
class MyTrainRecipe(Recipe):
    @override
    def register(self, container: DependencyContainer) -> None:
        # Register custom components (datasets, etc.)
        register_dataset_family(
            container,
            "my_dataset",
            MyDataset,
            MyDatasetConfig,
            opener=open_my_dataset,
        )

    @override
    def create_task(self, context: RecipeContext) -> Task:
        config = context.get_config_as(MyTrainConfig)
        model = context.get_data_parallel_model()
        unit = MyTrainUnit(model)
        dataset = context.get_dataset_as(MyDataset)
        data_reader = dataset.create_reader(...)
        return context.create_trainer(unit, data_reader)

    @property
    @override
    def config_kls(self) -> type[object]:
        return MyTrainConfig
```

3. **Implement TrainUnit**:

```python
class MyTrainUnit(TrainUnit[BatchT]):
    @override
    def prepare_metric_bag(self, metric_bag: MetricBag) -> None:
        # Register metrics
        add_loss_metric(metric_bag)

    @override
    def process_batch(self, batch: BatchT, metric_bag: MetricBag) -> tuple[Tensor, int | None]:
        # Forward pass and loss computation
        loss = self._model(batch)
        update_loss_metric(metric_bag, loss)
        return loss, None
```

### Implementing a Custom Data Pipeline

```python
def create_my_pipeline(rank: int, world_size: int) -> DataPipeline:
    # Source
    pipeline = read_sequence(dataset)

    # Distributed sharding
    pipeline = pipeline.shard(shard_idx=rank, num_shards=world_size)

    # Preprocessing
    pipeline = pipeline.map(
        preprocess_fn,
        num_parallel_calls=8,
        deterministic=True
    )

    # Shuffling
    pipeline = pipeline.shuffle(shuffle_window=10000, seed=42)

    # Dynamic bucketing
    bucket_sizes = create_bucket_sizes(
        max_num_elements=8192,
        max_seq_len=512,
        min_seq_len=32,
    )
    pipeline = pipeline.bucket_by_length(
        bucket_sizes=bucket_sizes,
        selector="seqs",
    )

    # Collation
    pipeline = pipeline.collate(pad_value=0)

    # Prefetching
    pipeline = pipeline.prefetch(num_examples=4)

    return pipeline.and_return()
```

### Adding a Custom Extension

1. **Create extension function**:

```python
# my_extension/register.py
from fairseq2.runtime.dependency import DependencyContainer
from fairseq2.recipe.component import register_component

def register_extension(container: DependencyContainer) -> None:
    register_component(
        container,
        Optimizer,
        "my_optimizer",
        config_kls=MyOptimizerConfig,
        factory=create_my_optimizer,
    )

def create_my_optimizer(resolver, config: MyOptimizerConfig) -> Optimizer:
    # Implementation
    return MyOptimizer(config)
```

2. **Register via setup.py**:

```python
setup(
    name="my-fairseq2-extension",
    entry_points={
        "fairseq2.extension": [
            "my_ext = my_extension.register:register_extension",
        ]
    }
)
```

3. **Use in config**:

```yaml
optimizer:
  name: my_optimizer
  config:
    lr: 0.001
    # ... other params
```

### Debugging Distributed Training

**Check gang initialization**:

```python
from fairseq2.gang import Gang, Gangs

gangs = Gangs.from_env()  # Or manually construct

print(f"DP size: {gangs.dp.size}, rank: {gangs.dp.rank}")
print(f"SDP size: {gangs.sdp.size}, rank: {gangs.sdp.rank}")
print(f"RDP size: {gangs.rdp.size}, rank: {gangs.rdp.rank}")
print(f"TP size: {gangs.tp.size}, rank: {gangs.tp.rank}")
```

**Profile FSDP memory**:

```bash
# Set environment variables
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Run with memory profiling
python -m torch.distributed.run \
    --nproc_per_node=8 \
    train.py \
    --profile-memory
```

**Check NCCL errors**:

```bash
# Enable NCCL debugging
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=ALL

# Check network connectivity
export NCCL_SOCKET_IFNAME=eth0  # Or your network interface
```

---

## Critical Files Reference

### Recipe System
- `src/fairseq2/recipe/base.py` - Recipe, RecipeContext base classes
- `src/fairseq2/recipe/config.py` - Configuration dataclasses (1373 lines)
- `src/fairseq2/recipe/component.py` - Component registration and lookup
- `src/fairseq2/recipe/internal/config.py` - Configuration structuring
- `src/fairseq2/composition/extensions.py` - Extension loading
- `src/fairseq2/recipe/composition/root.py` - Recipe registration
- `src/fairseq2/recipe/composition/optim.py` - Optimizer components
- `src/fairseq2/recipe/composition/lr_schedulers.py` - LR scheduler components

### Data Pipeline
- `src/fairseq2/data/data_pipeline.py` - Python API
- `native/src/fairseq2n/data/data_pipeline.h` - C++ header
- `native/src/fairseq2n/data/data_pipeline.cc` - C++ implementation
- `src/fairseq2/data/parquet/fragment_streaming/builder.py` - Parquet integration

### Asset System
- `src/fairseq2/assets/card.py` - AssetCard architecture
- `src/fairseq2/assets/store.py` - Asset store and retrieval
- `src/fairseq2/assets/download_manager.py` - Download managers
- `src/fairseq2/assets/metadata_provider.py` - Metadata providers

### Distributed Training
- `src/fairseq2/nn/fsdp/unified.py` - FSDP unified interface
- `src/fairseq2/nn/fsdp/fsdp1.py` - FSDP v1 implementation
- `src/fairseq2/nn/fsdp/fsdp2.py` - FSDP v2 implementation
- `src/fairseq2/nn/sharded.py` - Tensor parallelism interface
- `src/fairseq2/nn/projection.py` - ColumnShardedLinear
- `src/fairseq2/nn/embedding.py` - VocabShardedEmbedding
- `src/fairseq2/nn/data_parallel.py` - Data parallel facade

### Model Architecture (LLaMA)
- `src/fairseq2/models/llama/config.py` - Configuration
- `src/fairseq2/models/llama/factory.py` - Factory pattern
- `src/fairseq2/nn/transformer/attention.py` - Attention mechanisms
- `src/fairseq2/nn/transformer/ffn.py` - Feedforward networks
- `src/fairseq2/nn/normalization.py` - Normalization layers
- `src/fairseq2/nn/position_encoder.py` - Positional encoding

### Training Infrastructure
- `src/fairseq2/trainer.py` - Trainer implementation
- `src/fairseq2/evaluator.py` - Evaluator implementation
- `src/fairseq2/generator.py` - Generator implementation
- `src/fairseq2/metrics/` - Metric system

### Example Recipes
- `recipes/lm/train/` - LM training recipe
- `recipes/lm/sft/` - Supervised fine-tuning recipe
- `recipes/lm/generate/` - Generation recipe
- `recipes/chatbot/` - Chatbot inference

---

## Reference Documentation

Detailed reference documentation imported from DeepWiki:

### Core Architecture
- fairseq2 Overview - High-level introduction
- fairseq2 Core Architecture - System architecture
- fairseq2 Package System - Dual-package design
- fairseq2 Runtime Infrastructure - DI, device management
- fairseq2 Gang System - Distributed abstractions
- fairseq2 Data Pipeline - Streaming data processing
- fairseq2 Asset Management - Model/tokenizer/dataset management

### Neural Network Components
- fairseq2 Neural Network Components - Building blocks overview
- fairseq2 Embeddings and Projections
- fairseq2 Position Encoders - RoPE, sinusoidal
- fairseq2 Transformer Layers
- fairseq2 Feature Extraction

### Model Architectures
- fairseq2 Model Architectures - Overview
- fairseq2 Model Abstractions
- fairseq2 Model Families - Family-based loading
- fairseq2 Speech Models - Wav2Vec2, w2v-BERT
- fairseq2 Language Models - LLaMA, Mistral

### Data Management
- fairseq2 Data Management - Overview
- fairseq2 Text Processing
- fairseq2 Tokenization

### Training System
- fairseq2 Training System - Trainer, units
- fairseq2 Recipes and CLI - Recipe framework
- fairseq2 Checkpoint Management
- fairseq2 Distributed Training - FSDP, TP, DDP
- fairseq2 Optimizers and LR Schedulers

### Development
- fairseq2 Building and Installation
- fairseq2 Development and CI-CD
- fairseq2 Research Foundations

---

## Additional Resources

- **Documentation**: https://facebookresearch.github.io/fairseq2/stable/
- **GitHub**: https://github.com/facebookresearch/fairseq2
- **Contributing**: See `CONTRIBUTING.md` in repository
- **Build from Source**: See `INSTALL_FROM_SOURCE.md`

---

## Common Pitfalls

1. **PyTorch version mismatch**: Always ensure fairseq2n matches your exact PyTorch version
2. **Missing submodules**: Clone with `--recurse-submodules` or run `git submodule update --init --recursive`
3. **CUDA toolkit mismatch**: When building with CUDA, toolkit version must match PyTorch's CUDA version
4. **Conda environment issues**: Building C++ in Conda can fail due to library conflicts; prefer Python venv
5. **Stale nightlies**: After pulling latest commits, rebuild or reinstall matching fairseq2n nightly
6. **Gang initialization failures**: Check environment variables, network settings, and process group setup
7. **FSDP OOM**: Adjust sharding strategy, batch size, or enable gradient checkpointing
8. **Data pipeline stalls**: Check DataReader config, Gang in data loading, and deadlock conditions

---

**End of fairseq2 Knowledge Base**
