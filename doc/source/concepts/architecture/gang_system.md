---
myst:
  html_meta:
    "description lang=en": "fairseq2 Gang System"
    "keywords": "fairseq2, architecture, documentation"
---

# Distributed Processing with Gang


This document covers fairseq2's distributed computing abstraction layer, centered around the `Gang` interface and related components. The Gang system provides a unified API for collective operations across multiple processes, supporting various parallelism strategies including data parallelism, tensor parallelism, and sharded data parallelism.

For information about neural network module utilities that work with gangs, see fairseq2 Neural Network Components. For training infrastructure that uses gangs, see fairseq2 Training System. For distributed training strategies (DDP, FSDP, TP, HSDP), see fairseq2 Distributed Training. For high-level architecture context, see Core Architecture (§ Distributed Processing Overview).

## Gang Abstraction Layer

The `Gang` interface serves as fairseq2's primary abstraction for distributed computing, providing a consistent API regardless of the underlying implementation. It represents a set of processes that work collectively and supports standard collective communication operations.

**Sources:** src/fairseq2/gang.py36-126 src/fairseq2/gang.py147-266 src/fairseq2/gang.py268-491

### Gang Implementations

The system provides two concrete implementations:

* **`FakeGang`**: A non-distributed implementation for single-process execution or testing. It simulates collective operations locally and does not require PyTorch's distributed backend.
* **`ProcessGroupGang`**: A distributed implementation that wraps PyTorch's `ProcessGroup`. It supports NCCL backend for CUDA devices and Gloo backend for CPU devices, with automatic backend selection based on device type.

**Sources:** src/fairseq2/gang.py276-362 src/fairseq2/gang.py535-538

## Parallelism Management with Gangs

The `Gangs` dataclass organizes different types of gangs to support various parallelism strategies (see Distributed Training Strategies (§ Overview of Parallelism Strategies)). Each gang represents a different dimension of the parallel execution topology.

**Sources:** src/fairseq2/gang.py504-523

### Parallel Gang Creation

The `create_parallel_gangs()` function establishes the topology for data and tensor parallelism by partitioning the root gang into smaller sub-gangs.

| Gang Type | Purpose | Example (8 devices, tp\_size=2) |
| --- | --- | --- |
| **Data Parallel** | Different data batches | `[g0,g2,g4,g6]`, `[g1,g3,g5,g7]` |
| **Tensor Parallel** | Model parameters split | `[g0,g1]`, `[g2,g3]`, `[g4,g5]`, `[g6,g7]` |

**Sources:** src/fairseq2/gang.py541-667

### FSDP Gang Configuration

The `create_fsdp_gangs()` function extends the gang topology to support Fully Sharded Data Parallelism (FSDP) by creating intra-node and inter-node gangs. See FSDP Strategy (§ Fully Sharded Data Parallelism (FSDP)) for detailed usage.

**Sources:** src/fairseq2/gang.py670-793

## Collective Operations

The Gang interface standardizes collective communication patterns used throughout distributed training and inference.

### Core Collective Operations

**Sources:** src/fairseq2/gang.py52-106 src/fairseq2/gang.py128-136

### Utility Functions

The module provides convenience functions that wrap common collective operation patterns:

* `broadcast_flag()`: Broadcasts a boolean value across all processes
* `all_sum()`: Sums a scalar value across all processes and returns the result

**Sources:** src/fairseq2/gang.py796-811

## Module Integration

The Gang system integrates with PyTorch modules through several utility functions that handle distributed aspects of model management.

### Module Broadcasting

The `broadcast_module()` function synchronizes model parameters and buffers across all processes in a gang, ensuring consistent initialization in distributed training.

**Sources:** src/fairseq2/nn/utils/module.py370-454

### DDP Integration

The `to_ddp()` function wraps modules with PyTorch's `DistributedDataParallel`, handling gang-specific configuration and initialization. See DDP Strategy (§ Data Parallel Training (DDP)) for implementation details.

**Sources:** src/fairseq2/nn/ddp.py30-102

## Error Handling and Reliability

The Gang system includes comprehensive error handling for distributed operations:

* **`GangError`**: Base exception for gang-related failures
* **`raise_operational_gang_error()`**: Converts gang errors to operational errors
**Sources:** src/fairseq2/gang.py138-143 src/fairseq2/gang.py322-324

## Process Group Management

For CUDA devices, the system leverages PyTorch's experimental `split_group` API when available, which provides more efficient process group creation through NCCL's `ncclCommSplit` functionality.

**Sources:** src/fairseq2/gang.py599-612 src/fairseq2/gang.py635-648 src/fairseq2/gang.py729-742

This Gang abstraction provides fairseq2 with a flexible and efficient foundation for all distributed computing needs, from simple data parallelism to complex multi-dimensional parallelism strategies.


