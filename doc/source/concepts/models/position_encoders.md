---
myst:
  html_meta:
    "description lang=en": "fairseq2 Position Encoders"
    "keywords": "fairseq2, models, documentation"
---

# Position Encoders


Position encoders are a critical component in fairseq2's neural network architecture, providing sequence models with information about the position of elements in input sequences. Without position encoding, sequence models would be unable to distinguish the order of tokens, as many neural network operations are inherently order-agnostic.

This page documents the various position encoder implementations available in fairseq2, their interfaces, and common usage patterns. For information about how these position encoders are used within specific sequence models, see fairseq2 Model Architectures. For other neural network components, see fairseq2 Neural Network Components, fairseq2 Embeddings and Projections, and fairseq2 Transformer Layers. For the theoretical foundations, see fairseq2 Research Foundations. For the broader architecture context, see fairseq2 Core Architecture.

## Position Encoding Concepts

Sources: tests/unit/nn/test\_position\_encoder.py1-24

Position encoders in fairseq2 inject positional information into token representations. They generally operate by:

1. Taking input sequence embeddings
2. Adding or combining position information based on token positions
3. Returning the position-enhanced embeddings for further processing

Most position encoders in fairseq2 follow a similar interface pattern, taking sequences of token embeddings and optional masks, then applying positional information to those embeddings.

## Position Encoder Types

fairseq2 provides several position encoder implementations to support different model architectures and data types:

Sources: tests/unit/nn/test\_position\_encoder.py13-19

### Sinusoidal Position Encoder

The `SinusoidalPositionEncoder` implements fixed sinusoidal position embeddings as described in the "Attention Is All You Need" paper. This encoder creates fixed position encodings using sine and cosine functions of different frequencies.

Key characteristics:

Usage example:

Sources: tests/unit/nn/test\_position\_encoder.py25-205

### Learned Position Encoder

The `LearnedPositionEncoder` uses learnable parameters for position embeddings instead of fixed functions. This allows the model to learn the optimal position representations during training.

Key characteristics:

Usage example:

Sources: tests/unit/nn/test\_position\_encoder.py207-305

### Rotary Position Encoder

The `RotaryEncoder` implements Rotary Position Embeddings (RoPE) which encode absolute positions through a rotation matrix and naturally incorporates explicit relative position dependency. This is commonly used in models like LLaMA and GPT-NeoX.

Key characteristics:

Usage example:

Sources: tests/unit/nn/test\_position\_encoder.py306-421

### 2D Sinusoidal Position Encoder

The `Sinusoidal2dPositionEncoder` extends position encoding to 2D data like images or feature maps.

Key characteristics:

Usage example:

Sources: tests/unit/nn/test\_position\_encoder.py422-464

### 3D Sinusoidal Position Encoder

The `Sinusoidal3dPositionEncoder` further extends position encoding to 3D data.

Key characteristics:

Usage example:

Sources: tests/unit/nn/test\_position\_encoder.py465-524

## Common Usage Patterns

Sources: tests/unit/nn/test\_position\_encoder.py102-202 tests/unit/nn/test\_position\_encoder.py219-301

### Basic Usage

All position encoders follow a similar usage pattern:

1. Initialize with encoding dimension and sequence length constraints
2. Call the encoder with token embeddings during forward pass
3. Use the position-encoded embeddings in subsequent model layers

### Handling Padding

Position encoders in fairseq2 support padding masks to handle variable-length sequences:

Sources: tests/unit/nn/test\_position\_encoder.py177-200 tests/unit/nn/test\_position\_encoder.py283-303 tests/unit/nn/test\_position\_encoder.py394-403

### Incremental Decoding

Position encoders also support incremental decoding for autoregressive generation:

Sources: tests/unit/nn/test\_position\_encoder.py133-151 tests/unit/nn/test\_position\_encoder.py239-257 tests/unit/nn/test\_position\_encoder.py346-368

## Implementation Details

All position encoders enforce certain constraints:

1. The input sequence length cannot exceed the maximum sequence length
2. For most encoders, the encoding dimension must be even
3. The input tensor shape requirements depend on the specific encoder (1D, 2D, or 3D)

The position encoders are implemented to be efficient for both training and inference, with special optimization for incremental decoding scenarios where appropriate.

Sources: tests/unit/nn/test\_position\_encoder.py107-111 tests/unit/nn/test\_position\_encoder.py153-162 tests/unit/nn/test\_position\_encoder.py307-311 tests/unit/nn/test\_position\_encoder.py423-429 tests/unit/nn/test\_position\_encoder.py467-473

---

## Related

- fairseq2 Core Architecture
- fairseq2 Neural Network Components
- fairseq2 Transformer Layers
- fairseq2 Embeddings and Projections
- fairseq2 Model Architectures
- fairseq2 Research Foundations
- fairseq2 Language Models