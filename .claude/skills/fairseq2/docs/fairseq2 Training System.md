---
source: https://deepwiki.com/facebookresearch/fairseq2
tags:
  - fairseq2
  - documentation
  - reference
  - training
---
# Training System


The Training System in fairseq2 provides a comprehensive framework for training machine learning models with support for distributed training, mixed precision, checkpointing, and metrics tracking. This page explains the core components of the training system, their interactions, and how to configure and extend them. For information about specific model implementations, see fairseq2 Model Architectures. For the recipe execution framework, see fairseq2 Recipes and CLI. For distributed training strategies, see fairseq2 Distributed Training.

## Core Architecture

The training system is built around a set of key components that work together to provide a flexible and powerful training experience. See fairseq2 Core Architecture for how these components integrate with the dependency injection system and Recipes and CLI for recipe orchestration.

**v0.7 Update**: The training system now supports **async evaluation hooks** that enable arbitrary callback functions after checkpointing. This allows launching async SLURM jobs for evaluation/inference, supporting both synchronous and asynchronous validation units. Async evaluation is preferred for heavyweight evaluations (RL-based, human-in-the-loop).

Sources:

### TrainUnit

The `TrainUnit` interface defines how models process batches during training. It's an abstract class that serves as an intermediary between the `Trainer` and the model, allowing for task-specific implementations of the training logic:

The primary responsibilities of a `TrainUnit` include:

Task-specific implementations extend this interface to provide specialized behavior for different model types and training objectives.

Sources:

### Model

The `Model` interface provides a unified abstraction over PyTorch modules, adding functionality specifically needed for training:

In the training system, models can be wrapped with data parallelism wrappers (DDP or FSDP) which provide additional functionality for distributed training.

Sources:

## Training Process

The training process in fairseq2 follows a structured flow from initialization to completion:

Sources:

### Initialization Process

The initialization process for training involves several key steps:

1. Setting up the model
2. Preparing distributed training
3. Creating data readers
4. Setting up optimizer and learning rate scheduler
5. Initializing metrics tracking

Sources:

### Training Loop

The training loop is the core of the training system, handling batch processing, gradient computation, parameter updates, and periodic operations like validation and checkpointing:

Sources:

### Validation Process

The validation process evaluates the model on a separate dataset at configured intervals:

Validation can be used for model selection through keeping the best checkpoints based on validation metrics.

Sources:

## Model Management

The Model Management system in fairseq2 provides interfaces for loading, saving, and manipulating models during training:

The system supports loading models from asset cards, from file paths, or creating empty models for certain initialization workflows.

Sources:

### Model Loading Process

The model loading process involves several steps:

1. Determine the model loading strategy based on configuration
2. Load or create the model config
3. Initialize the model
4. Handle distributed initialization if necessary
5. Apply optional features (activation checkpointing, compilation)
6. Wrap the model with data parallelism if requested

Sources:

## Distributed Training

The Training System supports various forms of distributed training through integration with the Gang system for process group management. See fairseq2 Distributed Training for complete strategy documentation.

**v0.7 Performance Update**: Achieved 20%+ speedup in SeamlessNext training with ongoing optimizations to DDP and communication overhead reduction. Optimized sharding strategies now support models larger than single-device memory.

### Data Parallelism

Data parallelism allows training on multiple devices with each device handling different batches of data (see DDP (§ Data Parallel Training (DDP)) and FSDP (§ Fully Sharded Data Parallelism (FSDP)) for details):

The system supports two main types of data parallelism:

1. **DistributedDataParallel (DDP)**: Standard PyTorch DDP implementation
2. **Fully Sharded Data Parallel (FSDP)**: Memory-efficient version that shards model parameters

Sources:

### Model Parallelism

In addition to data parallelism, the system also supports model parallelism through tensor parallelism for large models (see Tensor Parallelism (§ Tensor Parallelism) and Sharded Layers):

This is particularly important for very large models that don't fit on a single device.

Sources:

## Training Configuration

The Training System uses a comprehensive configuration system that allows customizing all aspects of training:

Sources:

### Common Configuration Settings

Here are some of the most important configuration settings for training:

| Setting | Description | Example |
| --- | --- | --- |
| `trainer.dtype` | Data type for model parameters | `torch.float16` |
| `trainer.data_parallelism` | Data parallelism type | `"ddp"` or `"fsdp"` |
| `trainer.mixed_precision` | Mixed precision training mode | `"static"`, `"dynamic"`, `"off"` |
| `trainer.gradient_accumulation` | Number of steps to accumulate gradients | `2` |
| `trainer.max_gradient_norm` | Maximum gradient norm (clipping threshold) | `1.0` |
| `model.name` | Model name (if loading from asset store) | `"llama3_8b_instruct"` |
| `model.family` | Model family | `"transformer"` |
| `model.arch` | Model architecture | `"base_300m"` |
| `regime.num_steps` | Maximum number of training steps | `100000` |
| `regime.validate_every_n_steps` | Validation interval | `10000` |
| `regime.checkpoint_every_n_steps` | Checkpoint interval | `10000` |

Sources:

## Task-Specific Extensions

The Training System is designed to be extensible, with task-specific implementations built on top of the core components:

Each task implements its own `TrainUnit` with specialized processing logic and customized metrics tracking.

Sources:

### Example: ASR Training

Here's an example of how speech recognition training is implemented:

The ASR TrainUnit includes special logic for freezing and unfreezing the encoder during training, which is a common technique for fine-tuning wav2vec2 models.

Sources:

## Advanced Features

### Mixed Precision Training

The Training System supports various modes of mixed precision training (configured via DataTypeContext (§ Data Type Context Management)):

* **Static mixed precision**: Forward and backward passes in low precision, optimizer steps in full precision
* **Dynamic mixed precision**: Uses PyTorch's automatic mixed precision (amp) for dynamic casting
* **Full precision**: All operations in specified precision dtype

Dynamic loss scaling is used with mixed precision to prevent underflow and overflow.

**v0.7 Update**: FP16 loss scaler implementation is now robust and production-ready.

Sources:

### Activation Checkpointing

Activation checkpointing trades compute for memory by discarding activations during forward pass and recomputing them during backward pass:

This is particularly useful for large models that would otherwise exceed available memory.

Sources:

### Gradient Accumulation

Gradient accumulation allows effective training with larger batch sizes by accumulating gradients over multiple forward/backward passes before applying an optimizer update:

Sources:

### Checkpointing and Recovery

The Training System provides robust checkpointing and recovery mechanisms to resume training from interruptions. See fairseq2 Checkpoint Management for detailed checkpoint handling.

The checkpoint manager handles tracking and rotating checkpoints, including keeping the best checkpoints based on validation metrics.

Sources:


