---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - models
  - architecture
---
# Model Architectures


This document provides an overview of the various neural network model architectures implemented in fairseq2. It covers the base abstractions, specific model families, and their architectural components. For information about the core neural network building blocks (attention, embeddings, etc.), see fairseq2 Neural Network Components. For details about training these models, see fairseq2 Training System. For the family-based loading system, see fairseq2 Model Families. For specific implementations, see fairseq2 Language Models and fairseq2 Speech Models.

## Overview

fairseq2 implements several families of neural network architectures for sequence modeling tasks, including speech processing, machine translation, and language modeling. The architectures are organized around a few key base classes and follow consistent patterns for construction and composition.

### Model Architecture Hierarchy

**Sources:** src/fairseq2/models/seq2seq.py18-115 src/fairseq2/models/transformer/model.py src/fairseq2/models/wav2vec2/model.py33-345

## Base Model Abstractions

### Seq2SeqModel

The `Seq2SeqModel` class serves as the abstract base for all sequence-to-sequence architectures that process both source and target sequences.

**Sources:** src/fairseq2/models/seq2seq.py18-115

Key characteristics:

### TransformerModel

The `TransformerModel` class provides the foundation for transformer-based architectures, including both encoder-only and decoder-only models.

**Sources:** src/fairseq2/models/transformer/model.py

## Speech Model Architectures

### Wav2Vec2 Architecture

The Wav2Vec2 model implements self-supervised learning for speech representations through contrastive prediction and vector quantization.

**Sources:** src/fairseq2/models/wav2vec2/model.py33-345 src/fairseq2/models/wav2vec2/frontend.py31-224 src/fairseq2/models/wav2vec2/feature\_extractor.py28-190

The Wav2Vec2 model consists of:

* **Feature Extraction**: Conv1D layers that process raw audio into latent features
* **Masking**: Temporal masking strategy for self-supervised learning
* **Context Network**: Transformer encoder that builds contextualized representations
* **Vector Quantization**: Discretizes target representations for contrastive learning
* **Contrastive Loss**: Distinguishes true targets from distractors

Key classes:

* `Wav2Vec2Model`: Main model implementation
* `Wav2Vec2Features`: Holds extracted features and targets
* `Wav2Vec2Output`: Model predictions and quantized representations
* `Wav2Vec2Loss`: Multi-component loss (contrastive + diversity + features penalty)

### W2VBert Architecture

W2VBert extends Wav2Vec2 with BERT-style masked language modeling for improved speech representations.

**Sources:** src/fairseq2/models/w2vbert/model.py30-187

Key features:

### S2T Transformer Architecture

The Speech-to-Text Transformer implements the encoder-decoder architecture for speech translation and recognition.

**Sources:** src/fairseq2/models/s2t\_transformer/frontend.py23-104 src/fairseq2/models/s2t\_transformer/feature\_extractor.py24-134

Components:

* `Conv1dFbankSubsampler`: Subsamples log-mel filterbank features using 1D convolutions
* `S2TTransformerFrontend`: Processes speech features before transformer encoder
## Language Model Architectures

### LLaMA Architecture

LLaMA implements decoder-only transformer language models with several architectural innovations.

**Sources:** src/fairseq2/models/llama/\_\_init\_\_.py1-39

Key architectural features:

* **RMSNorm**: Root Mean Square Layer Normalization instead of LayerNorm
* **SwiGLU**: Swish-Gated Linear Unit activation in feed-forward networks
* **RoPE**: Rotary Position Encoding for improved position representation
* **Pre-normalization**: Layer normalization applied before attention and FFN blocks

### Mistral Architecture

Mistral models follow a similar decoder-only transformer pattern with some variations from LLaMA.

**Sources:** src/fairseq2/models/mistral/\_\_init\_\_.py1-26

## Transformer Components Architecture

### Frontend Components

Transformer frontends handle input preprocessing and embedding before the main transformer layers.

**Sources:** src/fairseq2/models/transformer/frontend.py22-131 src/fairseq2/models/wav2vec2/frontend.py31-224 src/fairseq2/models/s2t\_transformer/frontend.py23-104

### Core Transformer Architecture

**Sources:** src/fairseq2/models/transformer/\_\_init\_\_.py1-144

## Model Factory Pattern

fairseq2 uses a consistent factory pattern for model construction across all architectures:

| Model Family | Factory Class | Create Function | Configuration |
| --- | --- | --- | --- |
| Wav2Vec2 | `Wav2Vec2Factory` | `create_wav2vec2_model` | `Wav2Vec2Config` |
| W2VBert | `W2VBertFactory` | `create_w2vbert_model` | `W2VBertConfig` |
| LLaMA | `LLaMAFactory` | `create_llama_model` | `LLaMAConfig` |
| Mistral | `MistralFactory` | `create_mistral_model` | `MistralConfig` |
| S2T Transformer | `S2TTransformerFactory` | `create_s2t_transformer_model` | `S2TTransformerConfig` |

**Sources:** src/fairseq2/models/wav2vec2/\_\_init\_\_.py18-24 src/fairseq2/models/llama/\_\_init\_\_.py18-20 src/fairseq2/models/mistral/\_\_init\_\_.py14-16

### Model Registration and Discovery

Models are organized into families and registered through the asset management system:

**Sources:** src/fairseq2/models/wav2vec2/\_\_init\_\_.py10-17 src/fairseq2/models/llama/\_\_init\_\_.py12-17 src/fairseq2/models/mistral/\_\_init\_\_.py9-13

The factory pattern enables:


