# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import sys
from argparse import OPTIONAL, ArgumentParser, Namespace
from collections.abc import Iterator, Mapping
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any, TypeVar, final

from fairseq2.file_system import FileSystem
from fairseq2.runtime.dependency import get_dependency_resolver, DependencyResolver
from fairseq2.utils.argparse import ConfigAction
from fairseq2.utils.config import ConfigMerger
from fairseq2.utils.structured import StructureError, ValueConverter
from fairseq2.utils.yaml import YamlDumper, YamlError, YamlLoader

ConfigT = TypeVar("ConfigT")


@final
class ConfigCLI:
    """
    A reusable CLI utility for handling configuration files and overrides.
    
    This class provides a simple API for:
    - Reading configuration from YAML files
    - Applying command-line config overrides
    - Dumping configuration to YAML format
    - Converting between unstructured dicts and structured dataclasses
    
    Example usage:
        @dataclass(kw_only=True)
        class MyConfig:
            model: str = "llama"
            lr: float = 0.001
            
        cli = ConfigCLI(MyConfig)
        args = cli.parse_args()
        config = cli.load_config(args)
        
        if args.dump_config:
            cli.dump_config(config, sys.stdout)
    """

    def __init__(
        self,
        config_kls: type[ConfigT],
        *,
        resolver: DependencyResolver | None = None,
    ) -> None:
        """
        Initialize the ConfigCLI.
        
        :param config_kls: The dataclass type to use for configuration
        :param resolver: Dependency resolver (uses global resolver if None)
        """
        self.config_kls = config_kls
        
        # Use provided resolver or get the global one
        if resolver is not None:
            self.resolver = resolver
        else:
            self.resolver = get_dependency_resolver()
        
        # Get dependencies from the resolver
        self.file_system = self.resolver.resolve(FileSystem)
        self.yaml_loader = self.resolver.resolve(YamlLoader)
        self.yaml_dumper = self.resolver.resolve(YamlDumper)
        self.value_converter = self.resolver.resolve(ValueConverter)
        self.config_merger = self.resolver.resolve(ConfigMerger)

    def parse_args(self, args: list[str] | None = None) -> Namespace:
        """
        Parse command-line arguments for config handling.
        
        Adds the following arguments:
        - --config-file: Path to YAML configuration file
        - --config: Configuration overrides in key=value format
        - --dump-config: Flag to dump configuration to stdout
        
        :param args: Command line arguments (uses sys.argv if None)
        :return: Parsed arguments namespace
        """
        parser = ArgumentParser()
        
        parser.add_argument(
            "--config-file",
            dest="config_file",
            metavar="CONFIG_FILE",
            type=Path,
            nargs=OPTIONAL,
            help="configuration file",
        )
        
        parser.add_argument(
            "--config",
            dest="config_overrides",
            action=ConfigAction,
            help="command line configuration overrides",
        )
        
        parser.add_argument(
            "--dump-config",
            action="store_true",
            help="dump the configuration in mergeable format to standard output",
        )
        
        return parser.parse_args(args)

    def load_config(
        self,
        args: Namespace,
        *,
        config_file: Path | None = None,
        config_overrides: Iterator[Mapping[str, object]] | None = None,
    ) -> ConfigT:
        """
        Load and structure configuration from file and overrides.
        
        :param args: Parsed arguments namespace
        :param config_file: Override config file from args (uses args.config_file if None)
        :param config_overrides: Override config overrides from args (uses args.config_overrides if None)
        :return: Structured configuration instance
        """
        # Use provided values or fall back to args
        file_path = config_file if config_file is not None else args.config_file
        overrides = config_overrides if config_overrides is not None else args.config_overrides
        
        # Load unstructured config
        unstructured_config = self._load_unstructured_config(file_path, overrides)
        
        # Structure to dataclass
        try:
            return self.value_converter.structure(unstructured_config, self.config_kls)
        except StructureError as ex:
            raise ConfigLoadError(
                f"Configuration cannot be structured into {self.config_kls.__name__}"
            ) from ex

    def dump_config(self, config: ConfigT, stream: TextIO | None = None) -> None:
        """
        Dump configuration to YAML format.
        
        :param config: Configuration instance to dump
        :param stream: Output stream (uses sys.stdout if None)
        """
        if stream is None:
            stream = sys.stdout
            
        try:
            # Convert structured config to unstructured dict
            unstructured_config = self.value_converter.unstructure(config)
        except StructureError as ex:
            raise ConfigDumpError("Configuration cannot be unstructured") from ex
        
        try:
            # Dump to YAML
            self.yaml_dumper.dump(unstructured_config, stream)
        except YamlError as ex:
            raise ConfigDumpError("Failed to dump configuration to YAML") from ex

    def _load_unstructured_config(
        self,
        config_file: Path | None,
        config_overrides: Iterator[Mapping[str, object]] | None,
    ) -> object:
        """Load and merge configuration from file and overrides."""
        # Start with default config instance
        try:
            default_config = self.config_kls()
        except TypeError as ex:
            raise ConfigLoadError(
                f"Default configuration cannot be constructed for {self.config_kls.__name__}"
            ) from ex
        
        # Convert to unstructured dict
        try:
            unstructured_config = self.value_converter.unstructure(default_config)
        except StructureError as ex:
            raise ConfigLoadError(
                f"Default configuration cannot be unstructured for {self.config_kls.__name__}"
            ) from ex
        
        # Load from file if provided
        if config_file is not None:
            unstructured_config = self._load_from_file(config_file, unstructured_config)
        
        # Apply command-line overrides
        if config_overrides is not None:
            for overrides in config_overrides:
                try:
                    unstructured_config = self.config_merger.merge(
                        unstructured_config, overrides
                    )
                except (ValueError, TypeError) as ex:
                    raise ConfigLoadError(
                        "Configuration overrides cannot be applied"
                    ) from ex
        
        return unstructured_config

    def _load_from_file(self, config_file: Path, default_config: object) -> object:
        """Load configuration from YAML file and merge with defaults."""
        try:
            config_file = self.file_system.resolve(config_file)
        except OSError as ex:
            raise ConfigLoadError(f"Cannot resolve config file path: {ex}") from ex
        
        try:
            is_file = self.file_system.is_file(config_file)
        except OSError as ex:
            raise ConfigLoadError(f"Cannot check if config file exists: {ex}") from ex
        
        if not is_file:
            raise ConfigLoadError(f"{config_file} does not point to a configuration file")
        
        try:
            file_configs = self.yaml_loader.load(config_file)
        except YamlError as ex:
            raise ConfigLoadError(f"{config_file} is not a valid YAML file") from ex
        except OSError as ex:
            raise ConfigLoadError(f"Cannot read config file: {ex}") from ex
        
        if len(file_configs) == 0:
            raise ConfigLoadError(f"{config_file} is empty")
        
        try:
            return self.config_merger.merge(default_config, file_configs[0])
        except (ValueError, TypeError) as ex:
            raise ConfigLoadError(
                f"{config_file} cannot be merged with the default configuration"
            ) from ex


class ConfigLoadError(Exception):
    """Raised when configuration cannot be loaded or structured."""
    pass


class ConfigDumpError(Exception):
    """Raised when configuration cannot be dumped."""
    pass
