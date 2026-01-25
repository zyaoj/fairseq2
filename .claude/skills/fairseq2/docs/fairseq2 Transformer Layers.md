---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - neural-network
  - transformer
---
# Transformer Layers


This page documents the transformer layer components in fairseq2, including attention mechanisms, feed-forward networks, and complete encoder/decoder layers. These components form the core building blocks of transformer-based models.

For information about embeddings and projections used by these layers, see fairseq2 Embeddings and Projections. For position encoding strategies, see fairseq2 Position Encoders. For complete model architectures that use these layers, see fairseq2 Model Architectures. For distributed training integration, see Distributed Processing with Gang and fairseq2 Distributed Training. For the broader neural network context, see fairseq2 Neural Network Components. For the theoretical foundations, see fairseq2 Research Foundations. For the broader architecture context, see fairseq2 Core Architecture.

## Architecture Overview

Transformer layers in fairseq2 follow a modular design with several abstraction levels:

**Sources:** src/fairseq2/models/transformer/model.py1-289 src/fairseq2/models/conformer/block.py1-197

## Attention Mechanisms

### MultiheadAttention Base Class

The `MultiheadAttention` abstract base class defines the interface for all attention mechanisms:

Key methods:

* `forward(queries, queries_layout, keys, keys_layout, values, *, bias_cache, state_bag)` - Computes attention
**Sources:** Referenced from src/fairseq2/models/conformer/block.py160-167

### StandardMultiheadAttention

Implements scaled dot-product attention with the formula:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d\_k}}\right)V$$

Key features:

**Sources:** Standard attention mechanism referenced throughout encoder/decoder implementations

### Attention Bias and Masking

Attention mechanisms use `AttentionBiasCache` to efficiently compute and cache attention masks:

| Mask Type | Purpose | Usage |
| --- | --- | --- |
| Padding mask | Ignore padding tokens | Created from `BatchLayout.position_indices` |
| Causal mask | Prevent attending to future positions | Used in decoder self-attention |
| Cross-attention mask | Encoder-decoder attention constraints | Used in decoder cross-attention |

**Sources:** src/fairseq2/models/conformer/block.py124

## Feed-Forward Networks

### FeedForwardNetwork Class

Position-wise feed-forward networks apply two linear transformations with an activation:

$$\text{FFN}(x) = \text{activation}(xW\_1 + b\_1)W\_2 + b\_2$$

Common configurations:

* **Standard FFN**: `inner_dim = 4 * model_dim`, ReLU activation
* **SwiGLU FFN**: Uses SiLU activation with gating, `inner_dim ≈ 8/3 * model_dim`
* **GELU FFN**: Used in BERT-like models

**Sources:** Referenced from src/fairseq2/models/conformer/block.py35

### Gated Linear Units (GLU)

GLU variants split the inner dimension and use one half as a gate:

$$\text{GLU}(x) = (xW\_1) \odot \sigma(xW\_2)$$

Variants include:

* `GLU`: sigmoid gating
* `SwiGLU`: SiLU (swish) gating, used in LLaMA models
* `GeGLU`: GELU gating

**Sources:** src/fairseq2/models/conformer/convolution.py66

## Transformer Encoder Layers

### TransformerEncoderLayer Structure

Standard transformer encoder layer with pre-normalization:

Implementation details:

**Sources:** Architecture referenced from src/fairseq2/models/conformer/block.py28

### TransformerEncoder Stack

`TransformerEncoder` stacks multiple encoder layers:

Key features:

**Sources:** src/fairseq2/models/transformer/model.py161

## Transformer Decoder Layers

### TransformerDecoderLayer Structure

Decoder layer with self-attention, cross-attention, and feed-forward network:

Differences from encoder layer:

* **Causal self-attention**: Prevents attending to future positions
* **Cross-attention**: Attends to encoder output
* **Incremental decoding**: Supports key-value caching via `state_bag`

**Sources:** src/fairseq2/models/transformer/model.py180-186

### TransformerDecoder Stack

`TransformerDecoder` stacks multiple decoder layers:

**Sources:** src/fairseq2/models/transformer/model.py58

## Complete Transformer Model

### TransformerModel Architecture

The `TransformerModel` class combines all components into a complete sequence-to-sequence model:

Key components from src/fairseq2/models/transformer/model.py29-60:

| Component | Type | Purpose |
| --- | --- | --- |
| `encoder_frontend` | `TransformerFrontend` | Embedding + position encoding for source |
| `encoder` | `TransformerEncoder` | Stack of encoder layers |
| `decoder_frontend` | `TransformerFrontend` | Embedding + position encoding for target |
| `decoder` | `TransformerDecoder` | Stack of decoder layers |
| `final_proj` | `Projection` | Projects decoder output to vocabulary |

**Sources:** src/fairseq2/models/transformer/model.py29-60

### Forward Pass Flow

The `TransformerModel.forward()` method src/fairseq2/models/transformer/model.py137-214 implements:

1. **Encoder path** (lines 156-162):

   * Apply encoder frontend (embedding + position encoding)
   * Pass through encoder layers
   * Cache encoder output for incremental decoding
