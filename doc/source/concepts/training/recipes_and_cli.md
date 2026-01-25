---
myst:
  html_meta:
    "description lang=en": "fairseq2 Recipes And Cli"
    "keywords": "fairseq2, training, documentation"
---

# Recipes and CLI


This page documents fairseq2's recipe execution framework and command-line interface (CLI). Recipes are structured training workflows that orchestrate model loading, data preparation, training loops, and checkpointing. The CLI provides the primary user interface for executing recipes with configuration management and error handling.

**v0.7 Architecture Update**: The recipe system has evolved significantly in v0.7. Recipes are now kept **outside** the core library for better modularity and researcher flexibility. The library supports two distinct usage modes:
- **Library Mode**: `pip install fairseq2` provides stable APIs for model loading, data processing, and training infrastructure
- **Framework Mode**: Clone the repository to access and customize recipes for research projects

For serious research, **copy recipes** from the repository and customize them for your project rather than relying on pip-installed versions. This "copy/paste" workflow enables rapid iteration without forking the core library.

For distributed training strategies and Gang integration, see fairseq2 Distributed Training. For checkpoint management, see fairseq2 Checkpoint Management. For the Asset Management system that recipes use to load models and tokenizers, see fairseq2 Asset Management. For the dependency injection and runtime infrastructure, see fairseq2 Runtime Infrastructure.

## Recipe System Overview

The recipe system provides a structured framework for defining and executing training workflows. Each recipe encapsulates the complete training procedure including model instantiation, data loading, training loop implementation, and checkpoint management. See fairseq2 Training System for trainer and evaluator implementation details.

### Extension Mechanism

**v0.7 Update**: Recipes support an extension mechanism for registering custom components without modifying the core library. Register custom models, optimizers, LR schedulers, and trainer units via setuptools entry points:

```python
# setup.py in your extension package
setup(
    name="my-fairseq2-extension",
    entry_points={
        "fairseq2.extension": [
            "my_extension = my_package:register_extension",
        ]
    }
)

# Extension registration function
def register_extension(container: DependencyContainer) -> None:
    register_component(
        container,
        Optimizer,
        "my_optimizer",
        config_kls=MyOptimizerConfig,
        factory=create_my_optimizer,
    )
```

This enables independent project codebases without forking fairseq2. See Dependency Injection (§ Dependency Injection System) for the underlying container system.

### Recipe Architecture

See Core Architecture (§ CLI and Recipe Execution) for how recipes integrate with the dependency injection system and fairseq2 Training System for trainer implementation.

Sources: High-level architecture diagrams (Diagram 7)

## CLI Framework

The CLI provides the primary interface for executing recipes. Commands follow the pattern `fairseq2 <recipe_name> [options]`, where recipes are registered training workflows.

### CLI Command Structure

Sources: High-level architecture diagrams (Diagram 7)

### Common CLI Arguments

| Argument | Type | Purpose |
| --- | --- | --- |
| `--config-file` | Path | YAML configuration file path |
| `--output-dir` | Path | Directory for checkpoints and logs |
| `--model-name` | String | Model asset identifier (e.g., `llama3_8b`) |
| `--dataset` | String | Dataset asset identifier |
| `--dump-config` | Flag | Print merged configuration and exit |
| Key-value pairs | Various | Override config values (e.g., `train.max_steps=1000`) |

Sources: High-level architecture diagrams (Diagram 7)

## Configuration System

Recipes use structured dataclasses for configuration management (see Core Architecture Design Patterns (§ Design Patterns)). Configuration values can be specified via YAML files, command-line overrides, or programmatic defaults. The configuration system supports hierarchical merging and type validation.

### Configuration Loading Flow

See Runtime Infrastructure (§ Library Initialization and Registration) for how configuration integrates with dependency injection.

Sources: High-level architecture diagrams (Diagram 7)

### Configuration Dataclass Pattern

Recipe configurations are defined as structured dataclasses with type annotations:

The `ConfigRegistrar` class (used with model architectures like `LLaMAConfig`) allows registering predefined configurations with string identifiers through the `@arch()` decorator pattern.

Sources: src/fairseq2/models/llama/config.py12-13 src/fairseq2/models/llama/config.py124-125

## Recipe Execution Flow

Recipe execution proceeds through several phases: initialization, infrastructure setup, asset loading, and the training loop. Each phase is orchestrated by the recipe framework with comprehensive error handling. See fairseq2 Training System for training loop implementation details.

### Complete Execution Flow

Sources: High-level architecture diagrams (Diagram 7)

### Recipe Component Structure

Each recipe typically consists of these components:

| Component | Purpose | Key Responsibilities |
| --- | --- | --- |
| **Recipe Class** | Main orchestrator | Coordinates all phases of training |
| **RecipeConfig** | Configuration container | Holds all training parameters |
| **Trainer Unit** | Training logic | Implements forward/backward pass |
| **Criterion** | Loss computation | Calculates training loss |
| **Optimizer** | Parameter updates | Updates model weights |
| **DataPipeline** | Data loading | Streams and preprocesses data |
| **Checkpoint Manager** | State persistence | Saves/loads training state |

Sources: High-level architecture diagrams (Diagram 7)

## Error Handling Framework

The recipe framework implements comprehensive error handling with specific exception types and exit codes. This enables graceful failure handling and debugging.

### Error Handling Architecture

Sources: High-level architecture diagrams (Diagram 7)

### Exit Code Conventions

The CLI uses specific exit codes to indicate the type of failure:

| Exit Code | Category | Description | Examples |
| --- | --- | --- | --- |
| **0** | Success | Recipe completed successfully | Normal execution |
| **1** | Operational | Resource or operational errors | Asset not found, file I/O errors |
| **2** | Configuration | Invalid configuration | Missing required fields, type errors |
| **3** | Runtime | Training/execution errors | OOM, distributed failures, NaN loss |

Sources: High-level architecture diagrams (Diagram 7)

### Error Handler Registration

The framework supports custom error handlers through the `register_cli_error()` mechanism. This allows recipes to define specific handling logic for different exception types.

Sources: High-level architecture diagrams (Diagram 7)

## Configuration Management Patterns

The configuration system follows several key patterns that provide flexibility and maintainability:

### Hierarchical Configuration

Configurations use inheritance to minimize duplication and ensure consistency across model variants. See fairseq2 Model Families for family-based model configuration patterns and Asset Management (§ Asset Configuration Loading) for how asset cards override configurations.

Sources: src/fairseq2/models/llama/config.py127-273

### Computed Configuration Fields

Some configuration fields are computed based on other parameters to ensure architectural consistency:

| Computed Field | Calculation | Purpose |
| --- | --- | --- |
| `ffn_inner_dim` | `base_dim * scale * multiplier` | FFN dimension calculation |
| `init_std` | `model_dim ** -0.5` (default) | Weight initialization standard deviation |
| RoPE scaling | Based on context length extension | Position encoding adaptation |

Sources: src/fairseq2/models/llama/config.py50-97

This configuration management system provides a foundation for reproducible model training and ensures architectural consistency across the fairseq2 ecosystem while maintaining flexibility for research and experimentation.


