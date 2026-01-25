---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - training
  - optimizers
---
# Optimizers and Learning Rate Schedulers


## Purpose and Scope

This document describes the optimization components in fairseq2, including optimizers (such as AdamW) and learning rate schedulers. It covers how these components integrate with the training recipe system, support distributed training through the Gang abstraction, and maintain state for checkpointing and reproducibility.

For information about the broader training infrastructure, see fairseq2 Training System. For details on checkpoint management, see fairseq2 Checkpoint Management. For distributed training strategies that affect gradient synchronization, see fairseq2 Distributed Training. For the Gang system fundamentals, see fairseq2 Gang System. For the broader architecture context, see fairseq2 Core Architecture.

---

## Optimizer Integration in Training System

Optimizers in fairseq2 are integrated into the recipe execution flow as part of the standard training loop. The training system follows a canonical pattern:

The optimizer step occurs after the backward pass computes gradients, updating model parameters based on the accumulated gradients and the configured optimization algorithm.

Sources: High-level architecture diagrams (Diagram 7: Training Recipe Execution Flow)

---

## State Management and Checkpointing

### Stateful Protocol

Optimizers and schedulers implement the `Stateful` protocol, which provides a standard interface for saving and loading state during checkpointing:

The `Stateful` protocol defines two methods:

* `state_dict()`: Returns a dictionary containing the complete state
* `load_state_dict(state_dict)`: Restores state from a dictionary

This protocol enables optimizers and schedulers to be saved alongside model weights during checkpoint operations, ensuring training can be resumed exactly where it left off.

Sources: src/fairseq2/typing.py16-20

### State Dictionary Structure

Optimizer state dictionaries typically contain:

* **Parameter groups**: Configuration for different parameter sets (learning rates, weight decay, etc.)
* **State per parameter**: Momentum buffers, adaptive learning rate statistics (for Adam/AdamW)
* **Step count**: Current optimization step for algorithms that depend on iteration number

Learning rate scheduler state dictionaries contain:

* **Last epoch/step**: Current position in the schedule
* **Base learning rates**: Initial learning rates for each parameter group
* **Scheduler-specific state**: Additional state for complex schedulers (e.g., warm restart counters for cosine annealing)

---

## Random Number Generation for Reproducibility

The training system uses `RngBag` to manage random number generators across devices, ensuring reproducible training:

The `RngBag` class provides:

* **Device-specific generators**: Separate RNGs for CPU and each CUDA device
* **Synchronized seeding**: `manual_seed()` sets the same seed across all generators
* **Temporary state changes**: `temporary_manual_seed()` context manager for deterministic operations
* **Checkpoint support**: State can be saved and restored via the `Stateful` protocol

Key methods:

* `manual_seed(seed)`: Set seed across all generators (seed must be in 0, 2^32))\n- `seed()`

---

## Learning Rate Scheduling Strategies

Based on the research foundations in fairseq2's bibliography, the system supports various learning rate scheduling strategies:

### Cosine Annealing with Warm Restarts

The "SGDR: Stochastic Gradient Descent with Warm Restarts" paper (Loshchilov & Hutter, 2017) describes a cosine annealing schedule with periodic restarts. This strategy:

### Common Scheduling Patterns

| Pattern | Description | Use Case |
| --- | --- | --- |
| **Linear Warm-up** | Gradually increase LR from 0 to peak | Stabilize training at start |
| **Cosine Decay** | Smooth decrease following cosine curve | Standard training schedules |
| **Polynomial Decay** | Power function decrease | Alternative to cosine |
| **Step Decay** | Discrete drops at intervals | Legacy schedules |
| **Inverse Square Root** | Decay proportional to 1/√step | Transformer training (Vaswani et al.) |

Sources: bibliography.bib29-36 bibliography.bib48-57

---

## Integration with Distributed Training

### Gradient Synchronization

Optimizers must coordinate with the Gang system for distributed training. The synchronization strategy depends on the parallelism approach:

**DDP (DistributedDataParallel):**

**FSDP (Fully Sharded Data Parallel):**

**Tensor Parallelism:**

