# Docker Build System Refactoring - Complete

## Status: ✅ COMPLETE

This document tracks the multi-phase refactoring of the Docker build system. All phases are now complete.

## Executive Summary

The `variant` parameter has been **successfully removed** and replaced with a cleaner `custom_tags` system. The build configuration has been converted to a Pydantic BaseModel with the builder pattern (`.build()` method).

## Implementation Summary

### Phase 1: Remove Variant Parameter ✅
- **Commit**: 22238e07 (pushed to origin/xw/docker-workspace-refactor)
- **Changes**: 
  - Removed `variant` parameter from all build functions
  - Replaced with `custom_tags: list[str] | None` parameter
  - Updated cache tag generation to use base_image slug
  - Modified 6 files, all tests passing (11/11)

### Phase 2: Convert to Pydantic BaseModel ✅
- **Commit**: 265958a7 (local, not pushed)
- **Changes**:
  - Converted `AgentServerBuildConfig` to Pydantic `BaseModel`
  - Used `@computed_field` decorators for derived properties (tags, version, git_info)
  - Maintained backward compatibility with helper functions
  - All tests passing (11/11)

### Phase 3: Builder Pattern & Cleanup ✅
- **Commit**: (current changes, uncommitted)
- **Changes**:
  - Moved build logic into `config.build()` method
  - Removed standalone `build_agent_server_with_config()` function
  - Removed backward-compatible wrapper functions:
    - `generate_agent_server_tags()`
    - `get_agent_server_build_context()`
    - `get_agent_server_dockerfile()`
  - Removed tests for wrapper functions (6 tests removed)
  - Updated all callers to use new pattern:
    ```python
    config = AgentServerBuildConfig(...)
    image = config.build(builder, ...)
    ```
  - Files modified:
    - `openhands/workspace/utils/builder/__init__.py`
    - `openhands/workspace/utils/builder/build_config.py`
    - `openhands/workspace/docker/workspace.py`
    - `openhands/agent_server/docker/build.py`
    - `tests/sdk/workspace/test_build_config.py`
  - All tests passing (5/5)

## Current State Analysis

### 1. Where Variant is Used

#### Build System Files:
- `openhands/workspace/utils/builder/build_config.py` - Build configuration
- `openhands/agent_server/docker/build.py` - Build script
- `openhands/workspace/docker/workspace.py` - Workspace functions
- `.github/workflows/server.yml` - CI/CD workflow
- Test files

#### Usage Pattern:
1. **Cache tags**: `buildcache-{variant}-{branch}` (line 104 in build_config.py)
2. **Build arg**: `--build-arg=VARIANT={variant}` (line 298 in build_config.py)
3. **Metadata**: Passed around for display/logging purposes
4. **CI matrix**: Used to name different build jobs (python, java, golang)

### 2. Critical Finding: Variant is NOT Used in Dockerfile

**The Dockerfile does NOT reference the VARIANT build arg anywhere!**

```dockerfile
# The Dockerfile defines these ARGs:
ARG BASE_IMAGE=nikolaik/python-nodejs:python3.12-nodejs22
ARG USERNAME=openhands
ARG UID=10001
ARG GID=10001
ARG PORT=8000

# But VARIANT is never defined or used!
```

The `--build-arg=VARIANT={variant}` passed during build has no effect.

### 3. Your 3-Layer Hash-Based Tagging System

You already have a robust tagging system in `hash_utils.py`:

```python
tags = {
    "source": f"v{version}_{lock_hash}_{source_hash}{suffix}",     # Most specific
    "lock": f"v{version}_{lock_hash}{suffix}",                      # Medium specific
    "versioned": f"v{version}_{base_slug}{suffix}",                 # Least specific
}
```

**Hash Components:**
- `version`: SDK version
- `lock_hash`: Hash of base_image + pyproject.toml + uv.lock
- `source_hash`: Hash of source code directory (openhands/)
- `base_slug`: Slugified base image name

**Key Insight:** The `base_image` is already included in the lock_hash, so different base images (python-nodejs, eclipse-temurin, golang) automatically produce different tags!

