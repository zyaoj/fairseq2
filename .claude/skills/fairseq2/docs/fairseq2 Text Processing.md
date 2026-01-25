---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - data
  - text
---
# Text Processing


## Purpose and Scope

The text processing system in fairseq2 provides utilities for reading text files and converting string data within the data pipeline framework. Located in `fairseq2.data.text`, this module focuses on:

* **String Converters**: `StrSplitter`, `StrToIntConverter`, `StrToTensorConverter` for transforming string data
* **Text File Reading**: `read_text` function for loading text files with line ending normalization
* **Line Ending Handling**: `LineEnding` enum for cross-platform text file processing

These utilities prepare raw text data for downstream processing. For tokenization, see fairseq2 Tokenization. For the data pipeline framework that uses these components, see fairseq2 Data Pipeline. For the broader data management context, see fairseq2 Data Management. For the broader system context, see fairseq2 Core Architecture.

Sources: src/fairseq2/data/text/\_\_init\_\_.py1-14

## Module Organization

The `fairseq2.data.text` module exports five core components organized into two submodules:

**Module Structure Diagram**

Sources: src/fairseq2/data/text/\_\_init\_\_.py7-14

## String Converters

String converters are callable objects used within data pipeline `map()` operations to transform text data. All converters are defined in the `fairseq2.data.text.converters` module.

### StrSplitter

**Class**: `StrSplitter`

Splits strings into sequences of substrings based on a separator. Common use cases:

* **Word Splitting**: Split sentences into words using whitespace
* **Character Splitting**: Split text into individual characters using empty string separator
* **Field Parsing**: Split structured text (CSV-like) by delimiter

The splitter returns a list or sequence of strings that can be further processed by downstream pipeline operations.

**Pipeline Integration**:

```python
DataPipelineBuilder
  .map(StrSplitter(separator=" "))  # Split on spaces
  .map(tokenizer.encode_as_ids)     # Further processing
```

Sources: src/fairseq2/data/text/\_\_init\_\_.py9

### StrToIntConverter

**Class**: `StrToIntConverter`

Parses string representations of integers into Python `int` or NumPy integer types. Use cases:

The converter raises an exception if the string cannot be parsed as a valid integer.

Sources: src/fairseq2/data/text/\_\_init\_\_.py10

### StrToTensorConverter

**Class**: `StrToTensorConverter`

Converts strings into PyTorch `Tensor` objects. The conversion typically:

1. Encodes characters or tokens as integer indices
2. Creates a 1D tensor from the sequence
3. Handles padding/truncation if configured

This converter bridges string data to the tensor format required by neural network models.

Sources: src/fairseq2/data/text/\_\_init\_\_.py11

### Converter Comparison

| Converter | Input | Output | Typical Use |
| --- | --- | --- | --- |
| `StrSplitter` | String | List[str] | Tokenization, field parsing |
| `StrToIntConverter` | String | int | Label parsing, ID conversion |
| `StrToTensorConverter` | String | Tensor | Model input preparation |

## Text File Reading

The `fairseq2.data.text.reader` module provides the `read_text` function for loading text files as data pipeline sources.

### read\_text Function

**Function**: `read_text(path: str | Path, line_ending: LineEnding = LineEnding.INFER, ...) -> DataPipeline`

Reads a text file line-by-line and returns a `DataPipeline` that yields individual lines as strings. The function:

* **Streams Data**: Reads files incrementally without loading entire file into memory
* **Normalizes Line Endings**: Converts platform-specific line endings (CRLF, LF) to a consistent format
* **Handles Encoding**: Supports UTF-8 and other common text encodings
* **Returns Pipeline**: Output is a `DataPipeline` object that can be further transformed

**Usage Pattern**:

```python
pipeline = (
    read_text("data/corpus.txt")
    .map(StrSplitter(separator=" "))
    .map(tokenizer.encode_as_ids)
    .bucket(bucket_size=8192)
)
```

Sources: src/fairseq2/data/text/\_\_init\_\_.py13

### LineEnding Enum

**Enum**: `LineEnding`

Specifies how line endings should be handled when reading text files:

| Value | Description | Use Case |
| --- | --- | --- |
| `INFER` | Auto-detect line ending from file | Default, most common |
| `LF` | Unix/Linux line ending (`\n`) | Force LF normalization |
| `CRLF` | Windows line ending (`\r\n`) | Force CRLF normalization |

The line ending normalization ensures consistent text processing across different platforms and file sources.

**Text Reading Flow Diagram**

Sources: src/fairseq2/data/text/\_\_init\_\_.py12

## Data Pipeline Integration

Text processing components integrate with `DataPipelineBuilder` from the Data Processing Pipeline system. The typical pattern uses `read_text` as a source and converters in `map()` operations.

### Pipeline Composition Pattern

**End-to-End Text Processing Diagram**

### Example Processing Chains

**Basic Text Loading**:

```python
pipeline = read_text("data.txt")
# Pipeline yields: ["line 1", "line 2", "line 3", ...]
```

**Word Tokenization**:

```python
pipeline = (
    read_text("data.txt")
    .map(StrSplitter(separator=" "))
)
# Pipeline yields: [["word1", "word2"], ["word3"], ...]
```

**Label Parsing**:

```python
pipeline = (
    read_text("labels.txt")
    .map(StrToIntConverter())
)
# Pipeline yields: [0, 1, 2, 1, 0, ...]
```

**Multi-File Processing**:

```python
text_pipeline = read_text("corpus.txt").map(tokenizer.encode_as_ids)
label_pipeline = read_text("labels.txt").map(StrToIntConverter())
combined = text_pipeline.zip(label_pipeline)
# Pipeline yields: [(token_ids, label), ...]
```

Sources: src/fairseq2/data/text/\_\_init\_\_.py9-13

### Streaming and Performance

The text processing components support efficient processing of large datasets:

| Feature | Implementation | Benefit |
| --- | --- | --- |
| **Lazy Loading** | `read_text` streams lines incrementally | No full file in memory |
| **Lazy Conversion** | Converters execute only when data is consumed | On-demand processing |
| **C++ Backend** | Pipeline operations run in fairseq2n native code | High throughput |
| **Prefetching** | `.prefetch()` can parallelize I/O and conversion | Better CPU utilization |

The data pipeline's native C++ backend (see fairseq2 Data Pipeline) handles the actual execution of text reading and conversion operations for performance.

Sources: src/fairseq2/data/text/\_\_init\_\_.py1-14

## Usage Patterns

### Basic Text Conversion

The most common usage pattern involves reading text files and applying a series of converters to prepare data for model training or inference.

### Multi-Step Processing

Complex text processing workflows typically combine multiple converters in sequence, with each converter handling a specific aspect of the text transformation process.

### File Format Handling

The text reading system handles various text file formats and encodings, automatically detecting and converting to a standard internal representation for consistent downstream processing.

Sources: src/fairseq2/data/text/\_\_init\_\_.py9-13

---

## Related

- fairseq2 Core Architecture
- fairseq2 Data Management
- fairseq2 Data Pipeline
- fairseq2 Tokenization
- fairseq2 Package System