Sources: src/fairseq2/nn/ddp.py30-103 src/fairseq2/gang.py648-714

### Gradient Normalization

The DDP wrapper provides control over gradient normalization:

When `normalize_grads=False`, fairseq2 registers a custom communication hook that performs all-reduce without dividing by the world size. This is beneficial for sequence modeling tasks where batch sizes vary across steps, as the effective learning rate remains more stable.

Sources: src/fairseq2/nn/ddp.py99-152

---

## Optimizer Configuration in Recipes

The recipe system integrates optimizers through structured configuration dataclasses:

Configuration examples in YAML format:

The dependency injection system (see Runtime Infrastructure) resolves optimizer and scheduler factories, instantiating them with the configured parameters.

Sources: High-level architecture diagrams (Diagram 7: Training Recipe Execution Flow)

---

## Parameter Selection and Grouping

Fairseq2 provides utilities for selecting subsets of parameters with different optimization settings:

The `select_parameters()` function enables creating parameter groups with different hyperparameters:

**Function signature:**

**Common use cases:**

| Pattern | Configuration | Rationale |
| --- | --- | --- |
| **Bias and LayerNorm** | No weight decay | These parameters typically benefit from different regularization |
| **Embedding layers** | Lower learning rate | Embeddings often need more careful updates |
| **Frozen layers** | Learning rate = 0 | Explicitly prevent updates to specific layers |

Example usage pattern:

Sources: src/fairseq2/nn/utils/module.py299-320

---

## Deterministic Training

For reproducible optimization, fairseq2 provides utilities to enable deterministic algorithms:

**Key function:**

When enabled:

* `warn_only=True`: Warns instead of erroring when deterministic implementation unavailable

Combined with `RngBag.manual_seed()`, this ensures reproducible training runs.

Sources: src/fairseq2/utils/rng.py22-33

---

## Checkpoint State Management

### Saving Optimizer State

During checkpoint operations, optimizer and scheduler states are saved alongside model parameters:

### Loading and Resuming

When resuming training from a checkpoint:

1. **Model parameters** are restored first using checkpoint management utilities
2. **Optimizer state** is loaded to restore momentum and adaptive statistics
3. **Scheduler state** is loaded to resume at the correct position in the schedule
4. **RNG state** is restored for reproducible data sampling and stochastic operations

The state restoration ensures that resumed training continues seamlessly, as if the interruption never occurred.

Sources: src/fairseq2/models/utils/checkpoint.py19-95 src/fairseq2/utils/rng.py113-146

---

## State Dict Error Handling

Fairseq2 provides robust error handling for state dictionary operations:

The `StateDictError` exception provides detailed error messages when:

This error handling is particularly important during checkpoint loading, where mismatches between saved and current optimizer/scheduler configurations can occur.

Example error patterns:

* **Missing key**: "`state_dict` is expected to contain a key named 'generators'."
* **Type mismatch**: "`state_dict['generators']` is expected to be of type `list`, but is of type `dict` instead."
* **Size mismatch**: "Number of generators in `state_dict['generators']` is expected to match the number of generators in the bag (2), but is 1 instead."

Sources: src/fairseq2/utils/rng.py118-146 src/fairseq2/models/utils/checkpoint.py19-98

---

## Summary

The optimizer and learning rate scheduler system in fairseq2:

1. **Implements the Stateful protocol** for seamless checkpointing and resumption
2. **Integrates with the Gang system** for gradient synchronization in distributed training
3. **Supports parameter grouping** for differential treatment of different parameter types
4. **Provides deterministic training** through RNG management and algorithm selection
5. **Follows research best practices** including cosine annealing with warm restarts
6. **Handles state management robustly** with detailed error reporting

The system is designed to work seamlessly with fairseq2's recipe execution framework, providing a complete training solution that scales from single-GPU to large-scale distributed training.

---

## Related

- fairseq2 Core Architecture
- fairseq2 Training System
- fairseq2 Checkpoint Management
- fairseq2 Distributed Training
- fairseq2 Gang System
- fairseq2 Runtime Infrastructure