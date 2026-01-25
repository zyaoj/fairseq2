---
myst:
  html_meta:
    "description lang=en": "fairseq2 Neural Network Components"
    "keywords": "fairseq2, models, documentation"
---

# Neural Network Components


## Purpose and Scope

This document provides an overview of fairseq2's modular neural network building blocks. These components form the foundation for constructing sequence-to-sequence models, language models, and speech processing architectures.

The neural network components are organized into four major categories:

* **Embeddings and Projections**: Input/output layers with standard and sharded variants
* **Position Encoders**: Various positional encoding strategies (sinusoidal, learned, rotary)
* **Transformer Layers**: Attention mechanisms, feed-forward networks, and complete encoder/decoder layers
* **Feature Extraction and Masking**: Components for self-supervised learning in speech models

For information about complete model architectures that use these components, see fairseq2 Model Architectures. For distributed training strategies and how components are wrapped with DDP/FSDP, see fairseq2 Distributed Training. For the Gang system fundamentals, see fairseq2 Gang System. For the broader architecture context, see fairseq2 Core Architecture.

Sources: src/fairseq2/nn/projection.py1-665 src/fairseq2/nn/embedding.py1-533 src/fairseq2/models/transformer/model.py1-289

## Design Philosophy

fairseq2's neural network components follow a consistent architectural pattern that emphasizes modularity, extensibility, and distributed training support:

**Abstract Base Classes**: Each component category defines an abstract interface (e.g., `Projection`, `Embedding`) that specifies the contract for forward passes and shape transformations. This allows models to be written against interfaces rather than concrete implementations.

**Standard Implementations**: Each abstract class has a standard implementation (e.g., `Linear`, `StandardEmbedding`) that provides the baseline, non-distributed behavior. These implementations are functionally equivalent to PyTorch's built-in layers.

**Sharded Variants**: For tensor parallelism support, each component provides sharded implementations that distribute computation across the `tp_gang` (tensor parallel gang). These variants maintain mathematical equivalence to the standard implementation while enabling larger models to fit in memory.

**Gang Integration**: Sharded components accept a `Gangs` container or specific `Gang` instance, automatically determining whether to operate in distributed mode based on `gang.size > 1`. This allows the same model definition to work seamlessly in both single-GPU and distributed settings.

Sources: src/fairseq2/nn/projection.py31-56 src/fairseq2/nn/embedding.py29-58

## Component Hierarchy

The following diagram shows the organization of neural network components and their relationships:

Sources: src/fairseq2/nn/projection.py31-627 src/fairseq2/nn/embedding.py29-533 src/fairseq2/models/transformer/model.py25-289 src/fairseq2/models/conformer/block.py28-197

## Core Abstractions

fairseq2 defines four primary abstract base classes for neural network components:

| Abstract Class | Purpose | Key Methods | Location |
| --- | --- | --- | --- |
| `Projection` | Linear transformations from input\_dim to output\_dim | `forward(x: Tensor) -> Tensor` | nn/projection.py31-56 |
| `Embedding` | Dictionary-based embedding lookup | `forward(x: Tensor) -> Tensor` | nn/embedding.py29-58 |
| `PositionEncoder` | Adds positional information to sequences | `forward(seqs, padding_mask, state_bag)` | nn/position\_encoder.py |
| `MultiheadAttention` | Multi-head attention mechanism | `forward(queries, keys, values, ...)` | nn/transformer/attention.py |

Each abstract class defines:

* **Input/output shapes**: Documented shape transformations for forward passes
* **Required attributes**: Dimensionality parameters (e.g., `input_dim`, `output_dim`, `embed_dim`)
* **Optional parameters**: Common options like `pad_idx` for embeddings

Concrete implementations must implement the abstract `forward()` method and can optionally override `reset_parameters()` for custom initialization.

Sources: src/fairseq2/nn/projection.py31-56 src/fairseq2/nn/embedding.py29-58

## Sharding Strategies and Tensor Parallelism

Sharded components enable tensor parallelism by distributing a layer's parameters across multiple devices. fairseq2 provides two complementary sharding strategies:

### Projection Sharding

**ColumnShardedLinear** (nn/projection.py128-362):

**RowShardedLinear** (nn/projection.py365-597):

Sources: src/fairseq2/nn/projection.py128-362 src/fairseq2/nn/projection.py365-597

