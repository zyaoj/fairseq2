# ConfigCLI - Reusable Configuration CLI Utility

A reusable CLI utility for handling configuration files and overrides, extracted from the fairseq2 recipe system and integrated with its dependency injection container.

## Features

- **YAML Configuration Loading**: Load configuration from YAML files
- **Command-line Overrides**: Apply configuration overrides via command-line arguments
- **Configuration Dumping**: Export configuration to YAML format
- **Type Safety**: Full support for dataclass configurations with type validation
- **Nested Configuration**: Support for nested configuration structures
- **Flexible Overrides**: Support for dot-notation keys, deletions, and explicit sets
- **Fairseq2 Integration**: Uses fairseq2's dependency injection container for seamless integration

## Quick Start

```python
from dataclasses import dataclass, field
from fairseq2.utils.config_cli import ConfigCLI

@dataclass(kw_only=True)
class MyConfig:
    model: str = "llama"
    lr: float = 0.001
    optimizer: dict = field(default_factory=lambda: {"name": "adamw", "weight_decay": 0.01})

# Create CLI instance (automatically uses fairseq2's DI container)
cli = ConfigCLI(MyConfig)

# Parse command-line arguments
args = cli.parse_args()

# Load configuration
config = cli.load_config(args)

# Dump if requested
if args.dump_config:
    cli.dump_config(config)
```

## Command-line Interface

The `ConfigCLI` adds the following command-line arguments:

- `--config-file CONFIG_FILE`: Path to YAML configuration file
- `--config NAME=VALUE`: Configuration overrides (can be used multiple times)
- `--dump-config`: Dump the final configuration to stdout

### Override Syntax

The `--config` argument supports flexible override syntax:

```bash
# Simple key-value pairs
--config model=llama3_70b
--config lr=0.0001

# Nested keys using dot notation
--config optimizer.name=adafactor
--config optimizer.weight_decay=0.1

# Delete keys
--config del:some_key
--config del:nested.key

# Explicit set (overrides merge behavior)
--config set:optimizer.betas=[0.9,0.95]
```

## Examples

### Basic Usage

```python
from dataclasses import dataclass
from fairseq2.utils.config_cli import ConfigCLI

@dataclass(kw_only=True)
class TrainingConfig:
    model_name: str = "llama3_8b"
    learning_rate: float = 0.001
    batch_size: int = 32
    num_epochs: int = 10

cli = ConfigCLI(TrainingConfig)
args = cli.parse_args()
config = cli.load_config(args)
```

### With YAML File

Create `config.yaml`:
```yaml
model_name: "llama3_70b"
learning_rate: 0.0001
batch_size: 16
num_epochs: 20
```

Run:
```bash
python script.py --config-file config.yaml --dump-config
```

### With Command-line Overrides

```bash
python script.py \
  --config-file config.yaml \
  --config learning_rate=0.0005 \
  --config batch_size=8 \
  --dump-config
```

### Nested Configuration

```python
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class OptimizerConfig:
    name: str = "adamw"
    lr: float = 0.001
    weight_decay: float = 0.01

@dataclass(kw_only=True)
class ModelConfig:
    name: str = "llama"
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)

cli = ConfigCLI(ModelConfig)
```

Override nested values:
```bash
python script.py --config optimizer.lr=0.0005 --config optimizer.weight_decay=0.1
```

## Advanced Usage

### Custom Dependency Resolver

You can provide a custom dependency resolver if needed:

```python
from fairseq2.utils.config_cli import ConfigCLI
from fairseq2.runtime.dependency import DependencyContainer

# Create custom container with your own implementations
custom_container = DependencyContainer()
# ... register custom implementations ...

cli = ConfigCLI(MyConfig, resolver=custom_container)
```

### Programmatic Usage

```python
from collections.abc import Iterator
from typing import Mapping

# Apply overrides programmatically
overrides: Iterator[Mapping[str, object]] = iter([
    {
        "model_name": "custom_model",
        "learning_rate": 0.0005,
        "batch_size": 16,
    }
])

config = cli.load_config(args, config_overrides=overrides)
```

## Error Handling

The `ConfigCLI` provides specific exception types for error handling:

```python
from fairseq2.utils.config_cli import ConfigCLI, ConfigLoadError, ConfigDumpError

try:
    config = cli.load_config(args)
except ConfigLoadError as e:
    print(f"Failed to load configuration: {e}")
except ConfigDumpError as e:
    print(f"Failed to dump configuration: {e}")
```

## Integration with fairseq2

This utility is fully integrated with the fairseq2 ecosystem:

- **Dependency Injection**: Automatically uses fairseq2's global dependency resolver
- **Component Reuse**: Leverages existing `ConfigAction`, `ConfigMerger`, `ValueConverter`, and YAML utilities
- **Consistent Behavior**: Provides the same configuration handling as fairseq2 recipes
- **Type Safety**: Full support for dataclass configurations with validation

The `ConfigCLI` automatically resolves these dependencies from fairseq2's container:
- `FileSystem` → `LocalFileSystem`
- `YamlLoader` → `RuamelYamlLoader` 
- `YamlDumper` → `RuamelYamlDumper`
- `ValueConverter` → `StandardValueConverter`
- `ConfigMerger` → `StandardConfigMerger`

## Testing

Run the test suite to verify functionality:

```bash
python examples/test_config_cli.py
```

Run the example to see it in action:

```bash
python examples/config_cli_example.py --dump-config
python examples/config_cli_example.py --config-file examples/sample_config.yaml --dump-config
```
