---
myst:
  html_meta:
    "description lang=en": "fairseq2 Model Abstractions"
    "keywords": "fairseq2, models, documentation"
---

# Model Abstractions


## Purpose and Scope

This document covers the abstract base classes and interfaces that define the contracts for models in fairseq2. These abstractions provide a unified API that allows training recipes, inference utilities, and other components to work with different model architectures without depending on implementation details.

The primary focus is on the `Seq2SeqModel` interface, which is the foundational abstraction for sequence-to-sequence models. For information about specific model implementations, see Speech Models and Language Models. For information about how models are loaded and configured through the asset system, see Model Families. For integration with training, see fairseq2 Training System.

## Overview

Model abstractions in fairseq2 serve several purposes:

1. **Unified Interface**: Provide a consistent API for model forward passes, regardless of the underlying architecture
2. **Dual-Mode Operation**: Support both training (with loss computation) and inference (with optional incremental state)
3. **Type Safety**: Use Python type hints and overloads to enable static type checking
4. **Framework Integration**: Define clear integration points with other fairseq2 systems (data pipelines, distributed training, checkpointing)

**Diagram: Model Abstraction Architecture**

The abstraction layer allows consumer systems to depend on interfaces rather than concrete implementations, enabling flexibility in model selection and configuration.

Sources: src/fairseq2/models/seq2seq.py1-115

## Seq2SeqModel Interface

The `Seq2SeqModel` class is the primary abstraction for sequence-to-sequence models. It inherits from both `torch.nn.Module` and `ABC` (Abstract Base Class), making it a PyTorch module with abstract method requirements.

### Class Definition

The class is defined in src/fairseq2/models/seq2seq.py18-115

### Core Properties

| Property | Type | Purpose |
| --- | --- | --- |
| `max_source_seq_len` | `int` | Maximum sequence length supported for source (encoder input) |
| `max_target_seq_len` | `int` | Maximum sequence length supported for target (decoder input/output) |

These properties are set during initialization src/fairseq2/models/seq2seq.py21-25 and serve as metadata for:

### Relationship to PyTorch Module

**Diagram: Seq2SeqModel Inheritance**

By inheriting from `torch.nn.Module`, `Seq2SeqModel` implementations automatically support:

Sources: src/fairseq2/models/seq2seq.py18-25

## Forward Method Signatures

The `forward` method is the core operation of any model. `Seq2SeqModel` defines multiple overloaded signatures to support different use cases with full type safety. The method is declared abstract src/fairseq2/models/seq2seq.py97-111 requiring all concrete implementations to provide their own logic.

### Signature Modes

**Diagram: Forward Method Usage Modes**

### Mode 1: Inference

**Signature**: src/fairseq2/models/seq2seq.py28-36

**Purpose**: Generate logits for target sequences given source sequences. Used during inference and generation.

**Parameters**:

* `source_seqs`: Source sequence tensor (e.g., audio features, source text IDs)
* `source_seqs_layout`: Metadata describing the shape and structure of `source_seqs`
* `target_seqs`: Target sequence tensor (e.g., target text IDs, partially generated output)
* `target_seqs_layout`: Metadata describing the shape and structure of `target_seqs`
* `state_bag`: Optional container for incremental decoding state (cached key/value pairs in attention)

**Returns**: Tensor of shape `[N, S_tgt, V]` where N is batch size, S\_tgt is target sequence length, and V is vocabulary size.

**Use Cases**:

### Mode 2: Training (Loss Computation)

**Signature**: src/fairseq2/models/seq2seq.py52-65

**Purpose**: Compute cross-entropy loss for training. Most efficient mode as it doesn't return logits.

**Additional Parameters**:

* `targets`: Ground truth target token IDs, shape `[N, S_tgt]`
* `label_smoothing`: Label smoothing factor (0.0 = no smoothing, typical values: 0.1-0.2)
* `target_mask`: Optional mask indicating which positions to include in loss (shape `[N, S_tgt]`)
* `reduction`: How to aggregate loss across the batch ("sum" or "mean")
* `return_logits`: Must be `False` to use this signature

**Returns**: Scalar tensor containing the loss value (sum or mean depending on `reduction`).

**Use Cases**:

### Mode 3: Training (Loss + Logits)

**Signature**: src/fairseq2/models/seq2seq.py68-80

**Purpose**: Compute loss and return logits for additional analysis or metrics computation.

**Additional Parameters**: Same as Mode 2, except `return_logits` must be `True`.

**Returns**: Tuple of `(loss, logits)` where:

* `loss`: Scalar tensor containing the loss value
* `logits`: Tensor of shape `[N, S_tgt, V]` containing raw model outputs

**Use Cases**:

