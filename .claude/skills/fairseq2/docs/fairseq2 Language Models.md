---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - models
  - llm
---
# Language Models


## Purpose and Scope

This document covers the language model architectures implemented in fairseq2, focusing on the LLaMA family of decoder-only transformer models. It explains the configuration system, architecture variants, and how language models integrate with the broader model family infrastructure.

For information about the abstract model interfaces and base classes, see fairseq2 Model Abstractions. For details on how models are organized and loaded through the family system, see fairseq2 Model Families. For the underlying transformer components, see fairseq2 Transformer Layers. For distributed training, see fairseq2 Distributed Training. For integration with recipes, see fairseq2 Recipes and CLI.

**v0.7 Update**: OLMo2 support added (1B/7B/13B) with custom RMSNorm, post-norm decoder layers, Q/K normalization, and HuggingFace-style RoPE.

## Overview

fairseq2 implements language models as decoder-only transformer architectures. The primary implementation is the LLaMA (Large Language Model Meta AI) family, which supports multiple configuration variants ranging from 1B to 70B parameters. Language models in fairseq2:

**Sources:** src/fairseq2/models/llama/config.py1-273

## LLaMA Architecture

### Configuration System

The LLaMA architecture is defined by the `LLaMAConfig` dataclass, which encapsulates all architectural hyperparameters. This configuration object is used throughout the model lifecycle, from instantiation to checkpoint loading.

**Diagram: LLaMA Configuration System - Core hyperparameters and configuration registry**

The `LLaMAConfig` dataclass defines the following key architectural parameters:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `model_dim` | `int` | 4096 | Model dimensionality (embedding size) |
| `max_seq_len` | `int` | 2048 | Maximum sequence length |
| `vocab_size` | `int` | 32000 | Vocabulary size |
| `num_layers` | `int` | 32 | Number of decoder layers |
| `num_attn_heads` | `int` | 32 | Number of attention heads |
| `num_key_value_heads` | `int` | 32 | Number of key/value heads (Grouped Query Attention) |
| `ffn_inner_dim` | `int` | 16384 | FFN inner projection dimensionality |
| `rope_theta` | `float` | 10000.0 | Rotary position encoder base frequency |
| `use_scaled_rope` | `bool` | False | Whether to use scaled RoPE for longer contexts |
| `shard_embed_dim` | `bool` | True | Whether to shard embedding dimension for tensor parallelism |

**Sources:** src/fairseq2/models/llama/config.py18-102

### Architecture Variants

fairseq2 provides pre-configured architecture variants registered through `register_llama_configs()`. These variants correspond to published LLaMA models across three generations:

**Diagram: LLaMA Architecture Evolution - Model variants across generations**

#### LLaMA 1 (Original)

The original LLaMA models introduced the base architecture with standard multi-head attention:

* **7B:** Base configuration with 4096 model dimension, 32 layers
* **13B:** 5120 dimension, 40 layers and heads
* **33B:** 6656 dimension, 60 layers, 52 heads
* **65B:** 8192 dimension, 80 layers, 64 heads

**Sources:** src/fairseq2/models/llama/config.py127-164

#### LLaMA 2

LLaMA 2 extended the maximum sequence length to 4096 and introduced Grouped Query Attention (GQA) in the 70B variant:

* **llama2\_7b:** Extended context window to 4096 tokens
* **llama2\_13b:** 5120 dimension with 4096 context
* **llama2\_70b:** 8192 dimension with only 8 key/value heads (GQA), custom FFN scaling

The 70B model uses `num_key_value_heads=8` while maintaining 64 query heads, implementing efficient GQA that reduces memory usage during inference.

**Sources:** src/fairseq2/models/llama/config.py166-192

#### LLaMA 3

LLaMA 3 significantly increased vocabulary size and RoPE base frequency:

* **llama3\_8b:** 128,256 vocabulary, 8192 context, 500k RoPE theta, 8 KV heads
* **llama3\_70b:** Same vocabulary and RoPE settings as 8B variant

Both variants disable embedding dimension sharding (`shard_embed_dim=False`) to optimize distributed training.

**Sources:** src/fairseq2/models/llama/config.py194-220

#### LLaMA 3.1

LLaMA 3.1 extended context length to 131,072 tokens using scaled RoPE:

* **llama3\_1\_8b:** Inherits from LLaMA 3 8B with `use_scaled_rope=True`
* **llama3\_1\_70b:** Inherits from LLaMA 3 70B with `use_scaled_rope=True`

