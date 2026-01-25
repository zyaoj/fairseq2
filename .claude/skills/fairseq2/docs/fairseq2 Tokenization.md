---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - data
  - tokenization
---
# Tokenization


## Purpose and Scope

This document covers fairseq2's tokenization system, which provides text-to-token conversion for different model families including NLLB, LLaMA, S2T Transformer, and Mistral models. The tokenization system handles language-specific encoding, special token management, and model-specific formatting requirements.

For data pipeline integration, see fairseq2 Data Pipeline. For tokenizer asset management and loading, see fairseq2 Asset Management. For text processing utilities, see fairseq2 Text Processing. For the broader data management context, see fairseq2 Data Management. For the broader system context, see fairseq2 Core Architecture.

## Core Tokenization Architecture

The tokenization system in fairseq2 follows a modular design with abstract interfaces and model-specific implementations:

### Tokenization System Overview

Sources: src/fairseq2/models/nllb/tokenizer.py16-21 src/fairseq2/models/llama/tokenizer.py15-20 src/fairseq2/models/s2t\_transformer/tokenizer.py16-21

### Core Tokenizer Interface

The `Tokenizer` abstract class defines the standard interface implemented by all model-specific tokenizers:

| Method | Purpose | Parameters |
| --- | --- | --- |
| `create_encoder` | Creates task/language-specific token encoder | `task`, `lang`, `mode`, `device`, `pin_memory` |
| `create_raw_encoder` | Creates encoder without special tokens | `device`, `pin_memory` |
| `create_decoder` | Creates token decoder | `skip_special_tokens` |
| `vocab_info` | Returns vocabulary metadata | Property |

Sources: src/fairseq2/models/nllb/tokenizer.py50-128

## Model-Specific Tokenizers

### NLLB Tokenizer

The `NllbTokenizer` handles multilingual machine translation with language-specific formatting:

**Key Features:**

Sources: src/fairseq2/models/nllb/tokenizer.py34-157 tests/integration/models/test\_nllb.py62-82

### LLaMA Tokenizer

LLaMA models support multiple tokenizer implementations:

**Implementation Options:**

* **SentencePiece (`sp`)**: Basic tokenizer for older LLaMA models
* **Tiktoken (`tiktoken`)**: High-performance tokenizer with custom split regex
* **Hugging Face (`hg`)**: Compatible with Hugging Face ecosystem, includes chat templates

Sources: src/fairseq2/models/llama/tokenizer.py192-291

### S2T Transformer Tokenizer

The `S2TTransformerTokenizer` handles speech-to-text tasks:

**Task-Specific Behavior:**

* **Transcription**: Single language, prefix with `</s>`
* **Translation**: Multilingual with `</s> <lang:code>` prefix

Sources: src/fairseq2/models/s2t\_transformer/tokenizer.py34-150 tests/integration/models/test\_s2t\_transformer.py70-83

### Mistral Tokenizer

The Mistral tokenizer uses a simple SentencePiece implementation:

Sources: src/fairseq2/models/mistral/tokenizer.py18-21

## Tokenizer Backend Systems

### SentencePiece Backend

Used by NLLB, S2T Transformer, Mistral, and LLaMA (SP mode):

Sources: src/fairseq2/models/nllb/tokenizer.py22-28 src/fairseq2/models/s2t\_transformer/tokenizer.py22-28

### Tiktoken Backend

Used by LLaMA models for high-performance tokenization:

**Special Tokens:**

* `<|begin_of_text|>`: Beginning of text marker
* `<|end_of_text|>` / `<|eot_id|>`: End tokens (configurable)
* `<|start_header_id|>` / `<|end_header_id|>`: Chat formatting
Sources: src/fairseq2/models/llama/tokenizer.py229-268

### Hugging Face Backend

Provides compatibility with Hugging Face tokenizers and chat templates:

Sources: src/fairseq2/models/llama/tokenizer.py271-291

## Configuration and Loading

### Tokenizer Configuration Classes

| Model Family | Config Class | Key Parameters |
| --- | --- | --- |
| NLLB | `NllbTokenizerConfig` | `langs`, `default_lang` |
| LLaMA | `LLaMATokenizerConfig` | `impl`, `use_eot`, `split_regex` |
| S2T Transformer | `S2TTransformerTokenizerConfig` | `task`, `target_langs`, `default_target_lang` |
| Mistral | `None` | No configuration required |

### Tokenizer Factory Functions

Sources: src/fairseq2/models/nllb/tokenizer.py143-157 src/fairseq2/models/llama/tokenizer.py199-291 src/fairseq2/models/s2t\_transformer/tokenizer.py143-150 src/fairseq2/models/mistral/tokenizer.py18-21

## Usage Patterns

### Encoder Creation

Different models require specific parameters for encoder creation:

**NLLB Translation:**

**LLaMA Text Generation:**

**S2T Speech Translation:**

Sources: tests/integration/models/test\_nllb.py69-81 tests/integration/models/test\_s2t\_transformer.py77-79

### Special Token Handling

Each tokenizer family implements different special token conventions:

| Tokenizer | BOS Token | EOS Token | Language Tokens | Special Modes |
| --- | --- | --- | --- | --- |
| NLLB | `__lang__` (replaces BOS) | `</s>` | `__lang__` format | Mining, back-translation |
| LLaMA | `<|begin_of_text|>` | `<|end_of_text|>` or `<|eot_id|>` | None | Prompt, response modes |
| S2T | `</s>` | None | `<lang:code>` | Transcription/translation |
| Mistral | Standard SP | Standard SP | None | Basic SP behavior |

Sources: src/fairseq2/models/nllb/tokenizer.py89-106 src/fairseq2/models/llama/tokenizer.py64-80 src/fairseq2/models/s2t\_transformer/tokenizer.py105-116

---

## Related

- fairseq2 Core Architecture
- fairseq2 Data Management
- fairseq2 Data Pipeline
- fairseq2 Text Processing
- fairseq2 Asset Management
- fairseq2 Model Families
- fairseq2 Language Models