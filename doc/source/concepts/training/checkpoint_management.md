---
myst:
  html_meta:
    "description lang=en": "fairseq2 Checkpoint Management"
    "keywords": "fairseq2, training, documentation"
---

# Checkpoint Management


## Purpose and Scope

This document explains fairseq2's checkpoint management system, which handles saving, loading, converting, and broadcasting model checkpoints. The system supports multiple checkpoint formats, distributed loading with sharding, state dict conversion for framework compatibility, and model synchronization across processes.

For information about training recipes that use checkpoints, see fairseq2 Recipes and CLI. For distributed training strategies that affect checkpoint loading, see fairseq2 Distributed Training. For model family abstractions that integrate with checkpoint loading, see fairseq2 Model Families. For the broader architecture context, see fairseq2 Core Architecture.

## Checkpoint Loading Architecture

The checkpoint management system provides a multi-stage pipeline that handles checkpoint retrieval, conversion, and loading into model instances:

**Sources:** src/fairseq2/models/family.py446-605 src/fairseq2/models/utils/checkpoint.py19-94 src/fairseq2/nn/utils/module.py370-453

## Loading from Asset Cards

The `StandardModelFamily` class provides the primary interface for loading models from asset cards. The loading process handles checkpoint download, format conversion, distributed loading, and model synchronization.

### Load Model Flow

**Sources:** src/fairseq2/models/family.py446-532 src/fairseq2/models/family.py553-605

### Download Coordination

Only rank 0 downloads the checkpoint to avoid redundant network traffic and filesystem contention:

**Sources:** src/fairseq2/models/family.py607-619

### Key Components

| Component | Purpose | Location |
| --- | --- | --- |
| `StandardModelFamily.load_model()` | Main entry point for loading from asset cards | src/fairseq2/models/family.py446-532 |
| `StandardModelFamily._do_load_model()` | Internal implementation of model loading | src/fairseq2/models/family.py553-605 |
| `StandardModelFamily._download_model()` | Coordinates checkpoint download across ranks | src/fairseq2/models/family.py607-619 |
| `AssetDownloadManager.download_model()` | Downloads checkpoint from URI | Referenced in src/fairseq2/models/family.py613 |

## Direct Checkpoint Loading

The `load_custom_model()` method provides direct checkpoint loading from filesystem paths without asset cards:

This method bypasses asset card resolution and download management, directly loading from the specified path using the same internal `_do_load_model()` implementation.

**Sources:** src/fairseq2/models/family.py534-551

## Checkpoint Iteration

The `iter_checkpoint()` method provides lazy, memory-efficient checkpoint loading by yielding name-tensor pairs:

**Sources:** src/fairseq2/models/family.py622-692

### Shard Dimension Extraction

For distributed loading, the system extracts shard dimensions from the model to determine how parameters should be split across processes:

| Source | Method | Description |
| --- | --- | --- |
| From Model | `get_shard_dims(model)` | Inspects model structure to extract sharding info from sharded layers |
| From Specs | `ShardSpecsProvider(config)` | Uses pre-defined shard specifications (deprecated) |

**Sources:** src/fairseq2/models/family.py573-576 src/fairseq2/models/family.py640-652

## State Dict Operations

### Setting Model State

The `set_model_state()` function copies checkpoint tensors into a model's parameters and buffers with progress tracking and validation:

**Implementation Details:**

**Sources:** src/fairseq2/models/utils/checkpoint.py19-94

### State Dict Conversion

The `convert_state_dict()` function applies regex-based key transformations to convert between checkpoint formats:

**Key Conversion Process:**

**Sources:** src/fairseq2/models/utils/checkpoint.py101-124

### Fairseq Legacy Conversion

The `convert_fairseq_state_dict()` function adapts checkpoints from the original fairseq framework:

**Removed Keys:**

* `encoder.version` / `decoder.version` - Version metadata
* `encoder.embed_positions._float_tensor` / `decoder.embed_positions._float_tensor` - Internal buffers

**Sources:** src/fairseq2/models/utils/checkpoint.py127-150