### 4. What Really Differentiates Builds

The actual differentiator between "python", "java", and "golang" variants is the **BASE_IMAGE**, not the variant name:

```yaml
# .github/workflows/server.yml
matrix:
  include:
    - name: python
      base_image: nikolaik/python-nodejs:python3.12-nodejs22
    
    - name: java  
      base_image: eclipse-temurin:17-jdk
    
    - name: golang
      base_image: golang:1.21-bookworm
```

The base_image is already hashed into your tags, making variant redundant.

## Impact Analysis

### What Variant Currently Provides

1. **Cache tag organization**: `buildcache-python-main` vs `buildcache-java-main`
2. **Human-readable labels**: "python variant" vs "java variant"
3. **CI job names**: Matrix job identification

### What Will Still Work Without Variant

1. **Unique tags**: Hash-based tags already differentiate by base_image
2. **Cache reuse**: Can use base_image slug for cache organization
3. **Build matrix**: Can use base_image name or custom labels

## Recommendation: Remove Variant

### Benefits

1. **Simplification**: Remove unnecessary abstraction layer
2. **Clarity**: The base_image is the actual differentiator
3. **Fewer parameters**: Reduce cognitive load and potential confusion
4. **Consistency**: Align parameter names with actual usage

### Migration Strategy

#### Phase 1: Replace Variant in Cache Tags

Change from:
```python
cache_tag_base = f"buildcache-{variant}"
```

To:
```python
cache_tag_base = f"buildcache-{get_base_image_slug(base_image)}"
```

#### Phase 2: Remove Variant Parameter

1. Remove `variant` parameter from:
   - `AgentServerBuildConfig.__init__()`
   - `generate_agent_server_tags()`
   - `generate_cache_tags()`
   - `build_image()` in build.py
   - `build_agent_server_image()` in workspace.py

2. Remove `--build-arg=VARIANT={variant}` from build args

3. Update CI workflow to remove `VARIANT_NAME` env var

4. Update tests to remove variant assertions

#### Phase 3: Optional - Add Descriptive Labels

If you want human-readable labels for CI, use metadata annotations:

```python
config.metadata = {
    "description": "Python + Node.js runtime",
    "base_image": base_image,
}
```

## Alternative: Keep Variant for Cache Organization Only

If you want to keep cache tags human-readable, you could:

1. Make variant optional with auto-detection from base_image
2. Only use it for cache tag naming
3. Remove it from build args and config serialization

Example:
```python
def detect_variant_from_base_image(base_image: str) -> str:
    """Auto-detect variant label from base image."""
    if "python" in base_image or "nodejs" in base_image:
        return "python"
    elif "java" in base_image or "temurin" in base_image:
        return "java"
    elif "golang" in base_image or "go" in base_image:
        return "golang"
    else:
        # Use base image slug as fallback
        return get_base_image_slug(base_image)
```

## Files to Modify

### Core Build System
1. `openhands/workspace/utils/builder/build_config.py`
   - Remove `variant` parameter from functions
   - Update `generate_cache_tags()` to use base_image
   - Remove `variant` from `AgentServerBuildConfig`

2. `openhands/agent_server/docker/build.py`
   - Remove `--variant` CLI argument
   - Remove `VARIANT_NAME` environment variable

3. `openhands/workspace/docker/workspace.py`
   - Remove `variant_name` parameter from `build_agent_server_image()`

### CI/CD
4. `.github/workflows/server.yml`
   - Remove `VARIANT_NAME` from env vars
   - Update build info JSON structure
   - Update PR comment format

### Tests
5. `tests/sdk/workspace/test_build_config.py`
   - Remove variant assertions
   - Update test cases

## Conclusion

The `variant` parameter is vestigial and can be safely removed. Your hash-based tagging system already provides uniqueness through base_image hashing. Removing variant will simplify the build system while maintaining all functional requirements.

**Recommendation**: Proceed with removal in Phase 1 and 2, considering Phase 3 as optional for better observability.