2. **Decoder path** (lines 176-186):

   * Apply decoder frontend
   * Pass through decoder layers with encoder output
   * Support incremental state via `state_bag`
3. **Output projection** (lines 190-213):

   * Project to vocabulary dimension
   * Optionally compute cross-entropy loss
   * Support fused loss computation for efficiency

### Incremental Decoding State

The `_TransformerModelState` class src/fairseq2/models/transformer/model.py265-289 caches encoder output to avoid recomputation during autoregressive generation:

State management:

**Sources:** src/fairseq2/models/transformer/model.py265-289

## Specialized Layer Variants

### ConformerBlock

`ConformerBlock` extends `TransformerEncoderLayer` with a macaron-style architecture and convolutional module:

Key differences from standard encoder layer src/fairseq2/models/conformer/block.py32-46:

* **Macaron-style**: Two half-step FFNs (outputs scaled by 0.5)
* **Convolution module**: Between attention and second FFN
* **Pre-normalization**: LayerNorm before each sub-block
* **Final normalization**: LayerNorm after all residual connections

**Sources:** src/fairseq2/models/conformer/block.py28-197

### ConformerConvolution Module

The convolution module src/fairseq2/models/conformer/convolution.py24-183 uses depthwise-separable convolutions:

Features:

* **Pointwise convolution**: 1×1 conv for channel mixing
* **Depthwise convolution**: Separate conv per channel
* **GLU gating**: First pointwise conv uses gating
* **Causal option**: For streaming/online models

**Sources:** src/fairseq2/models/conformer/convolution.py24-183

## Integration with Distributed Training

### Tensor Parallelism in Layers

Transformer layers integrate with the Gang system for tensor parallelism. Sharded variants of projections are used within layers:

| Layer Component | Sharding Strategy | Implementation |
| --- | --- | --- |
| Attention QKV projection | Column sharding | `ColumnShardedLinear` with `gather_output=False` |
| Attention output projection | Row sharding | `RowShardedLinear` with `reduce_output=True` |
| FFN first projection | Column sharding | `ColumnShardedLinear` with `gather_output=False` |
| FFN second projection | Row sharding | `RowShardedLinear` with `reduce_output=True` |

Communication pattern:

1. **Column-sharded layers**: Use `reduce_on_backward()` on inputs
2. **Row-sharded layers**: Use `reduce()` on outputs
3. **Between layers**: Outputs are gathered or reduced before next layer

**Sources:** src/fairseq2/nn/projection.py128-362 src/fairseq2/nn/projection.py365-597

### Sharding Communication Flow

This communication pattern minimizes collectives while maintaining mathematical equivalence to non-sharded computation.

**Sources:** src/fairseq2/nn/projection.py279-290 src/fairseq2/nn/projection.py517-532

### Data Parallelism

Transformer layers are wrapped with DDP or FSDP for data parallelism:

* **DDP**: Gradient all-reduce across `dp_gang` or `rdp_gang`
* **FSDP**: Parameter sharding across `sdp_gang`, gradient reduce-scatter
* **Hybrid**: FSDP within nodes (`sdp_gang`), DDP across nodes (`rdp_gang`)

The Gang system (see Distributed Processing with Gang) provides unified abstractions for these patterns.

**Sources:** Referenced from distributed training context in high-level diagrams

## Layer Normalization Strategies

### Pre-normalization vs Post-normalization

fairseq2 primarily uses **pre-normalization** (LayerNorm before sub-layers):

**Pre-normalization** (standard in fairseq2):

```python
x = x + SubLayer(LayerNorm(x))
```

Benefits:

**Post-normalization** (original Transformer paper):

```python
x = LayerNorm(x + SubLayer(x))
```

**Sources:** Architecture patterns from src/fairseq2/models/conformer/block.py138-196

### LayerNorm Implementations

fairseq2 provides multiple LayerNorm implementations:

| Class | Features | Use Case |
| --- | --- | --- |
| `StandardLayerNorm` | Standard PyTorch LayerNorm | Default choice |
| `RMSNorm` | No mean centering, faster | LLaMA models |
| `LayerNorm` | Abstract base class | Custom implementations |

**Sources:** Referenced from normalization usage in transformer layers

## Initialization Strategies

### Weight Initialization

Different components use different initialization schemes:

**Linear projections** src/fairseq2/nn/projection.py638-656:

**BERT-style initialization** src/fairseq2/nn/projection.py659-664:

**Embeddings** src/fairseq2/nn/embedding.py511-522:

**Sources:** src/fairseq2/nn/projection.py629-665 src/fairseq2/nn/embedding.py511-533

### Layer-specific Initialization

Attention mechanisms and FFNs may use model-specific initialization:

Initialization is typically handled by model builders (see fairseq2 Model Families).

**Sources:** Initialization patterns referenced throughout model implementations

---

## Related

- fairseq2 Core Architecture
- fairseq2 Neural Network Components
- fairseq2 Embeddings and Projections
- fairseq2 Position Encoders
- fairseq2 Model Architectures
- fairseq2 Gang System
- fairseq2 Distributed Training
- fairseq2 Research Foundations
- fairseq2 Model Families