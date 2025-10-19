#!/usr/bin/env python3
"""
Example usage of the ConfigCLI utility.

This demonstrates how to use the reusable config CLI to:
1. Define a configuration dataclass
2. Parse command-line arguments
3. Load configuration from YAML files
4. Apply command-line overrides
5. Dump configuration to YAML

Run this script with various arguments to see how it works:
    python example_config_cli.py --dump-config
    python example_config_cli.py --config-file config.yaml --dump-config
    python example_config_cli.py --config model=llama3_70b --config lr=0.0001 --dump-config
    python example_config_cli.py --config-file config.yaml --config optimizer.name=adafactor --dump-config
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fairseq2.utils.config_cli import ConfigCLI


@dataclass(kw_only=True)
class OptimizerConfig:
    """Configuration for optimizer settings."""
    name: str = "adamw"
    lr: float = 0.001
    weight_decay: float = 0.01
    betas: tuple[float, float] = (0.9, 0.999)


@dataclass(kw_only=True)
class ModelConfig:
    """Configuration for model settings."""
    name: str = "llama3_8b"
    family: str = "llama"
    compile: bool = True
    dtype: str = "bfloat16"


@dataclass(kw_only=True)
class DatasetConfig:
    """Configuration for dataset settings."""
    name: str = "default_dataset"
    batch_size: int = 32
    max_seq_len: int = 2048
    num_workers: int = 4


@dataclass(kw_only=True)
class TrainingConfig:
    """Main training configuration."""
    model: ModelConfig = field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    
    # Training hyperparameters
    num_steps: int = 10000
    validate_every_n_steps: int = 1000
    checkpoint_every_n_steps: int = 500
    mixed_precision: bool = True
    gradient_accumulation_steps: int = 1
    
    # Logging and monitoring
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    wandb_project: str | None = None
    tensorboard_log_dir: str | None = None


def main() -> None:
    """Main function demonstrating ConfigCLI usage."""
    print("=== ConfigCLI Example ===\n")
    
    # Create CLI instance (now much simpler!)
    cli = ConfigCLI(TrainingConfig)
    
    # Parse command-line arguments
    print("Parsing command-line arguments...")
    args = cli.parse_args()
    
    print(f"Config file: {args.config_file}")
    print(f"Config overrides: {args.config_overrides}")
    print(f"Dump config: {args.dump_config}")
    print()
    
    # Load configuration
    print("Loading configuration...")
    try:
        config = cli.load_config(args)
        print("✓ Configuration loaded successfully")
        print()
        
        # Display loaded configuration
        print("=== Loaded Configuration ===")
        print(f"Model: {config.model.name} ({config.model.family})")
        print(f"Optimizer: {config.optimizer.name} (lr={config.optimizer.lr})")
        print(f"Dataset: {config.dataset.name} (batch_size={config.dataset.batch_size})")
        print(f"Training steps: {config.num_steps}")
        print(f"Mixed precision: {config.mixed_precision}")
        print(f"Log level: {config.log_level}")
        print()
        
        # Dump configuration if requested
        if args.dump_config:
            print("=== Dumped Configuration (YAML) ===")
            cli.dump_config(config)
            print()
        
        # Demonstrate programmatic usage
        print("=== Programmatic Usage Example ===")
        
        # Create a config with overrides programmatically
        from collections.abc import Iterator
        from typing import Mapping
        
        overrides: Iterator[Mapping[str, object]] = iter([
            {
                "model.name": "llama3_70b",
                "optimizer.lr": 0.0001,
                "num_steps": 50000,
                "mixed_precision": True,
            }
        ])
        
        programmatic_config = cli.load_config(
            args, 
            config_overrides=overrides
        )
        
        print("Configuration with programmatic overrides:")
        print(f"Model: {programmatic_config.model.name}")
        print(f"Learning rate: {programmatic_config.optimizer.lr}")
        print(f"Training steps: {programmatic_config.num_steps}")
        print()
        
    except Exception as ex:
        print(f"✗ Error loading configuration: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
