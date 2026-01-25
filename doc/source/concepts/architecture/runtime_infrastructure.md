---
myst:
  html_meta:
    "description lang=en": "fairseq2 Runtime Infrastructure"
    "keywords": "fairseq2, architecture, documentation"
---

# Runtime Infrastructure


This page documents fairseq2's runtime infrastructure layer, which provides foundational services for device management, data type control, dependency injection, and thread-local context handling. These systems enable clean separation of concerns and support both single-process development and distributed multi-GPU training with minimal code changes.

For information about distributed processing and communication primitives, see Distributed Processing with Gang. For the package structure and build system, see Package System.

---

## Overview

fairseq2's runtime infrastructure consists of four interconnected systems (see Core Architecture (§ Runtime Infrastructure Overview) for high-level overview):

1. **Dependency Injection** - Provides a type-safe container for managing component lifecycles and dependencies (see Recipes and CLI for usage in recipes)
2. **Device Context Management** - Controls the default device (CPU/CUDA) for tensor operations (used by distributed training)
3. **Data Type Context Management** - Controls the default floating-point dtype for tensor operations (essential for mixed-precision training (§ Mixed Precision))
4. **Thread-Local Storage** - Enables context stacking for nested configuration overrides

These systems work together to provide a clean API surface where components can be configured globally while allowing local overrides in specific code sections.

**Sources:** src/fairseq2/device.py1-303 src/fairseq2/data\_type.py1-229 src/fairseq2/utils/threading.py1-100 src/fairseq2/composition/lib.py115-260

---

## Dependency Injection System

fairseq2 uses a dependency injection (DI) container to manage component instantiation and resolution. The `DependencyContainer` allows registration of types, factories, and singleton instances, while `DependencyResolver` provides type-safe access to registered dependencies.

**Container Registration Pattern**

The `_register_library()` function in src/fairseq2/composition/lib.py115-260 demonstrates the registration pattern:

**Key Registration Patterns:**

| Registration Type | Purpose | Example |
| --- | --- | --- |
| `register_type()` | Map interface to implementation | `CudaContext` → `StandardCudaContext` |
| `register()` | Use factory function for construction | `Device` resolved via `DefaultDeviceDetector.detect()` |
| `register_instance()` | Pre-constructed singleton | `Environment` instance |
| `singleton=True` | Single shared instance per container | Most infrastructure components |
| `collection.register_type()` | Multiple implementations of same interface | `ModuleSharder` implementations |

**Dependency Resolution**

Components access dependencies through `DependencyResolver`:

The resolver automatically instantiates dependencies and their transitive dependencies, injecting them via constructor parameters.

**Sources:** src/fairseq2/composition/lib.py115-260 src/fairseq2/recipe/cli.py95-99

---

## Device Context Management

The `DeviceContext` system controls which PyTorch device (CPU, CUDA, etc.) is used as the default for tensor operations. This allows code to be device-agnostic while still respecting user-specified device placement.

### Architecture

### Key Classes and Functions

**`DeviceContext` Interface** src/fairseq2/device.py106-121

Abstract interface defining device management operations:

* `get_current_device()` - Returns the current contextual device
* Device can be used as a context manager with `with device:` for thread-local override

**`_StandardDeviceContext` Implementation** src/fairseq2/device.py123-139

Uses PyTorch 2.8+ `torch.get_default_device()` when available, falls back to dummy tensor creation on earlier versions. The device itself can be used as a context manager (e.g., `with torch.device("cuda:0"):`).

**`_DefaultDeviceDetector`** src/fairseq2/device.py177-247

Detects the default device using the following precedence:

1. `FAIRSEQ2_DEVICE` environment variable (explicit override)
2. Single device in `CUDA_VISIBLE_DEVICES` (if CUDA available)
3. CUDA device at index `LOCAL_RANK` (for distributed training)
4. Falls back to CPU

**`CudaContext` Interface** src/fairseq2/device.py260-280

Provides abstraction over CUDA runtime:

* `is_available()` - Check if CUDA is available
* `device_count()` - Number of CUDA devices
* `get_device_properties()` - Device capabilities
* `memory_stats()` - Memory usage statistics
* `reset_peak_memory_stats()` - Reset peak memory counters

### Usage Patterns

**Basic Device Control**

**Device Detection for Distributed Training**

The detector automatically maps `LOCAL_RANK` to a CUDA device for multi-GPU setups:

**Error Handling**

The detector raises `LocalRankOutOfRangeError` if `LOCAL_RANK` exceeds available devices src/fairseq2/device.py249-257:

**Sources:** src/fairseq2/device.py1-303 src/fairseq2/composition/lib.py168-174 src/fairseq2/composition/lib.py204-207

---

## Data Type Context Management

The `DataTypeContext` system controls the default floating-point dtype for tensor operations. This is essential for mixed-precision training where different model components may use different dtypes (e.g., bfloat16 for parameters, float32 for loss computation).

### Architecture

### Key Classes and Functions

**`default_dtype()` Context Manager** src/fairseq2/data\_type.py19-27

**v0.7.0 Simplified API**: The data type management in v0.7.0 is simplified to a single context manager that wraps PyTorch's default dtype:

```python
from fairseq2.data_type import default_dtype
import torch

# Set default dtype for tensor operations within context
with default_dtype(torch.bfloat16):
    # All tensors created here use bfloat16
    x = torch.randn(10, 10)  # bfloat16 tensor
```