### Reverse Key Mapping

The `create_reverse_key_map()` function generates the inverse of a key mapping for bidirectional conversion:

**Sources:** src/fairseq2/models/utils/checkpoint.py153-180

## Model Broadcasting

Broadcasting synchronizes model parameters and buffers across all processes in a gang after rank 0 loads the checkpoint. This ensures all ranks have identical model state before training begins.

### Broadcasting Architecture

**Sources:** src/fairseq2/nn/utils/module.py370-453

### Broadcast Details

| Aspect | Implementation | Purpose |
| --- | --- | --- |
| **Device Alignment** | `to_device(module, gang.device)` | Ensures module is on gang's device before broadcast |
| **Tensor Collection** | Recursive traversal with memoization | Collects parameters and persistent buffers, skipping shared tensors |
| **Bucketing** | 250 MB buckets (same as DDP) | Balances communication efficiency with memory usage |
| **Buffer Filtering** | Checks `_non_persistent_buffers_set` | Only broadcasts persistent buffers; non-persistent are static |
| **Gradient Warning** | Warns if `param.grad` is set | Broadcasting doesn't support gradient synchronization |

**Sources:** src/fairseq2/nn/utils/module.py398-453

### Buffer Broadcasting in DDP

The `_broadcast_buffers()` function is used internally by DDP to synchronize buffers at initialization:

**Sources:** src/fairseq2/nn/ddp.py105-138

## Load State Dict

The `load_state_dict()` function provides an alternative to `set_model_state()` with additional validation:

**Key Differences from `set_model_state()`:**

| Aspect | `set_model_state()` | `load_state_dict()` |
| --- | --- | --- |
| Input Type | Iterator of (key, tensor) pairs | Complete state dict |
| Progress Tracking | Yes, with `ProgressReporter` | No |
| Validation | Shape checking, missing/unexpected keys | PyTorch's built-in + None module checking |
| Memory Efficiency | Lazy loading, immediate copy | Requires full state dict in memory |
| Use Case | Checkpoint loading from disk | In-memory state dict loading |

**Additional Validation:**

The function checks for keys corresponding to `None` modules (registered via `Module.register_module(name, None)`), which PyTorch's built-in method doesn't catch:

**Sources:** src/fairseq2/nn/utils/module.py456-485

## Checkpoint Load Options

The `ModelCheckpointLoadOptions` dataclass configures checkpoint loading behavior:

### Option Details

| Option | Type | Purpose |
| --- | --- | --- |
| `gangs` | `Gangs` | Provides gang configuration for distributed loading and sharding |
| `mmap` | `bool` | If `True`, memory-maps checkpoint files for efficient loading of large models |
| `restrict` | `bool` | If `True`, applies restrictions to checkpoint loading (implementation-specific) |
| `state_dict_converter` | `Callable | None` | Optional function to convert state dict keys/values during loading |

**Sources:** src/fairseq2/models/family.py684-689

## Complete Loading Example

Here's how the components work together in a typical model loading scenario:

**Sources:** src/fairseq2/models/family.py446-605

## Error Handling

The checkpoint management system defines specific exceptions for different failure scenarios:

| Exception | Raised When | Location |
| --- | --- | --- |
| `ModelCheckpointMismatchError` | Checkpoint structure doesn't match model | src/fairseq2/models/utils/checkpoint.py97-98 |
| `CorruptModelCheckpointError` | Checkpoint file is corrupted or invalid | Referenced in src/fairseq2/models/family.py516-522 |
| `StateDictError` | State dict contains unexpected structure | src/fairseq2/nn/utils/module.py485 |
| `GangError` | Distributed operation fails during broadcast | src/fairseq2/nn/utils/module.py453 |

**Example Error Messages:**

**Sources:** src/fairseq2/models/utils/checkpoint.py54-94 src/fairseq2/nn/utils/module.py480-485

---

## Related

- fairseq2 Core Architecture
- fairseq2 Model Families
- fairseq2 Training System
- fairseq2 Distributed Training
- fairseq2 Gang System
- fairseq2 Asset Management