### Abstract Implementation

The actual implementation signature src/fairseq2/models/seq2seq.py97-111 combines all modes:

Concrete implementations must handle all three modes by checking:

1. `targets is None` → Mode 1 (Inference)
2. `targets is not None and return_logits is False` → Mode 2 (Loss only)
3. `targets is not None and return_logits is True` → Mode 3 (Loss + Logits)

Sources: src/fairseq2/models/seq2seq.py27-111

## Integration with Core Systems

### BatchLayout

`BatchLayout` is used to describe the structure of input tensors src/fairseq2/models/seq2seq.py31-32 src/fairseq2/models/seq2seq.py43-44 It provides metadata about:

This allows models to:

1. Skip computation on padded positions
2. Apply proper attention masks
3. Handle variable-length sequences efficiently

The separation of tensors and their layout metadata enables efficient batch processing while maintaining flexibility in how batches are constructed. For more information on batch layout, see fairseq2 Neural Network Components.

### IncrementalStateBag

`IncrementalStateBag` is used during inference src/fairseq2/models/seq2seq.py35 to store cached computation from previous time steps. This is critical for efficient autoregressive generation:

**Diagram: Incremental Decoding with State Caching**

Without `IncrementalStateBag`, generating a sequence of length N requires O(N²) computation (recomputing attention for all previous positions at each step). With caching, this becomes O(N).

The state bag is passed through the model hierarchy, allowing each attention layer to retrieve and update its cached key/value tensors. For more information on incremental decoding, see fairseq2 Neural Network Components.

Sources: src/fairseq2/models/seq2seq.py106

## Parameter Summary

The complete parameter set for the forward method:

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `source_seqs` | `Tensor` | Yes | - | Source sequence tensor |
| `source_seqs_layout` | `BatchLayout` | Yes | - | Source sequence layout metadata |
| `target_seqs` | `Tensor` | Yes | - | Target sequence tensor |
| `target_seqs_layout` | `BatchLayout` | Yes | - | Target sequence layout metadata |
| `targets` | `Tensor | None` | No | `None` | Ground truth targets for loss computation |
| `state_bag` | `IncrementalStateBag | None` | No | `None` | Cache for incremental decoding |
| `label_smoothing` | `float` | No | `0.0` | Label smoothing factor (0.0-1.0) |
| `target_mask` | `Tensor | None` | No | `None` | Mask for loss computation |
| `reduction` | `Literal["sum", "mean"]` | No | `"sum"` | Loss reduction method |
| `return_logits` | `bool` | No | `False` | Whether to return logits with loss |

Sources: src/fairseq2/models/seq2seq.py97-111

## Usage Examples

### Inference Mode

### Training Mode (Loss Only)

### Training Mode (Loss + Logits)

### Incremental Decoding

Sources: src/fairseq2/models/seq2seq.py1-115

## Type Safety Features

The `Seq2SeqModel` interface makes extensive use of Python's type hinting system src/fairseq2/models/seq2seq.py10 to provide compile-time type checking through tools like mypy.

### Overload Decorators

The interface uses `@overload` decorators src/fairseq2/models/seq2seq.py27-95 to define multiple type signatures for the same method. This enables:

1. **Return Type Inference**: The type checker knows that when `return_logits=True`, the return type is `tuple[Tensor, Tensor]`, otherwise it's `Tensor`
2. **Parameter Validation**: The type checker can verify that required parameters are provided for each mode
3. **IDE Support**: Code editors can provide accurate autocomplete and inline documentation

### TYPE\_CHECKING Block

The interface includes a special block src/fairseq2/models/seq2seq.py113-114:

This assigns the `__call__` method to point to `forward` only during type checking, ensuring that when the model is invoked as `model(...)`, type checkers understand it has the same signature as `forward(...)`.

Sources: src/fairseq2/models/seq2seq.py10 src/fairseq2/models/seq2seq.py27-114

## Extending the Abstraction

Concrete model implementations must subclass `Seq2SeqModel` and implement the abstract `forward` method. The implementation pattern typically follows:

For examples of concrete implementations, see Language Models and Speech Models.

Sources: src/fairseq2/models/seq2seq.py18-115

## Relationship to Model Families

The `Seq2SeqModel` abstraction works in conjunction with the Model Family system. The relationship is:

**Diagram: Model Abstraction in Asset Loading Pipeline**

This separation allows:

1. **Decoupling**: User code depends on the `Seq2SeqModel` interface, not concrete implementations
2. **Flexibility**: The asset system can load different model architectures as long as they implement `Seq2SeqModel`
3. **Testability**: Implementations can be swapped for testing without changing consumer code

Sources: src/fairseq2/models/seq2seq.py1-115


