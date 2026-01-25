---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - architecture
  - data-pipeline
---
# Data Processing Pipeline


This document covers fairseq2's data processing pipeline system, which provides efficient data loading, transformation, and batching capabilities for training and inference workflows. The pipeline system is built around the `DataPipeline` and `DataPipelineBuilder` classes and supports stateful iteration with checkpoint persistence.

For information about dataset management and data readers, see fairseq2 Data Management. For asset management of models and tokenizers, see fairseq2 Asset Management. For high-level architecture, see Core Architecture (§ Data Processing Overview). For integration with training workflows, see fairseq2 Training System.

## Overview

The fairseq2 data processing pipeline is a flexible, high-performance system designed for machine learning workloads. It provides a fluent API for constructing data processing graphs that can handle various data sources, apply transformations, perform batching operations, and combine multiple data streams.

## Pipeline Architecture

The fairseq2 data pipeline follows the fluent API design pattern (§ Design Patterns) from Core Architecture, with a Python API backed by a C++ backend (see Package System for the dual-package architecture).

Sources: src/fairseq2/data/data\_pipeline.py1-633

## Core Components

### DataPipeline

The `DataPipeline` class is the central component that represents a stateful, iterable data processing pipeline. Key characteristics:

* **Stateful Iteration**: Unlike regular Python iterators, `DataPipeline` maintains internal state and calling `iter()` multiple times creates iterators that share the same state
* **Persistence**: Pipeline state can be saved and restored using `state_dict()` and `load_state_dict()`
* **Error Recovery**: Provides mechanisms to detect and handle broken pipeline states

Sources: src/fairseq2/data/data\_pipeline.py21-194

### DataPipelineBuilder

The `DataPipelineBuilder` class implements the builder pattern for constructing data pipelines. It provides a fluent API where operations can be chained together before creating the final `DataPipeline`.

| Operation Category | Methods | Purpose |
| --- | --- | --- |
| **Transformation** | `map`, `filter`, `yield_from` | Apply functions, filter data, flatten nested pipelines |
| **Batching** | `bucket`, `bucket_by_length`, `collate`, `dynamic_bucket`, `pack` | Combine examples into batches |
| **Data Flow** | `shuffle`, `repeat`, `shard`, `skip`, `take` | Control data ordering and selection |
| **Performance** | `prefetch` | Background data loading |
| **Creation** | `and_return` | Build final `DataPipeline` |

Sources: src/fairseq2/data/data\_pipeline.py196-427

## Data Sources and Readers

The pipeline system supports multiple data sources through dedicated reader functions:

### File-based Data Sources

* **`list_files(path, pattern)`**: Recursively lists files matching a pattern
* **`read_zipped_records(path)`**: Reads files from zip archives
* **`FileMapper`**: Maps filenames to file content with optional byte-level slicing and LRU caching

### Memory-based Data Sources

* **`read_sequence(seq)`**: Reads from Python sequences
* **`read_iterator(iterator, reset_fn, infinite)`**: Reads from iterators with reset capability

Sources: src/fairseq2/data/data\_pipeline.py433-479 src/fairseq2/data/data\_pipeline.py553-587

## Pipeline Operations and Transformations

### Map Operations

The `map` operation applies functions to pipeline elements with support for:

### Data Flow Control

| Operation | Purpose | Key Parameters |
| --- | --- | --- |
| `filter(predicate)` | Keep only examples matching predicate | `predicate`: filtering function |
| `shuffle(shuffle_window)` | Randomize example order | `shuffle_window`: buffer size (0 = full shuffle) |
| `repeat(num_repeats)` | Repeat pipeline examples | `num_repeats`: repetition count (None = infinite) |
| `shard(shard_idx, num_shards)` | Distribute data across workers | `shard_idx`, `num_shards`: sharding parameters |
| `skip(num_examples)` | Skip initial examples | `num_examples`: examples to skip |
| `take(num_examples)` | Limit pipeline length | `num_examples`: maximum examples |

Sources: src/fairseq2/data/data\_pipeline.py275-424

## Batching and Collation

### Bucket Operations

The pipeline provides sophisticated batching strategies:

* **`bucket(bucket_size)`**: Simple fixed-size batching
* **`bucket_by_length(bucket_sizes, selector)`**: Length-based batching for sequences
* **`dynamic_bucket(threshold, cost_fn)`**: Cost-based dynamic batching
* **`pack(num_elements, max_seq_len)`**: Token-level packing for language models

### Collater

The `Collater` class handles tensor concatenation and padding:

The `Collater` supports:

Sources: src/fairseq2/data/data\_pipeline.py481-551 src/fairseq2/data/data\_pipeline.py635-639

## Pipeline Combination and Composition

Multiple pipelines can be combined using static methods:

### Combination Strategies

### Combination Parameters

| Method | Key Parameters | Behavior |
| --- | --- | --- |
| `concat` | `pipelines` | Sequential concatenation |
| `round_robin` | `stop_at_shortest`, `allow_repeats` | Alternating selection |
| `sample` | `weights`, `seed`, `allow_repeats` | Probabilistic sampling |
| `zip` | `names`, `zip_to_shortest`, `flatten` | Parallel combination |

Sources: src/fairseq2/data/data\_pipeline.py76-194

### State Management and Persistence

The pipeline system provides comprehensive state management compatible with checkpoint management:

* **`state_dict(strict=True)`**: Captures pipeline position and internal buffers
* **`load_state_dict(state_dict)`**: Restores exact pipeline state
* **`reset(reset_rng=False)`**: Resets to beginning, optionally resetting RNG state

The `strict` parameter controls whether internal buffers are saved, trading state size for recovery guarantees.

### Error Handling

The system provides specialized exceptions:

* `DataPipelineError`: General pipeline errors
* `ByteStreamError`: File reading failures
* `RecordError`: Corrupt record detection

Sources: src/fairseq2/data/data\_pipeline.py39-74 src/fairseq2/data/data\_pipeline.py428-431 src/fairseq2/data/data\_pipeline.py589-593

## Performance Considerations

### Optimization Features

* **Prefetching**: `prefetch(num_examples)` loads data in background threads
* **Parallel Processing**: `map(fn, num_parallel_calls=N)` distributes computation
* **Memory Mapping**: `FileMapper` with `cached_fd_count` for efficient file access
* **Deterministic Control**: `deterministic=False` in map operations for speed gains

### Utility Functions

The system includes helper functions for common batching scenarios:

* **`create_bucket_sizes()`**: Generates optimal bucket configurations for `bucket_by_length`
Sources: src/fairseq2/data/data\_pipeline.py369-375 src/fairseq2/data/data\_pipeline.py646-717


