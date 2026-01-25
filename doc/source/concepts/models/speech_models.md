---
myst:
  html_meta:
    "description lang=en": "fairseq2 Speech Models"
    "keywords": "fairseq2, models, documentation"
---

# Speech Models


This document covers speech processing models implemented in fairseq2, including self-supervised speech representation models (Wav2Vec2, W2VBert) and speech-to-text models (S2T Transformer). These models process raw audio waveforms or log-mel filterbanks to learn speech representations or perform speech-to-text conversion.

For language models and text processing, see fairseq2 Language Models. For core neural network components used across all model types, see fairseq2 Neural Network Components. For sequence-to-sequence interfaces and model architectures, see fairseq2 Model Architectures. For feature extraction details, see fairseq2 Feature Extraction. For the theoretical foundations, see fairseq2 Research Foundations. For the broader architecture context, see fairseq2 Core Architecture.

## Architecture Overview

The speech models in fairseq2 follow a common architectural pattern with specialized frontends for processing audio features, transformer-based encoders for learning representations, and task-specific heads for different objectives.

Sources: src/fairseq2/models/wav2vec2/model.py33-345 src/fairseq2/models/w2vbert/model.py30-187 src/fairseq2/models/seq2seq.py18-115

## Wav2Vec2 Model

The `Wav2Vec2Model` implements the self-supervised speech representation learning approach described in the wav2vec 2.0 paper. It learns representations through contrastive prediction of quantized latent speech representations.

### Core Architecture

The model consists of several key components defined in src/fairseq2/models/wav2vec2/model.py37-101:

* `encoder_frontend`: Wav2Vec2Frontend for feature extraction and processing
* `encoder`: TransformerEncoder for learning contextual representations
* `masker`: Wav2Vec2Masker for temporal masking during training
* `quantizer`: Wav2Vec2VectorQuantizer for discretizing targets
* `final_proj`: Linear projection for encoder outputs
* `final_target_proj`: Linear projection for quantized targets

### Forward Pass and Loss Computation

The model's forward pass in src/fairseq2/models/wav2vec2/model.py102-120 follows these steps:

1. **Feature Extraction**: Extract features using `extract_features()`
2. **Quantization and Contrast**: Generate logits with `quantize_and_contrast()`
3. **Loss Computation**: Compute combined loss with three components

The loss combines contrastive, diversity, and features penalty terms as implemented in src/fairseq2/models/wav2vec2/model.py279-306:

Sources: src/fairseq2/models/wav2vec2/model.py102-120 src/fairseq2/models/wav2vec2/model.py279-334

### Feature Extraction and Processing

The `Wav2Vec2Frontend` handles feature extraction and processing in src/fairseq2/models/wav2vec2/frontend.py31-224:

The feature extraction process involves:

Sources: src/fairseq2/models/wav2vec2/frontend.py142-218

### Vector Quantization

The `Wav2Vec2VectorQuantizer` discretizes continuous features into discrete codes using Gumbel-Softmax sampling, as implemented in src/fairseq2/models/wav2vec2/vector\_quantizer.py61-210:

Sources: src/fairseq2/models/wav2vec2/vector\_quantizer.py129-188

## W2VBert Model

The `W2VBertModel` extends Wav2Vec2 by adding BERT-style masked language modeling over quantized speech representations, as described in src/fairseq2/models/w2vbert/model.py30-187

### Architecture Integration

The key innovation is using a layer hook to capture intermediate encoder representations and apply additional BERT encoder layers for masked prediction, as implemented in src/fairseq2/models/w2vbert/model.py84-98

Sources: src/fairseq2/models/w2vbert/model.py71-128

## S2T Transformer Models

Speech-to-text transformer models implement the `Seq2SeqModel` interface for converting speech to text. The `S2TTransformerFrontend` processes audio features for encoder-decoder architectures.

### S2T Frontend Architecture

The S2T frontend in src/fairseq2/models/s2t\_transformer/frontend.py23-104 provides a simpler pipeline than Wav2Vec2, focusing on preparing features for sequence-to-sequence tasks.

Sources: src/fairseq2/models/s2t\_transformer/frontend.py76-103

### Conv1d Feature Subsampling

The `Conv1dFbankSubsampler` processes log-mel filterbanks using strided convolutions with GLU activations, as implemented in src/fairseq2/models/s2t\_transformer/feature\_extractor.py24-134:

Sources: src/fairseq2/models/s2t\_transformer/feature\_extractor.py90-124

## Common Interfaces

### Seq2SeqModel Base Class

Speech-to-text models implement the `Seq2SeqModel` abstract base class defined in src/fairseq2/models/seq2seq.py18-115 which provides overloaded forward methods for different use cases:

### TransformerFrontend Hierarchy

All speech model frontends inherit from `TransformerFrontend` in src/fairseq2/models/transformer/frontend.py22-50 providing a consistent interface for processing sequences before transformer encoding.

Sources: src/fairseq2/models/transformer/frontend.py22-50 src/fairseq2/models/wav2vec2/frontend.py31 src/fairseq2/models/s2t\_transformer/frontend.py23

## Feature Extractor Components

### Wav2Vec2FeatureExtractor

The `Wav2Vec2FeatureExtractor` processes raw audio waveforms through multiple convolutional layers with configurable normalization, as implemented in src/fairseq2/models/wav2vec2/feature\_extractor.py28-190:

Key features:

### Fbank-based Extractors

For pre-computed features, fairseq2 provides extractors that work with log-mel filterbanks:

* `Wav2Vec2FbankFeatureExtractor`: Simple striding and sampling
* `Conv1dFbankSubsampler`: Convolutional subsampling with GLU activations

Sources: src/fairseq2/models/wav2vec2/feature\_extractor.py288-361 src/fairseq2/models/s2t\_transformer/feature\_extractor.py24-134

---

## Related

- fairseq2 Core Architecture
- fairseq2 Model Architectures
- fairseq2 Neural Network Components
- fairseq2 Feature Extraction
- fairseq2 Transformer Layers
- fairseq2 Research Foundations
- fairseq2 Language Models
- fairseq2 Model Families