The context manager temporarily sets `torch.set_default_dtype()` and restores the original dtype on exit.

**`_DataTypeModeStack`** src/fairseq2/data\_type.py130-165

**Note:** In v0.7.0, the data type management was simplified. The complex mode stack system was replaced with a simple context manager (`default_dtype()`) that wraps PyTorch's native dtype functionality. This provides the same functionality with a cleaner API.

**v0.7.0 Migration:**
- `get_current_dtype()` → Use `torch.get_default_dtype()`
- `set_dtype(dtype)` context → Use `default_dtype(dtype)` context manager
- Mode stack operations → Handled automatically by context manager nesting

**`_DataTypeMode`** src/fairseq2/data\_type.py167-187

Extends PyTorch's `TorchFunctionMode` to intercept tensor constructor calls. When enabled, it injects the configured dtype into tensor constructors unless an explicit `dtype` argument is provided.

The mode tracks ~30 tensor constructors src/fairseq2/data\_type.py189-228 including:

### Usage Patterns

**Basic Dtype Control**

**Mixed-Precision Training Pattern**

**Explicit dtype Overrides Mode**

**Sources:** src/fairseq2/data\_type.py1-229 src/fairseq2/composition/lib.py176-182 src/fairseq2/composition/lib.py205 tests/unit/test\_data\_type.py1-32

---

## Thread-Local Storage

The `ThreadLocalStorage` abstraction provides a clean interface for managing thread-local state, which is essential for context stacking in both device and dtype management.

### Architecture

### Key Classes

**`ThreadLocalStorage` Interface** src/fairseq2/utils/threading.py23-26

Abstract interface with a single method:

* `get(key: str, default_factory: Callable[[], T]) -> T` - Retrieves or creates a thread-local value

**`_StandardThreadLocalStorage` Implementation** src/fairseq2/utils/threading.py28-42

Wraps Python's `threading.local()` to provide lazy initialization:

### Usage Pattern

The `_DataTypeModeStack` uses TLS to maintain independent mode stacks per thread src/fairseq2/data\_type.py163-164:

This ensures that:

**Sources:** src/fairseq2/utils/threading.py1-100 src/fairseq2/data\_type.py130-165 src/fairseq2/composition/lib.py227

---

## Library Initialization and Registration

The `_register_library()` function in src/fairseq2/composition/lib.py115-260 wires together all runtime infrastructure components in the dependency injection container. This function is called during recipe initialization src/fairseq2/recipe/cli.py173 to set up the runtime environment via `init_fairseq2()`.

**v0.7 API Update**: The initialization function was renamed from `setup_fairseq2()` to `init_fairseq2()` in v0.7. Always use `init_fairseq2()` in new code:

```python
from fairseq2 import init_fairseq2

# Initialize fairseq2 library (required before using dependency injection)
init_fairseq2()
```

### Registration Flow

### Key Initialization Steps

**1. Environment Setup** src/fairseq2/composition/lib.py118-126

**2. Progress Reporters** src/fairseq2/composition/lib.py128-158

Conditionally registers either a rich progress reporter or a no-op reporter based on:

* `no_progress` parameter
* `FAIRSEQ2_NO_PROGRESS` environment variable
**3. Device Detection** src/fairseq2/composition/lib.py168-174

**4. Data Type Mode Stack** src/fairseq2/composition/lib.py176-182

**5. Thread Pool** src/fairseq2/composition/lib.py184-190

Thread pool size is calculated based on local world size (number of processes on the node):

**6. RNG Bag** src/fairseq2/composition/lib.py192-198

Random number generator initialization for both CPU and default device:

**7. Context Managers** src/fairseq2/composition/lib.py204-210

All singleton context managers are registered:

### Singleton vs Transient

The registration distinguishes between:

| Component | Lifecycle | Rationale |
| --- | --- | --- |
| `Environment` | Singleton instance | Shared environment variables |
| `Device` | Singleton factory | Single default device per process |
| `DeviceContext` | Singleton type | Shared device context state |
| `DataTypeContext` | Singleton type | Shared dtype context state |
| `GangContext` | Singleton type | Shared gang context state |
| `ThreadLocalStorage` | Transient type | Each consumer gets its own instance |
| `_DataTypeModeStack` | Transient factory | Created per DataTypeContext |

**Sources:** src/fairseq2/composition/lib.py115-260 src/fairseq2/recipe/cli.py168-183

---

## Integration with Recipe Execution

The runtime infrastructure is initialized early in the recipe execution flow to ensure all downstream components have access to configured contexts.

**Recipe Access Pattern**

Once the library is registered via `init_fairseq2()`, recipe code can access runtime infrastructure through two mechanisms:

1. **Direct function calls** (standalone functions that internally use `get_dependency_resolver()`):
2. **Dependency injection** (for object-oriented code):

**Error Handling Integration**

The CLI error handlers src/fairseq2/recipe/cli.py509-890 are also registered during initialization, providing user-friendly error messages for infrastructure failures like `LocalRankOutOfRangeError` src/fairseq2/recipe/cli.py719-722

**Sources:** src/fairseq2/recipe/cli.py154-183 src/fairseq2/recipe/cli.py185-219 src/fairseq2/composition/lib.py115-260
