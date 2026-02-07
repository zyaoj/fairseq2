===============
fairseq2.assets
===============

.. automodule:: fairseq2.assets

.. currentmodule:: fairseq2.assets

The assets module provides a programmatic system for managing models, tokenizers, datasets, and other ML artifacts through an asset card registry.

Overview
========

fairseq2 uses an **asset card system** to manage model checkpoints, configurations, and metadata. Instead of hardcoding file paths or URLs, you reference assets by name through a centralized store.

Key benefits:

- **Reproducibility**: Asset names are stable across environments
- **Versioning**: Multiple versions of the same asset can coexist
- **Automatic downloading**: Assets are fetched and cached automatically
- **Metadata management**: Rich metadata (model type, architecture, etc.) travels with assets

Quick Start
===========

Loading an Asset
----------------

.. testcode::

    from fairseq2.assets import get_asset_store

    # Get the global asset store
    store = get_asset_store()

    # Retrieve an asset card by name
    card = store.retrieve_card("llama3_1_8b")
    
    # Access card metadata
    print(f"Model: {card.name}")
    print(f"Type: {card.model_type}")

.. testoutput::
    :options: +ELLIPSIS

    Model: llama3_1_8b
    Type: ...

Using Assets with Models
-------------------------

Asset cards integrate seamlessly with fairseq2's model loading:

.. testcode::

    from fairseq2.assets import get_asset_store
    from fairseq2.models import load_model

    # Load model directly by asset name
    model = load_model("llama3_1_8b")

The model loader automatically:

1. Retrieves the asset card
2. Downloads checkpoints if needed
3. Loads the model with correct configuration

Core Classes
============

AssetStore
----------

.. autoclass:: AssetStore
    :members:
    :undoc-members:
    :show-inheritance:

The asset store is the central registry for all assets. Get the global instance with :func:`get_asset_store`.

**Key Methods**:

- :meth:`~AssetStore.retrieve_card`: Get an asset card by name
- :meth:`~AssetStore.register_card`: Register a new asset
- :meth:`~AssetStore.list_cards`: List all available assets

StandardAssetStore
------------------

.. autoclass:: StandardAssetStore
    :members:
    :undoc-members:
    :show-inheritance:

The default implementation of :class:`AssetStore`.

AssetCard
---------

.. autoclass:: AssetCard
    :members:
    :undoc-members:
    :show-inheritance:

An asset card contains metadata about a specific asset version.

**Common Fields**:

- ``name``: Unique asset identifier
- ``model_type``: Model architecture (e.g., "llama", "mistral")
- ``checkpoint``: Path or URL to model checkpoint
- ``tokenizer``: Associated tokenizer name
- ``model_config``: Architecture-specific configuration

AssetDownloadManager
--------------------

.. autoclass:: AssetDownloadManager
    :members:
    :undoc-members:
    :show-inheritance:

Handles downloading and caching of asset files.

StandardAssetDownloadManager
----------------------------

.. autoclass:: StandardAssetDownloadManager
    :members:
    :undoc-members:
    :show-inheritance:

AssetMetadataProvider
---------------------

.. autoclass:: AssetMetadataProvider
    :members:
    :undoc-members:
    :show-inheritance:

Provides asset metadata from various sources (local files, remote URLs, etc.).

Advanced Usage
==============

Registering Custom Assets
--------------------------

You can register your own assets programmatically:

.. testcode::

    from fairseq2.assets import AssetCard, get_asset_store

    # Create a custom asset card
    card = AssetCard(
        name="my_custom_llama",
        model_type="llama",
        checkpoint="s3://my-bucket/checkpoints/model.pt",
        tokenizer="llama3_1_tokenizer",
        model_config={
            "model_dim": 4096,
            "num_layers": 32,
            # ... other config
        }
    )

    # Register it with the store
    store = get_asset_store()
    store.register_card(card)

    # Now you can load it by name
    # model = load_model("my_custom_llama")

Listing Available Assets
-------------------------

