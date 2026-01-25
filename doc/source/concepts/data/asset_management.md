---
myst:
  html_meta:
    "description lang=en": "fairseq2 Asset Management"
    "keywords": "fairseq2, data, documentation"
---

# Asset Management


The Asset Management system provides discovery, loading, and caching of models, tokenizers, and datasets in fairseq2. It consists of four subsystems: an asset store for retrieval (`StandardAssetStore`), asset cards for metadata (`AssetCard`), metadata providers for different sources, and download managers for URI-based asset acquisition.

The system supports environment-specific configuration (e.g., `model_name@user` vs `model_name@prod`), card inheritance hierarchies, and multiple URI schemes (file://, http://, https://, hg://). All assets are accessed through the dependency injection system via `get_asset_store()`. See Core Architecture (§ Asset Management Overview) for high-level overview and Dependency Injection (§ Dependency Injection System) for container integration.

**v0.7 Update**: Direct HuggingFace model import is now supported with native fairseq2 sharding and tensor parallelism. Models can be loaded directly from HF Hub (e.g., `hg://Qwen/Qwen-Omni-2.5`) without manual checkpoint conversion, with automatic integration into fairseq2's distributed training infrastructure.

## Core Architecture

The asset management system comprises four layers: the `AssetStore` interface for retrieval, `AssetCard` objects for metadata representation, `AssetMetadataProvider` implementations for sourcing metadata, and `AssetDownloadManager` implementations for URI-based downloads.

### System Component Diagram

**Sources:** src/fairseq2/assets/store.py21-208 src/fairseq2/assets/card.py23-128 src/fairseq2/assets/download\_manager.py36-242 src/fairseq2/assets/metadata\_provider.py26-455

## Asset Cards

`AssetCard` objects represent asset metadata with support for inheritance hierarchies. Each card has a name, metadata dictionary, and optional base card. Field resolution walks the inheritance chain from leaf to root.

### AssetCard Structure and Field Resolution

### Field Resolution Algorithm

The `maybe_get_field()` method implements a recursive lookup:

1. Check current card's `_metadata` dictionary
2. If not found, check `_base` card recursively
3. Return `AssetCardField` with the card reference and value
4. Return `None` if field not found in any card

| Method | Description | Raises |
| --- | --- | --- |
| `field(name)` | Returns field, raises `AssetCardError` if not found | `AssetCardError` |
| `maybe_get_field(name)` | Returns field or `None` | - |
| `has_field(name)` | Returns `True` if field exists in card or base cards | - |

### AssetCardField Type System

`AssetCardField` provides type-safe field value access:

| Method | Purpose | Example |
| --- | --- | --- |
| `as_(kls)` | Type-checked cast to `kls` | `field.as_(str)`, `field.as_(int)` |
| `as_uri()` | Convert to `Uri` object, supports relative paths | `field.as_uri()` |

The `as_uri()` method handles:

**Sources:** src/fairseq2/assets/card.py24-83 src/fairseq2/assets/card.py85-128

## Asset Store

`StandardAssetStore` implements `AssetStore` with environment-specific resolution and card inheritance. It aggregates multiple `AssetMetadataProvider` instances and resolves asset names with optional environment qualifiers.

### StandardAssetStore Resolution Flow

### Environment Resolution Rules

`StandardAssetStore.__init__()` establishes environment priority:

```python
_envs = ["user", default_env] if default_env else ["user"]
```

Asset name parsing in `maybe_retrieve_card()`:

| Input | Parsed Name | Environments |
| --- | --- | --- |
| `model_name` | `model_name` | `["user", default_env]` or `["user"]` |
| `model_name@prod` | `model_name` | `["prod"]` |
| `model_name@` | `model_name` | `[]` (no environment lookup) |

The `_do_retrieve_card()` method:

1. Retrieves base metadata with `_maybe_get_metadata(f"{name}@")`
2. Iterates through environments, merging first found environment-specific metadata
3. Recursively loads base card if `base` field exists
4. Returns `AssetCard` with merged metadata

**Sources:** src/fairseq2/assets/store.py48-161 src/fairseq2/assets/store.py87-144

## Metadata Providers

`AssetMetadataProvider` implementations supply asset metadata from various sources. All providers return `dict[str, object]` metadata via `maybe_get_metadata(name)` and expose available asset names via the `asset_names` property.

### Metadata Provider Hierarchy

### Metadata Source Types

| Source Class | Purpose | Typical Use |
| --- | --- | --- |
| `WellKnownAssetMetadataSource` | System and user directories | Default asset cards from `~/.config/fairseq2` and system paths |
| `PackageAssetMetadataSource` | Python package resources | Built-in asset cards from `fairseq2.assets.cards` |
| `FileAssetMetadataSource` | File or directory path | Custom asset cards from user-specified paths |
| `InMemoryAssetMetadataSource` | In-memory metadata list | Programmatically registered assets |

### YAML Asset Card Format

`YamlAssetMetadataFileLoader` parses YAML files with asset entries. Each entry must have a `name` field:

The loader calls `canonicalize_asset_name()` to normalize names (appends `@` if no environment specified) and validates `base` fields with `sanitize_base_asset_name()`. The `__base_path__` field is added to support relative path resolution in `AssetCardField.as_uri()`.

**Sources:** src/fairseq2/assets/metadata\_provider.py26-455 src/fairseq2/assets/metadata\_provider.py291-350 src/fairseq2/assets/metadata\_provider.py352-378

## Download Management

`AssetDownloadManager` implementations handle URI-based asset downloads with scheme-specific logic. `DelegatingAssetDownloadManager` routes requests to appropriate managers based on URI scheme.

### Download Manager Class Hierarchy

### URI Scheme Routing

| Manager Class | Schemes | Implementation |
| --- | --- | --- |
| `StandardAssetDownloadManager` | `http`, `https` | HTTP downloads with caching and extraction |
| `HuggingFaceHub` | `hg` | Hugging Face Hub via `huggingface_hub.snapshot_download()` |
| `LocalAssetDownloadManager` | `file` | Direct path resolution via `Uri.to_path()` |

`DelegatingAssetDownloadManager.__init__()` validates disjoint scheme sets and builds the `_scheme_to_manager` routing table. The `_get_download_manager()` method raises `NotSupportedError` for unknown schemes.

### StandardAssetDownloadManager Download Process

### Cache Directory Structure

`_AssetDownloadOperation` uses SHA1-based cache naming:

```python
cache_dir/
  <sha1_hash[:24]>/           # Asset directory
    <filename>                 # Downloaded file or extracted contents
  <sha1_hash[:24]>.download/   # Temporary download directory
  <sha1_hash[:24]>.download.tmp/  # In-progress download
```

The `_get_uri_hash()` method generates cache directory names:

### Download and Extraction Flow

The `_download_asset()` method in `_AssetDownloadOperation`:

1. Checks if asset already cached (skip if exists)
2. Creates `.download.tmp` directory
3. Downloads via `urlopen()` with progress tracking
4. Extracts filename from `Content-Disposition` header or URL path
5. Renames `.download.tmp` to `.download`

The `_ensure_asset_extracted()` method:

1. Checks for `.download` directory
2. For `.zip` files: extracts via `ZipFile.extractall()`
3. For tar files: extracts via `TarFile.extractall()`
4. For other files: moves directly to asset directory
5. Removes `.download` directory

The `_retrieve_asset_path()` method returns:

### HuggingFaceHub Implementation

`HuggingFaceHub` wraps `huggingface_hub.snapshot_download()` for direct model import:

* `download_model()`: Downloads with `allow_patterns="*.safetensors"`
* `download_tokenizer()`: Downloads with `allow_patterns="tokenizer*.json"`
* `download_dataset()`: Downloads entire dataset repository

The `_get_repo_id()` method strips the `hg://` scheme prefix to obtain the repository identifier (e.g., `hg://meta-llama/Llama-2-7b` → `meta-llama/Llama-2-7b`).

**v0.7 Direct Import**: Models downloaded from HuggingFace Hub integrate seamlessly with fairseq2's sharding system (see Tensor Parallelism (§ Tensor Parallelism)). The checkpoint converter automatically handles HuggingFace format, enabling native fairseq2 sharding and distributed training without manual conversion. Example:

```python
# Direct HF model import with native sharding
model_card = asset_store.retrieve_card("hg://Qwen/Qwen-Omni-2.5")
model = load_model(model_card, gangs=gangs)  # Automatic sharding via gangs.tp
```

**Sources:** src/fairseq2/assets/download\_manager.py40-482 src/fairseq2/assets/download\_manager.py485-786 src/fairseq2/assets/download\_manager.py299-406

## Environment Resolution

`AssetEnvironmentDetector` determines the default environment for asset lookups by iterating through `AssetEnvironmentResolver` callables. The detected environment is passed to `StandardAssetStore` as `default_env`.

### Environment Detection Flow

### Environment Priority Order

`StandardAssetStore.__init__()` establishes the environment search order:

The `user` environment always has highest priority. This allows users to override system or detected environment settings with local asset cards.

### Environment-Specific Asset Resolution

When `maybe_retrieve_card()` is called without an explicit environment (e.g., `model_name` instead of `model_name@prod`), `StandardAssetStore` attempts to merge metadata in this order:

1. Base metadata: `_maybe_get_metadata(f"{name}@")`
2. User environment (if exists): `_maybe_get_metadata(f"{name}@user")`
3. Default environment (if exists and user not found): `_maybe_get_metadata(f"{name}@{default_env}")`

The first found environment metadata is merged with base metadata via `metadata.update(env_metadata)`. This allows environment-specific overrides while maintaining shared base configuration.

**Sources:** src/fairseq2/assets/store.py186-208 src/fairseq2/assets/store.py49-61 src/fairseq2/assets/store.py118-144

## Asset Configuration Loading

`StandardAssetConfigLoader` merges asset card configuration overrides with base configuration objects. This enables asset cards to customize model, tokenizer, or dataset configurations without duplicating entire configuration structures. See Recipes Configuration (§ Hierarchical Configuration) for related config patterns and Model Families for family-based config inheritance.

### Configuration Loading Process

### Configuration Merge Behavior

The `load()` method:

1. Walks the card inheritance chain collecting all `config_key` fields
2. Unstructures the `base_config` to a dictionary representation
3. Iterates through overrides in reverse order (base to leaf), merging each
4. Processes configuration directives (via `ConfigProcessor`)
5. Structures the result back to the original configuration type

This allows asset cards to specify partial configuration overrides. For example, a model card might override only the `num_layers` field while inheriting all other configuration from the base model family configuration.

**Sources:** src/fairseq2/assets/card.py144-213

## Integration and Usage

The asset management system integrates with fairseq2's dependency injection system (§ Dependency Injection System) through the composition layer. It's used throughout recipes and the training system to load models, tokenizers, and datasets:

The system is accessed through the global `get_asset_store()` function, which returns the configured `AssetStore` instance. Common usage patterns include:

**Sources:** src/fairseq2/composition/assets.py84-142 src/fairseq2/assets/store.py21-22

## fairseq2 Extensions

**For detailed extension implementation guide, see `fairseq2-extension.md`.**

The fairseq2 asset system supports extensions that provide environment-specific asset cards without modifying the core library. Extensions are registered via Python entry points and automatically discovered during fairseq2 initialization.

### Extension Mechanism (v0.5+)

Extensions register themselves via `pyproject.toml`:

```toml
[project.entry-points."fairseq2.extension"]
"fairseq2" = "your_package:setup_fairseq2_extension"
```

```{mermaid}
flowchart TB
    subgraph Init["fairseq2 Initialization"]
        START["init_fairseq2()"]
        DISCO["Discover extensions via entry points"]
        CALL["Call setup_fairseq2_extension(container)"]
    end

    subgraph Extension["Extension Registration"]
        SETUP["setup_fairseq2_extension()"]
        REG_LIB["_register_library()"]
        REG_ASSETS["_register_assets()"]
        PKG_ASSETS["register_package_assets()<br/>Scans your_package.cards/**/*.yaml"]
        ENV_RES["Register AssetEnvironmentResolver"]
    end

    subgraph Runtime["Asset Loading"]
        LOAD["load_model('llama3_1_8b')"]
        RESOLVE["AssetEnvironmentResolver → 'awscluster'"]
        LOOKUP["Lookup: llama3_1_8b@awscluster"]
        MERGE["Merge: core card + extension overrides"]
    end

    START --> DISCO
    DISCO --> CALL
    CALL --> SETUP
    SETUP --> REG_LIB
    REG_LIB --> REG_ASSETS
    REG_ASSETS --> PKG_ASSETS
    REG_ASSETS --> ENV_RES

    PKG_ASSETS --> Runtime
    ENV_RES --> RESOLVE
```

fairseq2 calls `setup_fairseq2_extension(container)` during initialization, allowing extensions to register:

1. **Package Assets**: YAML asset cards via `register_package_assets(container, package="your_package.cards")`
2. **Environment Resolvers**: Custom cluster detection via `container.collection.register(AssetEnvironmentResolver, ...)`
3. **Custom Families**: Dataset/model families via `register_dataset_family()`, `register_model_family()`

### Environment-Specific Asset Cards

Extensions provide **cluster-specific overrides** that merge with core asset definitions:

```{mermaid}
flowchart TB
    subgraph Core["fairseq2 Core (fairseq2.assets.cards)"]
        BASE["llama3<br/>model_family: llama<br/>tokenizer_family: llama"]
        ARCH["llama3_1_8b<br/>model_arch: llama3_1_8b<br/>base: llama3"]
        BASE --> ARCH
    end

    subgraph Extension["Extension Package (your_package.cards)"]
        TOKN_AWS["llama3@awscluster<br/>tokenizer: /datasets/..."]
        TOKN_FAIR["llama3@faircluster<br/>tokenizer: /large_experiments/..."]
        CKPT_AWS["llama3_1_8b@awscluster<br/>checkpoint: /fsx-ram/..."]
        CKPT_FAIR["llama3_1_8b@faircluster<br/>checkpoint: /checkpoint/..."]
    end

    subgraph Resolution["Runtime Asset Resolution"]
        REQ["load_model('llama3_1_8b')"]
        ENV["Cluster: awscluster"]
        MERGED["Merged Card:<br/>model_arch + checkpoint path"]
    end

    ARCH -->|"provides architecture"| MERGED
    CKPT_AWS -->|"provides checkpoint"| MERGED
    TOKN_AWS -->|"provides tokenizer"| MERGED
    REQ --> ENV
    ENV --> MERGED
```

**Core Package (fairseq2.assets.cards)**:
- Defines base model families (`llama`, `mistral`)
- Defines architectures (`llama3_1_8b`, `model_arch: llama3_1_8b`)
- Provides default configurations

**Extension Package (your_package.cards)**:
- Provides `checkpoint` paths per cluster (`llama3_1_8b@awscluster`)
- Provides `tokenizer` paths per cluster (`llama3@faircluster`)
- Provides `dataset_config` paths per cluster (`librispeech_960h@rsccluster`)

**Asset Resolution Flow**:

1. User calls `load_model("llama3_1_8b")`
2. `AssetEnvironmentResolver` returns cluster label (e.g., `"awscluster"`)
3. Asset store retrieves base card `llama3_1_8b` from core (defines `model_arch`, `model_family`)
4. Asset store retrieves override card `llama3_1_8b@awscluster` from extension (provides `checkpoint`)
5. Cards are merged: base metadata + environment-specific overrides
6. Model loads using resolved `checkpoint` path

### Environment Resolution with Extensions

`AssetEnvironmentResolver` is a callable that returns the current environment label:

```python
def resolve_cluster_label(resolver: DependencyResolver) -> str:
    """Returns cluster label like 'awscluster', 'faircluster', etc."""
    return get_cluster_label()  # Custom detection logic
```

Extensions register resolvers during setup:

```python
container.collection.register(
    AssetEnvironmentResolver,
    lambda _: resolve_cluster_label
)
```

`AssetEnvironmentDetector` iterates through all registered resolvers and uses the first non-None result as the `default_env` for `StandardAssetStore`.

### Asset Card Naming Convention

**Base cards** (no environment): Define shared configuration
```yaml
name: llama3_1_8b
model_arch: llama3_1_8b
base: llama3
```

**Environment cards**: Provide cluster-specific paths
```yaml
name: llama3_1_8b@awscluster
checkpoint: "/fsx-ram/shared/Meta-Llama-3.1-8B/original/consolidated.00.pth"

---

name: llama3_1_8b@faircluster
checkpoint: "/large_experiments/ram/shared/Meta-Llama-3.1-8B/original/consolidated.00.pth"
```

The `@` suffix is **required** for environment-specific cards. Without it, fairseq2 treats the card as environment-independent.

### Extension Best Practices

1. **Separate concerns**: Core defines model families, extensions provide paths
2. **Use inheritance**: Cluster-specific cards inherit from base cards via `base` field
3. **Provide overrides**: Use minimal overrides (`checkpoint`, `tokenizer`) rather than duplicating entire configs
4. **Environment detection**: Implement automatic cluster detection with environment variable override (`FS2_EXT_CLUSTER_ENV`)
5. **Config defaults**: All config dataclass fields must have defaults (framework calls `config_kls()` with no arguments)

**See `fairseq2-extension.md` for complete implementation guide with working examples.**

---

## Related

- Extending fairseq2 for Asset Management (`fairseq2-extension.md`) - **Primary guide for creating extensions**