---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - neural-network
  - features
---
# Feature Extraction and Masking


This document covers the feature extraction and masking components in fairseq2, which are essential building blocks for speech processing models. These components handle the extraction of features from raw input sequences and the application of masking patterns during training.

For information about speech model architectures that use these components, see fairseq2 Speech Models. For other neural network building blocks, see fairseq2 Neural Network Components, fairseq2 Transformer Layers, and fairseq2 Embeddings and Projections. For the theoretical foundations, see fairseq2 Research Foundations. For the broader architecture context, see fairseq2 Core Architecture.

## Feature Extraction Interface

The feature extraction system provides an abstract interface for converting input sequences into latent feature representations. The core abstraction is the `SequenceFeatureExtractor` class, which defines the contract for all feature extraction implementations.

The `SequenceFeatureExtractor` abstract base class defines a standardized interface for feature extraction:

* **Input**: Raw sequences with shape `(N, S, *)` where `N` is batch size, `S` is sequence length, and `*` represents any number of sequence-specific dimensions
* **Output**: Extracted features with shape `(N, S_out, E)` where `S_out` is the output sequence length and `E` is the feature dimensionality

Sources: src/fairseq2/models/feature\_extractor.py18-41

## Masking in Speech Models

Masking is a critical component in self-supervised speech representation learning. It involves strategically hiding portions of the input features during training, forcing the model to learn meaningful representations by predicting the masked content.

The masking system operates on two dimensions:

1. **Temporal Masking**: Masks contiguous spans of time steps
2. **Spatial Masking**: Masks specific feature dimensions across all time steps

Sources: src/fairseq2/models/wav2vec2/masker.py26-46

## Wav2Vec2 Masking Implementation

The `Wav2Vec2Masker` abstract class provides the interface for masking extracted wav2vec 2.0 features, with `StandardWav2Vec2Masker` implementing the specific masking strategy described in the wav2vec 2.0 paper.

### Masking Parameters

The `StandardWav2Vec2Masker` supports configurable masking behavior through several key parameters:

| Parameter | Default | Description |
| --- | --- | --- |
| `temporal_span_len` | 10 | Length of each temporal mask span |
| `max_temporal_mask_prob` | 0.65 | Maximum probability of masking a time step |
| `min_num_temporal_mask_spans` | 2 | Minimum number of temporal spans to mask |
| `spatial_span_len` | 10 | Length of each spatial mask span |
| `max_spatial_mask_prob` | 0.0 | Maximum probability of masking a feature |
| `min_num_spatial_mask_spans` | 2 | Minimum number of spatial spans to mask |

### Masking Process

The masking process involves these steps:

1. **Temporal Mask Generation**: Creates spans of masked time steps using `RowMaskFactory`
2. **Temporal Mask Application**: Replaces masked positions with a learnable embedding (`temporal_mask_embed`)
3. **Spatial Mask Generation**: Optionally creates spans of masked feature dimensions
4. **Spatial Mask Application**: Sets masked feature values to zero

Sources: src/fairseq2/models/wav2vec2/masker.py68-189

## Key Implementation Details

### Mask Embedding

The `StandardWav2Vec2Masker` uses a learnable parameter `temporal_mask_embed` to replace masked time steps. This embedding is initialized using uniform distribution and has the same dimensionality as the model features.

### Masked Element Extraction

The `Wav2Vec2Masker` provides a static utility method `extract_masked_elements` for retrieving only the masked portions of sequences, which is useful for computing contrastive losses during training.

### Row Mask Factory Integration

The masking system integrates with fairseq2's `RowMaskFactory` system, allowing for flexible mask generation strategies. The factory handles:

Sources: src/fairseq2/models/wav2vec2/masker.py121-122 src/fairseq2/models/wav2vec2/masker.py136-143

## Usage in Speech Models

These feature extraction and masking components are primarily used in speech processing models like wav2vec 2.0 and W2V-BERT. The typical usage pattern involves:

1. Extract features from raw audio using a `SequenceFeatureExtractor`
2. Apply masking using a `Wav2Vec2Masker` during training
3. Process masked features through a Transformer encoder
4. Compute contrastive loss between original and predicted features

The masking strategy follows the approach described in the wav2vec 2.0 paper, where both temporal and spatial masking encourage the model to learn robust speech representations through self-supervised learning.

Sources: bibliography.bib165-172 src/fairseq2/models/wav2vec2/masker.py69-70

---

## Related

- fairseq2 Core Architecture
- fairseq2 Neural Network Components
- fairseq2 Speech Models
- fairseq2 Transformer Layers
- fairseq2 Research Foundations
- fairseq2 Model Architectures
- fairseq2 Model Families