The `LLaMARoPEScaleConfig` with default factor of 8.0 enables handling longer sequences by adjusting rotary encoder frequencies.

**Sources:** src/fairseq2/models/llama/config.py222-238

#### LLaMA 3.2

LLaMA 3.2 introduced smaller models (1B and 3B) with aggressive RoPE scaling:

* **llama3\_2\_1b:** 2048 dimension, 16 layers, 32 attention heads, 8 KV heads, 32x RoPE scaling, tied embeddings
* **llama3\_2\_3b:** 3072 dimension, 28 layers, 24 attention heads, 8 KV heads, 32x RoPE scaling, tied embeddings

Both use `tied_embeddings=True` to share weights between input embeddings and output projection, reducing parameter count.

**Sources:** src/fairseq2/models/llama/config.py240-272

### Configuration Inheritance Pattern

Architecture configurations use inheritance to avoid duplication:

**Diagram: Configuration Inheritance - How architecture variants build on each other**

Each configuration function creates a base configuration and modifies specific fields, enabling compact definitions that clearly show the differences between variants.

**Sources:** src/fairseq2/models/llama/config.py124-272

## Integration with Model Family System

Language models integrate with fairseq2's ModelFamily infrastructure, which provides:

1. **Configuration Loading:** Asset cards specify `model_arch` field to select a registered configuration (see Asset Configuration (§ Asset Configuration Loading))
2. **Model Instantiation:** The `ModelFactory` protocol creates model instances from `LLaMAConfig`
3. **Checkpoint Loading:** The `StandardModelFamily` handles state dict loading and distribution
4. **Distributed Support:** Integration with Gangs for tensor parallelism based on `shard_embed_dim` (see Tensor Parallelism (§ Tensor Parallelism))

**Diagram: Model Loading Pipeline - From asset card to instantiated model**

The loading process follows these steps:

1. **Asset Card Lookup:** User requests a model by name (e.g., "llama-3-8b")
2. **Family Resolution:** `model_family` field identifies the `StandardModelFamily` for "llama"
3. **Config Retrieval:** `model_arch` field selects the appropriate `LLaMAConfig` from the registry
4. **Config Override:** Asset card's `model_config` or `model_config_overrides` fields can modify config
5. **Model Creation:** Factory creates model on rank 0, potentially on meta device if `supports_meta=True`
6. **Checkpoint Download:** Downloads checkpoint if URI is remote, with gang synchronization
7. **State Loading:** Loads checkpoint into model, optionally converting state dict format
8. **Broadcasting:** Broadcasts model parameters to all ranks via `broadcast_module()`

**Sources:** src/fairseq2/models/family.py364-401 src/fairseq2/models/family.py445-605

## RoPE Scaling Configuration

Language models support Rotary Position Encoding (RoPE) scaling to extend context length beyond the original training maximum. The `LLaMARoPEScaleConfig` controls frequency scaling:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `factor` | `float` | 8.0 | Ratio of new to original max length |
| `frequency_factors` | `tuple[float, float]` | (1.0, 4.0) | Low and high frequency boundaries |
| `original_context_length` | `int` | 8192 | Original training context length |

When `use_scaled_rope=True`, the rotary encoder adjusts its frequency components to maintain positional information at longer sequence lengths. LLaMA 3.1 and 3.2 models enable this by default.

**Sources:** src/fairseq2/models/llama/config.py104-122

## Configuration Registration

The `register_llama_configs()` function registers all architecture variants with the dependency container:

This registration makes configurations available for lookup during model loading. The `ConfigRegistrar` creates a `Lookup[LLaMAConfig]` that maps architecture names to configuration factories.

**Sources:** src/fairseq2/models/llama/config.py124-273

## Key Design Principles

The LLaMA language model implementation follows several design principles:

1. **Dataclass Configuration:** All architecture parameters are explicit dataclass fields, enabling type checking and validation
2. **Registry Pattern:** Pre-defined architectures registered by name, allowing asset cards to reference them by string identifier
3. **Progressive Enhancement:** Each generation builds on the previous, inheriting base configurations and modifying specific fields
4. **Distributed-First:** Configuration includes tensor parallelism hints (`shard_embed_dim`) and integrates with `Gangs` system
5. **Position Encoding Flexibility:** Supports both standard and scaled RoPE through configuration, enabling context length extension

**Sources:** src/fairseq2/models/llama/config.py1-273