.. testcode::

    from fairseq2.assets import get_asset_store

    store = get_asset_store()
    
    # List all available asset cards
    cards = store.list_cards()
    
    print(f"Found {len(cards)} assets")
    
    # Filter by model type
    llama_cards = [c for c in cards if c.model_type == "llama"]
    print(f"Found {len(llama_cards)} Llama models")

.. testoutput::
    :options: +ELLIPSIS

    Found ... assets
    Found ... Llama models

Asset Environments
------------------

Assets can have environment-specific configurations (e.g., different checkpoint paths for CPU vs GPU):

.. autoclass:: AssetEnvironmentResolver
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: AssetEnvironmentDetector
    :members:
    :undoc-members:
    :show-inheritance:

Download Management
===================

get_asset_download_manager
--------------------------

.. autofunction:: get_asset_download_manager

LocalAssetDownloadManager
-------------------------

.. autoclass:: LocalAssetDownloadManager
    :members:
    :undoc-members:
    :show-inheritance:

For assets stored on local filesystem.

HuggingFaceHub
--------------

.. autoclass:: HuggingFaceHub
    :members:
    :undoc-members:
    :show-inheritance:

For downloading assets from Hugging Face Hub.

DelegatingAssetDownloadManager
-------------------------------

.. autoclass:: DelegatingAssetDownloadManager
    :members:
    :undoc-members:
    :show-inheritance:

Delegates to multiple download managers based on URL scheme.

Metadata Management
===================

AssetMetadataSource
-------------------

.. autoclass:: AssetMetadataSource
    :members:
    :undoc-members:
    :show-inheritance:

Represents a source of asset metadata (file, URL, etc.).

WellKnownAssetMetadataSource
-----------------------------

.. autoclass:: WellKnownAssetMetadataSource
    :members:
    :undoc-members:
    :show-inheritance:

Built-in metadata sources for fairseq2 models.

CachedAssetMetadataProvider
----------------------------

.. autoclass:: CachedAssetMetadataProvider
    :members:
    :undoc-members:
    :show-inheritance:

Caches metadata to reduce repeated fetches.

Configuration Loading
=====================

AssetConfigLoader
-----------------

.. autoclass:: AssetConfigLoader
    :members:
    :undoc-members:
    :show-inheritance:

StandardAssetConfigLoader
-------------------------

.. autoclass:: StandardAssetConfigLoader
    :members:
    :undoc-members:
    :show-inheritance:

Directory Management
====================

AssetDirectoryAccessor
----------------------

.. autoclass:: AssetDirectoryAccessor
    :members:
    :undoc-members:
    :show-inheritance:

StandardAssetDirectoryAccessor
------------------------------

.. autoclass:: StandardAssetDirectoryAccessor
    :members:
    :undoc-members:
    :show-inheritance:

Utility Functions
=================

canonicalize_asset_name
-----------------------

.. autofunction:: canonicalize_asset_name

sanitize_base_asset_name
-------------------------

.. autofunction:: sanitize_base_asset_name

load_in_memory_asset_metadata
------------------------------

.. autofunction:: load_in_memory_asset_metadata

Exceptions
==========

AssetNotFoundError
------------------

.. autoexception:: AssetNotFoundError
    :members:
    :show-inheritance:

Raised when an asset cannot be found in the store.

AssetCardError
--------------

.. autoexception:: AssetCardError
    :members:
    :show-inheritance:

Base exception for asset card errors.

AssetCardNotValidError
----------------------

.. autoexception:: AssetCardNotValidError
    :members:
    :show-inheritance:

Raised when an asset card fails validation.

AssetDownloadError
------------------

.. autoexception:: AssetDownloadError
    :members:
    :show-inheritance:

Raised when asset download fails.

AssetMetadataError
------------------

.. autoexception:: AssetMetadataError
    :members:
    :show-inheritance:

Raised when asset metadata cannot be loaded or parsed.

AssetSourceNotFoundError
------------------------

.. autoexception:: AssetSourceNotFoundError
    :members:
    :show-inheritance:

Raised when an asset metadata source cannot be found.

See Also
========

- :doc:`../concepts/assets` - High-level concepts
- :doc:`../basics/assets` - Getting started guide
- :doc:`fairseq2.models` - Model loading API
