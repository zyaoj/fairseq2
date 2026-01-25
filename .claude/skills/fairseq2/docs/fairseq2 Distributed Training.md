---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - training
  - distributed
---
# Distributed Training Strategies


## Purpose and Scope

This page documents the distributed training strategies supported by fairseq2, including Data Parallel (DDP), Fully Sharded Data Parallelism (FSDP), Tensor Parallelism (TP), and Hybrid Sharded Data Parallelism (HSDP). These strategies enable efficient training of large models across multiple devices by partitioning computation, parameters, and gradients.

For the underlying communication primitives and gang abstraction, see fairseq2 Gang System. For tensor-parallel layer implementations (sharded embeddings and projections), see fairseq2 Embeddings and Projections. For integration with the training loop, see fairseq2 Training System. For high-level architecture, see Core Architecture (§ Distributed Processing Overview).

**v0.7 Updates**:
- 20%+ speedup in SeamlessNext training with ongoing DDP and communication overhead optimizations
- Hardware support added for GB200 and ARM architectures
- Migration to fair-sc(-3) clusters

## Overview of Parallelism Strategies

fairseq2 supports multiple parallelism strategies that can be combined to optimize training efficiency:

| Strategy | Abbreviation | Parameters | Gradients | Optimizer States | Use Case |
| --- | --- | --- | --- | --- | --- |
| Data Parallel | DP | Replicated | All-reduced | Replicated | Small models, high throughput |
| Distributed Data Parallel | DDP | Replicated | All-reduced | Replicated | Medium models, gradient bucketing |
| Fully Sharded Data Parallel | FSDP | Sharded | Sharded | Sharded | Large models, memory efficiency |
| Tensor Parallel | TP | Sharded | Sharded | Sharded | Very large layers, low latency |
| Hybrid Sharded Data Parallel | HSDP | Sharded intra-node, replicated inter-node | Mixed | Sharded intra-node | Multi-node training, optimal bandwidth usage |

**Key Design Principles:**

1. **Gang-based abstraction**: All strategies use the Gang interface for collective operations, enabling consistent APIs across different parallelism types
2. **Composability**: Strategies can be combined (e.g., FSDP + TP) by using separate gangs for each dimension
3. **Transparent integration**: Sharded layers work seamlessly with FSDP by coordinating through gang topology (see Core Architecture Design Patterns (§ Design Patterns))

Sources: src/fairseq2/gang.py7-16 src/fairseq2/gang.py647-689

## Gang Topology for Distributed Training

The `Gangs` container holds references to all parallel gangs used in a distributed configuration. Gang creation functions split the root gang into non-overlapping sub-gangs for each parallelism dimension. See Gang System (§ Parallelism Management with Gangs) for detailed gang management.

**Gang Creation Functions:**

* **`create_parallel_gangs(root_gang, tp_size)`**: Creates DP and TP gangs from a root gang by splitting processes into a 2D mesh
* **`create_fsdp_gangs(gangs, intra_node_size)`**: Further splits the DP gang into intra-node (sdp) and inter-node (rdp) sub-gangs for hybrid sharding

Sources: src/fairseq2/gang.py647-689 src/fairseq2/gang.py907-1031 src/fairseq2/gang.py1034-1082

## Gang Mesh Construction

**Implementation Details:**

The mesh construction uses PyTorch's `split_group` API (PyTorch 2.5+) for NCCL backends on CUDA devices, which provides optimized gang creation through `ncclCommSplit`. For other backends, gangs are created sequentially using `create_gang()`.

Sources: src/fairseq2/gang.py907-1031 src/fairseq2/gang.py1034-1155

## Data Parallel Training (DDP)

Distributed Data Parallel (DDP) replicates the model across all processes in the data parallel gang and synchronizes gradients using all-reduce after the backward pass.

**Key Functions:**

* **`to_ddp(module, gangs, ...)`**: Wraps a module with DDP, handling meta initialization and buffer broadcasting
* **`_broadcast_buffers(module, gang)`**: Synchronizes persistent buffers across all processes before training begins
* **`_all_reduce_hook(gang, bucket)`**: Custom gradient reduction hook that skips normalization by world size

**Meta Initialization Support:**

DDP supports meta device initialization to reduce memory overhead during model construction. Only rank 0 materializes parameters, while other ranks use empty tensors that will be overwritten during the initial broadcast:

**Gradient Normalization:**

By default, DDP normalizes gradients by dividing by the world size. For variable-length sequences, this behavior can be disabled by setting `normalize_grads=False`, which installs a custom communication hook that performs all-reduce without division.

Sources: src/fairseq2/nn/ddp.py30-102 src/fairseq2/nn/ddp.py105-139 src/fairseq2/nn/ddp.py141-152

## Fully Sharded Data Parallelism (FSDP)

FSDP shards model parameters, gradients, and optimizer states across processes to reduce per-device memory usage. fairseq2 supports both PyTorch FSDP1 and FSDP2 implementations.

**FSDP Gangs:**

FSDP uses the `sdp` (sharded data parallel) gang for parameter sharding. In hybrid sharding configurations (HSDP), FSDP uses both `sdp` for intra-node sharding and `rdp` for inter-node replication:

| Configuration | sdp Gang | rdp Gang | Communication Pattern |
| --- | --- | --- | --- |
| Full Sharding | `gangs.dp` | Fake gang (size 1) | All-gather across all DP ranks |
| Hybrid Sharding | Intra-node gang | Inter-node gang | All-gather within node, all-reduce across nodes |

**Layerwise FSDP:**

For memory efficiency, FSDP can be applied to individual transformer layers rather than the entire model:

This approach reduces peak memory usage during forward/backward passes by limiting the amount of parameters that must be all-gathered at any given time.

Sources: src/fairseq2/gang.py1034-1082 src/fairseq2/models/transformer/fsdp.py17-37

## Tensor Parallelism

Tensor Parallelism (TP) shards individual weight matrices across multiple devices, enabling the training of models with layers too large to fit on a single device. fairseq2 implements TP through specialized layer types that coordinate through the `tp` gang.

**Sharded Layer Types:**

fairseq2 provides three types of sharded layers for tensor parallelism:

1. **`ColumnShardedLinear`**: Splits output dimension across `tp_gang`, no communication in forward pass
2. **`RowShardedLinear`**: Splits input dimension across `tp_gang`, all-reduce in forward pass
3. **`VocabShardedEmbedding`**: Splits vocabulary dimension across `tp_gang`, all-reduce after embedding lookup

**Communication Patterns:**

The sharded layers use different collective operations based on their sharding strategy:

These communication patterns ensure mathematical equivalence with the non-sharded variants while distributing computation and memory across devices.

Sources: src/fairseq2/gang.py647-689

## Hybrid Sharding Strategies (HSDP)

Hybrid Sharded Data Parallelism (HSDP) combines FSDP's memory efficiency with DDP's communication efficiency by sharding parameters within nodes and replicating across nodes.

**Benefits of HSDP:**

1. **Reduced inter-node communication**: Only gradients are all-reduced across nodes, not full parameters
2. **Efficient intra-node bandwidth**: High-speed NVLink/NVSwitch used for parameter all-gather
3. **Scalability**: Combines benefits of FSDP (memory) and DDP (communication efficiency)

**Gang Configuration:**

**Communication Volume Comparison:**

| Strategy | Forward Pass | Backward Pass | Optimizer Step |
| --- | --- | --- | --- |
| DDP | None | All-reduce gradients (P) | None |
| FSDP | All-gather params (P) | Reduce-scatter grads (P) | None |
| HSDP | All-gather params (P/R) intra-node | All-reduce grads (P/R) inter-node + reduce-scatter (P/R) intra-node | None |

Where P = parameter count, R = replication factor (rdp gang size).

Sources: src/fairseq2/gang.py1034-1155 src/fairseq2/nn/ddp.py46-50

## Model Initialization and Broadcasting

fairseq2 provides utilities for initializing and synchronizing model parameters across distributed processes, with special support for meta device initialization.

**Key Functions:**

* **`broadcast_module(module, gang, source_rank=0)`**: Broadcasts all parameters and persistent buffers from source rank to all other ranks
* **`to_device(module, device)`**: Moves module to device, handling meta initialization if needed
* **`to_empty(module, device)`**: Creates empty tensors on device without copying storage (for meta device)

**Meta Device Initialization:**

Meta device initialization reduces memory overhead by deferring parameter allocation until necessary:

This pattern is used internally by both `to_ddp()` and FSDP wrappers to minimize peak memory usage during initialization.

**Broadcast Implementation:**

The broadcast operation uses PyTorch's `_broadcast_coalesced` for efficient multi-tensor broadcasting:

Tensors are collected in post-order traversal to match the order expected by DDP and FSDP wrappers.

Sources: src/fairseq2/nn/utils/module.py370-454 src/fairseq2/nn/utils/module.py98-136 src/fairseq2/nn/utils/module.py137-162

## Combining Parallelism Strategies

Multiple parallelism strategies can be combined to optimize training for different model sizes and hardware configurations.

**Memory and Computation Distribution:**

| Layer Type | Parameters per Device | Computation per Device | Communication |
| --- | --- | --- | --- |
| Regular layer with FSDP | P / (sdp\_size) | Same as single device | All-gather (intra-node), all-reduce (inter-node) |
| ColumnShardedLinear with FSDP | P / (tp\_size × sdp\_size) | 1/tp\_size of matmul | FSDP all-gather + backward reduce |
| RowShardedLinear with FSDP | P / (tp\_size × sdp\_size) | 1/tp\_size of matmul | FSDP all-gather + forward all-reduce |

**Initialization Order:**

1. Create root gang from process group
2. Create parallel gangs (DP + TP) using `create_parallel_gangs()`
3. Optionally split DP gang into SDP + RDP using `create_fsdp_gangs()`
4. Construct model with sharded layers that reference `gangs.tp`
5. Wrap model or layers with FSDP using `gangs.sdp` and `gangs.rdp`

This layered approach allows fine-grained control over memory-compute tradeoffs while maintaining a clean separation of concerns between different parallelism dimensions.

Sources: src/fairseq2/gang.py907-1031 src/fairseq2/gang.py1034-1155 src/fairseq2/gang.py647-689