### Embedding Sharding

**VocabShardedEmbedding** (nn/embedding.py112-323):

**ShardedEmbedding** (nn/embedding.py326-509):

Sources: src/fairseq2/nn/embedding.py112-323 src/fairseq2/nn/embedding.py326-509

### Gang Integration Pattern

All sharded components follow a consistent pattern for Gang integration:

Key aspects:

* **Device matching**: Sharded components validate that their device matches `gang.device` (nn/projection.py165-168 nn/embedding.py146-151)
* **Divisibility checks**: Dimensions must be divisible by `gang.size` (nn/projection.py209-212 nn/embedding.py190-193)
* **Factory methods**: `from_linear()` and `from_embedding()` create sharded variants from standard instances (nn/projection.py132-187 nn/embedding.py118-169)
* **Unsharding**: `to_linear()` and `to_embedding()` methods reconstruct the full unsharded layer (nn/projection.py292-318 nn/embedding.py273-287)

Sources: src/fairseq2/nn/projection.py189-249 src/fairseq2/nn/embedding.py171-217

## Component Initialization

fairseq2 provides a flexible initialization system that allows customization while maintaining sensible defaults:

| Component | Default Initialization | Custom Init Parameter | Example |
| --- | --- | --- | --- |
| `Linear` | Kaiming uniform on weight, uniform bias (projection.py638-656) | `init_fn: Callable[[Linear], None]` | `init_bert_projection` |
| `StandardEmbedding` | Normal distribution (embedding.py517) | `init_fn: Callable[[StandardEmbedding], None]` | `init_scaled_embedding` |
| Sharded variants | Create temporary standard layer, then shard (projection.py251-258) | Same `init_fn` as standard | N/A |

The initialization flow for sharded components:

1. If `gang.size == 1`: Initialize locally using standard logic
2. If `gang.size > 1`:
   * Create full standard layer on the gang's device
   * Initialize it using `init_fn` or defaults
   * Shard and copy the appropriate slice to the local rank

This ensures all ranks start with identical parameter values before sharding.

Sources: src/fairseq2/nn/projection.py629-665 src/fairseq2/nn/embedding.py511-533

## Component Integration in Models

The following diagram shows how components are composed into complete models:

**Component Composition Pattern**:

1. **Frontends**: Combine embeddings and position encoders to convert input tokens into contextualized representations
2. **Transformer Layers**: Stack multiple encoder/decoder layers, each containing attention and FFN
3. **Feed-Forward Networks**: Use paired column-sharded and row-sharded projections for tensor parallelism
4. **Multi-Head Attention**: Shards Q/K/V projections by column, output projection by row
5. **Final Projection**: Often tied to input embedding weights using `TiedProjection` (projection.py600-615)

**Sharding Strategy in Practice**:

Sources: src/fairseq2/models/transformer/model.py29-61 src/fairseq2/nn/projection.py600-627

## Specialized Components

Beyond the core abstractions, fairseq2 provides specialized components for specific architectures:

**TiedProjection** (projection.py600-615):

**IdentityProjection** (projection.py618-627):

**ConformerConvolution** (models/conformer/convolution.py24-184):

**ConformerBlock** (models/conformer/block.py28-197):

Sources: src/fairseq2/nn/projection.py600-627 src/fairseq2/models/conformer/convolution.py24-184 src/fairseq2/models/conformer/block.py28-197

## Usage Patterns

### Creating Standard Components

### Creating Sharded Components for Tensor Parallelism

### Converting Between Sharded and Standard

Sources: src/fairseq2/nn/projection.py68-110 src/fairseq2/nn/embedding.py64-93 src/fairseq2/nn/projection.py132-187

## Related Pages

* **fairseq2 Embeddings and Projections**: Detailed documentation of embedding and projection implementations
* **fairseq2 Position Encoders**: Position encoding strategies and their applications
* **fairseq2 Transformer Layers**: Attention mechanisms, feed-forward networks, and transformer layer composition
* **fairseq2 Feature Extraction**: Self-supervised learning components for speech models
* **Distributed Processing with Gang**: Gang system fundamentals and collective operations
* **fairseq2 Model Families**: How neural network components are assembled into complete model architectures
* **fairseq2 Distributed Training**: Integration of sharded components with FSDP and DDP
* **fairseq2 Core Architecture**: Broader system architecture and design patterns
