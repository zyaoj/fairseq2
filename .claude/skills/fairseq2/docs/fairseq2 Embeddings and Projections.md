---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - neural-network
  - embeddings
---
# Embeddings and Projections


This page documents the embedding and projection layers in fairseq2, which are fundamental building blocks for neural network models. These components provide abstract interfaces with standard implementations and sharded variants for tensor parallelism.

**Scope**: This page covers the `Embedding` and `Projection` class hierarchies, their standard implementations, and sharded variants for distributed training. For position encoding (sinusoidal, learned, rotary), see fairseq2 Position Encoders. For transformer attention and feed-forward networks, see fairseq2 Transformer Layers. For distributed training infrastructure, see Distributed Processing with Gang and fairseq2 Distributed Training. For usage in complete models, see fairseq2 Model Architectures. For the broader neural network context, see fairseq2 Neural Network Components. For the broader architecture context, see fairseq2 Core Architecture.

## Overview

fairseq2 provides two main categories of neural network components:

* **Embeddings**: Map discrete indices to continuous vector representations
* **Projections**: Apply linear transformations to input tensors

Both categories follow a consistent design pattern with abstract base classes, standard implementations that match PyTorch behavior, and sharded variants for tensor parallelism in distributed training.

**Sources**: src/fairseq2/nn/embedding.py29-58 src/fairseq2/nn/projection.py31-56

## Abstract Interfaces

### Embedding

The `Embedding` abstract base class defines the interface for all embedding layers. It stores embeddings of a fixed dictionary size and dimensionality.

**Key attributes**:

* `num_embeddings`: Size of the vocabulary
* `embed_dim`: Dimensionality of embeddings
* `pad_idx`: Optional padding index (gradients zeroed during training)

**Forward signature**: Takes a tensor of indices (any shape) and returns embeddings of shape `(*input_shape, embed_dim)`.

**Sources**: src/fairseq2/nn/embedding.py29-58

### Projection

The `Projection` abstract base class defines the interface for linear transformations.

**Key attributes**:

* `input_dim`: Input dimensionality
* `output_dim`: Output dimensionality

**Forward signature**: Takes a tensor of shape `(*, input_dim)` and returns a tensor of shape `(*, output_dim)`.

**Sources**: src/fairseq2/nn/projection.py31-56

## Standard Implementations

### StandardEmbedding

`StandardEmbedding` is the standard implementation of the `Embedding` interface, functionally equivalent to `torch.nn.Embedding`.

**Key features**:

**Parameters**:

| Parameter | Type | Description |
| --- | --- | --- |
| `num_embeddings` | `int` | Vocabulary size |
| `embed_dim` | `int` | Embedding dimensionality |
| `pad_idx` | `int | None` | Padding index (no gradient updates) |
| `init_fn` | `Callable | None` | Custom initialization function |
| `device` | `Device | None` | Device placement |
| `dtype` | `DataType | None` | Data type |

**Sources**: src/fairseq2/nn/embedding.py60-109

### Linear

`Linear` is the standard implementation of the `Projection` interface, identical to `torch.nn.Linear`.

**Key features**:

**Parameters**:

| Parameter | Type | Description |
| --- | --- | --- |
| `input_dim` | `int` | Input dimensionality |
| `output_dim` | `int` | Output dimensionality |
| `bias` | `bool` | Whether to include bias |
| `init_fn` | `Callable | None` | Custom initialization function |
| `device` | `Device | None` | Device placement |
| `dtype` | `DataType | None` | Data type |

**Sources**: src/fairseq2/nn/projection.py58-125

## Sharded Variants for Tensor Parallelism

fairseq2 provides sharded variants of embeddings and projections for tensor parallelism. These variants distribute computation across multiple devices using the Gang system (see Distributed Processing with Gang).

### Sharding Strategies

**Sources**: src/fairseq2/nn/embedding.py112-323 src/fairseq2/nn/projection.py127-597

### VocabShardedEmbedding

Shards the embedding table across the vocabulary dimension. Each rank holds a contiguous shard of the vocabulary.

**Sharding details**:

