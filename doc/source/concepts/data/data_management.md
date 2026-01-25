---
myst:
  html_meta:
    "description lang=en": "fairseq2 Data Management"
    "keywords": "fairseq2, data, documentation"
---

# Data Management


The Data Management system handles the transformation of raw text data into tensor representations suitable for neural network processing. This encompasses text reading and conversion utilities, tokenization infrastructure, and integration with the DataPipeline system for efficient batch processing.

The system is organized into two main subsystems:

* **Text Processing**: Utilities for reading text files and converting strings to tensors
* **Tokenization**: SentencePiece-based tokenization with asset-based loading

For data transformation pipelines, see fairseq2 Data Pipeline. For asset-based tokenizer and dataset loading, see fairseq2 Asset Management. For the broader system context, see fairseq2 Core Architecture.

## Architecture Overview

**Diagram: Data Management System Components**

Sources: src/fairseq2/data/text/\_\_init\_\_.py1-14 src/fairseq2/data/data\_pipeline.py1-100 src/fairseq2/data/\_\_init\_\_.py1-6

## Data Flow Architecture

The typical data processing flow in fairseq2 follows this pattern:

**Diagram: Text-to-Tensor Data Flow**

This pipeline can be implemented using the DataPipeline system (page 2.4):

| Stage | Component | Operation | Output Type |
| --- | --- | --- | --- |
| 1. Reading | `read_text()` | Read text files line-by-line | `str` |
| 2. Tokenization | `Tokenizer` | Convert strings to token IDs | `list[int]` |
| 3. Conversion | `StrToTensorConverter` | Convert lists to tensors | `Tensor` |
| 4. Batching | `Collater` | Pad and stack tensors | `SequenceData` |

Sources: src/fairseq2/data/text/\_\_init\_\_.py9-13 src/fairseq2/data/data\_pipeline.py509-551

## Text Processing System

The text processing subsystem provides utilities for reading text data and converting strings into numerical representations. These components integrate with the DataPipeline system to enable efficient streaming text processing.

**Diagram: Text Processing Components and Usage**

### Text Reading

The `read_text()` function reads text files line-by-line with configurable line ending handling:

| Parameter | Type | Purpose |
| --- | --- | --- |
| `path` | `Path` | File path to read |
| `line_ending` | `LineEnding` | Line ending mode (INFER, UNIX, WINDOWS, UNIVERSAL) |

The function returns a `DataPipelineBuilder` that yields individual lines as strings.

### String Converters

Three converter classes transform strings into progressively more structured representations:

| Converter | Input | Output | Use Case |
| --- | --- | --- | --- |
| `StrSplitter` | `str` | `list[str]` | Tokenizing text by whitespace or delimiter |
| `StrToIntConverter` | `str` or `list[str]` | `int` or `list[int]` | Converting string token IDs to integers |
| `StrToTensorConverter` | Various | `Tensor` | Converting to PyTorch tensors with specified dtype/device |

These converters are typically chained together using the `DataPipeline.map()` operation.

Sources: src/fairseq2/data/text/\_\_init\_\_.py1-14

For detailed documentation on these components, see page 5.1 (Text Processing).

## Tokenization System

The tokenization subsystem provides infrastructure for loading and using tokenizers, primarily based on SentencePiece. Tokenizers are managed through the asset system (fairseq2 Asset Management), allowing them to be loaded by name with automatic download and caching.

**Diagram: Tokenization Architecture**

### Tokenizer Loading

Tokenizers are loaded through the asset system using the `load_tokenizer()` function:

The loading process:

1. Resolves the tokenizer name through `AssetStore`
2. Retrieves the associated `AssetCard` metadata
3. Determines the appropriate `TokenizerFamily`
4. Downloads model files if not cached
5. Instantiates the tokenizer instance

### SentencePiece Integration

fairseq2 primarily uses SentencePiece for subword tokenization. The SentencePiece tokenizer provides:

* **Vocabulary management**: Access to vocabulary size, special tokens, and token mappings
* **Encoding**: Convert text strings to token ID sequences
* **Decoding**: Convert token ID sequences back to text
* **Special token handling**: Automatic handling of BOS, EOS, PAD, and UNK tokens

### Pipeline Integration

Tokenizers integrate with the DataPipeline system through the `map()` operation:

| Pipeline Stage | Operation | Input | Output |
| --- | --- | --- | --- |
| Text loading | `read_text()` | File path | `str` |
| Tokenization | `map(tokenizer.encode)` | `str` | `list[int]` |
| Tensorization | `map(StrToTensorConverter())` | `list[int]` | `Tensor` |
| Batching | `collate()` | `Tensor` | `SequenceData` |

Sources: Based on Diagram 3 (Asset and Model Loading Pipeline) from high-level architecture

For detailed documentation on tokenizers and their configuration, see fairseq2 Tokenization.

## Batch Construction with Collater

After text processing and tokenization, individual tensors must be combined into batches for efficient training. The `Collater` class handles padding and batching of variable-length sequences.

**Diagram: Collater Operation**

### Collater Configuration

The `Collater` class supports several configuration options:

| Parameter | Type | Purpose | Default |
| --- | --- | --- | --- |
| `pad_value` | `int | None` | Value for padding shorter sequences | `None` |
| `pad_to_multiple` | `int` | Pad batch length to this multiple | `1` |
| `overrides` | `list[CollateOptionsOverride]` | Per-column padding overrides | `None` |

When all sequences have the same length, no padding is applied and `is_ragged` is `False`. When padding is required, the `Collater` returns a `SequenceData` dictionary:

### Column-Specific Overrides

The `CollateOptionsOverride` class allows different padding configurations for different data columns:

Sources: src/fairseq2/data/data\_pipeline.py481-551 src/fairseq2/data/\_\_init\_\_.py1-6

## Utility Functions

The data management system includes several utility functions for common operations.

### Bucket Size Calculation

The `create_bucket_sizes()` function computes optimal bucket configurations for `DataPipeline.bucket_by_length()`:

| Parameter | Type | Purpose |
| --- | --- | --- |
| `max_num_elements` | `int` | Maximum total elements per bucket |
| `max_seq_len` | `int` | Maximum sequence length |
| `min_seq_len` | `int` | Minimum sequence length |
| `num_seqs_multiple_of` | `int` | Bucket size must be multiple of this |

The function returns a list of `(bucket_size, seq_len)` tuples optimized to minimize padding while maintaining efficient batch sizes.

### Example Usage Pattern

Sources: src/fairseq2/data/data\_pipeline.py646-717 src/fairseq2/data/\_\_init\_\_.py1-6

## Integration Patterns

The Data Management system integrates with other fairseq2 components through well-defined interfaces and protocols:

| Integration Point | Component | Interface | Purpose |
| --- | --- | --- | --- |
| Data Pipeline | `DataPipelineReader` | `DataReader` | Feeds data into processing pipelines |
| Asset Management | `DatasetHub` | `DatasetHubAccessor` | Discovers datasets through asset system |
| Training System | `SequenceBatch`, `Seq2SeqBatch` | Batch interfaces | Provides structured data for training |
| Error Handling | All components | Exception hierarchy | Consistent error propagation |

The system design emphasizes modularity and extensibility, allowing new dataset families and readers to be added without modifying existing code. The hub-based discovery mechanism enables dynamic dataset registration and supports both built-in and user-defined datasets.

Sources: src/fairseq2/datasets/\_\_init\_\_.py1-26

---

## Related

- fairseq2 Core Architecture
- fairseq2 Data Pipeline
- fairseq2 Text Processing
- fairseq2 Tokenization
- fairseq2 Asset Management
- fairseq2 Training System