1. Compute vocabulary range for this rank: `<FileRef file-url="https://github.com/facebookresearch/fairseq2/blob/a510a839/vocab_begin_idx, vocab_end_idx)`\n2. Create mask for out-of-range indices\n3. Adjust indices#LNaN-LNaN" NaN file-path="vocab\_begin\_idx, vocab\_end\_idx)`\n2. Create mask for out-of-range indices\n3. Adjust indices">Hii

### ShardedEmbedding

Shards the embedding table across the embedding dimension. Each rank holds the full vocabulary but only a portion of each embedding vector.

**Sharding details**:

**Forward pass algorithm** (src/fairseq2/nn/embedding.py450-460):

1. Apply `reduce_on_backward` to input indices (no-op forward, reduce gradients in backward)
2. Lookup embeddings from local shard
3. Gather outputs along embedding dimension across ranks

**Sources**: src/fairseq2/nn/embedding.py325-509

### ColumnShardedLinear

Shards a linear layer across its output dimension (columns of weight matrix).

**Sharding details**:

**Parameters**:

| Parameter | Type | Description |
| --- | --- | --- |
| `gather_output` | `bool` | Whether to gather outputs (default: `True`) |

**Forward pass algorithm** (src/fairseq2/nn/projection.py279-290):

1. Apply `reduce_on_backward` to inputs
2. Apply linear transformation with local weight/bias shard
3. Optionally gather outputs along output dimension

**When to use**:

**Sources**: src/fairseq2/nn/projection.py127-362

### RowShardedLinear

Shards a linear layer across its input dimension (rows of weight matrix).

**Sharding details**:

**Parameters**:

| Parameter | Type | Description |
| --- | --- | --- |
| `scatter_input` | `bool` | Whether to scatter inputs (default: `True`) |
| `reduce_output` | `bool` | Whether to reduce outputs (default: `True`) |

**Forward pass algorithm** (src/fairseq2/nn/projection.py517-532):

1. Optionally scatter inputs along input dimension
2. Apply linear transformation with local weight shard (no bias yet)
3. Optionally all-reduce outputs across ranks
4. Add bias (if present)

**When to use**:

**Sources**: src/fairseq2/nn/projection.py364-597

## Communication Patterns in Sharded Layers

The following diagram shows how communication primitives are used in each sharded variant:

**Sources**: src/fairseq2/nn/embedding.py236-272 src/fairseq2/nn/embedding.py450-460 src/fairseq2/nn/projection.py279-290 src/fairseq2/nn/projection.py517-532

## Specialized Projections

### TiedProjection

`TiedProjection` uses the weight and bias parameters from another module, enabling weight tying between embedding and output projection layers (a common technique in language models to reduce parameters).

**Usage**:

**Key characteristics**:

**Sources**: src/fairseq2/nn/projection.py599-615

### IdentityProjection

`IdentityProjection` is a no-op projection that returns its input unchanged. Useful for disabling projections without changing model architecture or configuration code.

**Usage**:

**Sources**: src/fairseq2/nn/projection.py617-627

## Initialization

Both embeddings and projections support custom initialization via the `init_fn` parameter, which receives the module instance and is called in `reset_parameters()`.

### Built-in Initializers

**For embeddings**:

| Function | Description | Usage |
| --- | --- | --- |
| `_init_embedding` | Default: `nn.init.normal_(weight)`, zeros padding index | Automatic |
| `init_scaled_embedding` | Normal distribution: `N(0, 1/√embed_dim)` | Pass as `init_fn` |

**For projections**:

| Function | Description | Usage |
| --- | --- | --- |
| `_init_linear` | Default: Kaiming uniform for weight, uniform for bias | Automatic |
| `init_bert_projection` | BERT-style: `N(0, 0.02)` for weight, zeros for bias | Pass as `init_fn` |

### Custom Initialization Example

**Sources**: src/fairseq2/nn/embedding.py511-533 src/fairseq2/nn/projection.py629-665

## Integration with Gang System

Sharded variants integrate with the Gang system (see Distributed Processing with Gang) for distributed training:

**Key integration points**:

1. **Gang retrieval**: Sharded layers use `gangs.tp` for tensor parallelism operations
2. **Device validation**: Weight device must match `gangs.device` (or be `meta`)
3. **Rank-based sharding**: Each rank gets a shard based on `gang.rank` and `gang.size`
4. **Communication primitives**: Use `reduce`, `gather`, `scatter`, `reduce_on_backward` from src/fairseq2/ops/tensor\_parallel.py
5. **Unsharding**: Methods like `to_embedding()` and `to_linear()` gather shards back to standard layers

**Sources**: src/fairseq2/nn/embedding.py117-169 src/fairseq2/nn/projection.py132-187 src/fairseq2/gang.py

## The Sharded Interface

All sharded variants implement the `Sharded` interface, which provides:

**Key methods**:

* `get_shard_dims()`: Returns list of `(Parameter, shard_dimension)` tuples indicating which parameters are sharded and along which dimension

**Shard dimensions**:

| Class | Sharded Parameter | Shard Dimension |
| --- | --- | --- |
| `VocabShardedEmbedding` | `weight` | 0 (vocabulary) |
| `ShardedEmbedding` | `weight` | 1 (embedding) |
| `ColumnShardedLinear` | `weight`, `bias` | 0 (output) |
| `RowShardedLinear` | `weight` | 1 (input) |

**Sources**: src/fairseq2/nn/sharded.py src/fairseq2/nn/embedding.py300-301 src/fairseq2/nn/embedding.py489-490 src/fairseq2/nn/projection.py331-335 src/fairseq2/nn/projection.py568-569

## Usage in Models

Embeddings and projections are used throughout fairseq2 models. The `TransformerModel` demonstrates typical usage:

**Typical usage patterns**:

1. **Input embeddings**: `StandardEmbedding` or `VocabShardedEmbedding` in frontends
2. **Attention projections**: `Linear` or `ColumnShardedLinear` for Q/K/V projections, `Linear` or `RowShardedLinear` for output projection
3. **FFN projections**: `Linear` or `ColumnShardedLinear` for first layer, `Linear` or `RowShardedLinear` for second layer
4. **Final projection**: `Linear`, `TiedProjection` (tied with input embedding), or sharded variants

**Sources**: src/fairseq2/models/transformer/model.py29-61 src/fairseq2/models/transformer/frontend.py src/fairseq2/models/transformer/attention.py src/fairseq2/models/transformer/ffn.py

## Parameter Counts

Understanding parameter counts for sharded vs. unsharded variants:

| Component | Standard | Sharded Variant | Parameters per Rank |
| --- | --- | --- | --- |
| Embedding (50k vocab, 768d) | 38.4M | VocabSharded (tp=4) | 9.6M |
| Embedding (50k vocab, 768d) | 38.4M | ShardedEmbedding (tp=4) | 38.4M (full vocab) |
| Linear (768→3072, with bias) | 2.36M | ColumnSharded (tp=4) | 0.59M |
| Linear (3072→768, with bias) | 2.36M | RowSharded (tp=4) | 0.59M |

**Note**: `VocabShardedEmbedding` reduces memory per rank, while `ShardedEmbedding` keeps full memory but distributes computation. Column and row sharded linear layers both reduce memory proportionally to `tp_size`.

**Sources**: src/fairseq2/nn/embedding.py src/fairseq2/nn/projection.py

## Conversion Between Sharded and Standard

Sharded variants provide bidirectional conversion methods:

**Sharding** (standard → sharded):

**Unsharding** (sharded → standard):

**Implementation details**:

* `from_X` methods: Split weights along shard dimension, copy appropriate shard to each rank
* `to_X` methods: Gather weights from all ranks, reconstruct full parameter tensors
**Sources**: src/fairseq2/nn/embedding.py117-169 src/fairseq2/nn/embedding.py273-288 src/fairseq2/nn/projection.py132-187 src/fairseq2/nn/projection.py292-318

---

## Related

- fairseq2 Core Architecture
- fairseq2 Neural Network Components
- fairseq2 Transformer Layers
- fairseq2 Position Encoders
- fairseq2 Gang System
- fairseq2 Distributed Training
- fairseq2 Model Architectures
- fairseq2 Model Families