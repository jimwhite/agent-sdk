# OpenHands Tools Plugin Architecture Implementation Plan

## Overview

This document outlines the implementation of a plugin architecture for `openhands/tools` that enables selective installation of tools with their specific dependencies. The architecture uses a combination of **Entry Points** and **Namespace Packages** to provide a clean, extensible plugin system.

## Requirements Met

✅ **Selective Installation**: Users can install `openhands-tools[bash]` to get only the bash tool and its dependencies  
✅ **Clean Imports**: `from openhands.tools.bash import BashTool` works without importing browser code  
✅ **Dependency Isolation**: Each tool package includes only its required dependencies  
✅ **Plugin Discovery**: Tools are discoverable through entry points  
✅ **Backward Compatibility**: Existing code can be migrated gradually  

## Architecture Components

### 1. Core Package (`openhands-tools-core`)
- **Location**: `packages/openhands-tools-core/`
- **Purpose**: Provides plugin discovery system and base functionality
- **Dependencies**: `openhands-sdk` only
- **Features**:
  - Entry point discovery system
  - Base tool interfaces
  - Plugin loading utilities

### 2. Individual Tool Packages

#### Bash Tool (`openhands-tools-bash`)
- **Location**: `packages/openhands-tools-bash/`
- **Dependencies**: `bashlex>=0.18`, `libtmux>=0.46.2`
- **Provides**: `openhands.tools.bash.BashTool`

#### Editor Tool (`openhands-tools-editor`)
- **Location**: `packages/openhands-tools-editor/`
- **Dependencies**: `binaryornot>=0.4.4`
- **Provides**: `openhands.tools.editor.FileEditorTool`

#### Tracker Tool (`openhands-tools-tracker`)
- **Location**: `packages/openhands-tools-tracker/`
- **Dependencies**: None (no external dependencies)
- **Provides**: `openhands.tools.tracker.TaskTrackerTool`

#### Browser Tool (`openhands-tools-browser`)
- **Location**: `packages/openhands-tools-browser/`
- **Dependencies**: `browser-use>=0.1.0`
- **Provides**: `openhands.tools.browser.BrowserTool`

### 3. Meta Package (`openhands-tools`)
- **Location**: `packages/openhands-tools/`
- **Purpose**: Provides convenient installation with extras
- **Dependencies**: `openhands-tools-core` (base)
- **Extras**:
  - `[bash]`: Installs bash tool
  - `[editor]`: Installs editor tool
  - `[tracker]`: Installs tracker tool
  - `[browser]`: Installs browser tool
  - `[all]`: Installs all tools

## Technical Implementation

### Namespace Package Structure

Each tool package uses the namespace package pattern:

```python
# openhands/__init__.py
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

# openhands/tools/__init__.py  
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
```

This allows multiple packages to contribute to the same namespace.

### Entry Points Registration

Each tool registers itself via entry points in `pyproject.toml`:

```toml
[project.entry-points."openhands.tools"]
bash = "openhands.tools.bash:BashTool"
editor = "openhands.tools.editor:FileEditorTool"
tracker = "openhands.tools.tracker:TaskTrackerTool"
browser = "openhands.tools.browser:BrowserTool"
```

### Plugin Discovery

The core package provides discovery utilities:

```python
import pkg_resources

def get_available_tools():
    """Get all available tool plugins."""
    return [ep.name for ep in pkg_resources.iter_entry_points('openhands.tools')]

def get_tools():
    """Load all available tool plugins."""
    tools = {}
    for entry_point in pkg_resources.iter_entry_points('openhands.tools'):
        tools[entry_point.name] = entry_point.load()
    return tools
```

## Installation Examples

### Selective Installation
```bash
# Install only bash tool with its dependencies
pip install openhands-tools[bash]
# Result: openhands-tools-core + openhands-tools-bash + bashlex + libtmux

# Install only editor tool with its dependencies
pip install openhands-tools[editor]  
# Result: openhands-tools-core + openhands-tools-editor + binaryornot

# Install only tracker tool (no external dependencies)
pip install openhands-tools[tracker]
# Result: openhands-tools-core + openhands-tools-tracker

# Install all tools
pip install openhands-tools[all]
# Result: All tool packages + all dependencies
```

### Usage Examples
```python
# Import specific tools
from openhands.tools.bash import BashTool
from openhands.tools.editor import FileEditorTool
from openhands.tools.tracker import TaskTrackerTool
from openhands.tools.browser import BrowserTool

# Create tool instances
bash_tool = BashTool.create(working_dir='/path/to/work')
editor_tool = FileEditorTool.create()
tracker_tool = TaskTrackerTool.create()
browser_tool = BrowserTool.create()

# Use tools
tools = [bash_tool, editor_tool, tracker_tool, browser_tool]
```

## Migration Path

### Current State
```python
# Old way (still works)
from openhands.tools import BashTool, FileEditorTool
```

### New Plugin Architecture
```python
# New way (selective imports)
from openhands.tools.bash import BashTool
from openhands.tools.editor import FileEditorTool
```

### Gradual Migration
1. Install new plugin packages alongside existing tools
2. Update imports gradually in client code
3. Remove legacy tools package when migration is complete

## Benefits

### 1. **Dependency Isolation**
- Bash tool users don't need browser dependencies
- Editor tool users don't need bash dependencies
- Smaller installation footprint

### 2. **Plugin Extensibility**
- Easy to add new tools as separate packages
- Third-party tools can integrate seamlessly
- Entry points provide automatic discovery

### 3. **Selective Installation**
- Install only needed functionality
- Reduced dependency conflicts
- Faster installation and smaller environments

### 4. **Clean Architecture**
- Clear separation of concerns
- Namespace packages provide clean imports
- Entry points enable loose coupling

## File Structure

```
agent-sdk/
├── packages/
│   ├── openhands-tools-core/
│   │   ├── openhands/
│   │   │   ├── __init__.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── core/
│   │   │           ├── __init__.py
│   │   │           └── discovery.py
│   │   └── pyproject.toml
│   ├── openhands-tools-bash/
│   │   ├── openhands/
│   │   │   ├── __init__.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── bash/
│   │   │           ├── __init__.py
│   │   │           ├── tool.py
│   │   │           └── executor.py
│   │   └── pyproject.toml
│   ├── openhands-tools-editor/
│   │   ├── openhands/
│   │   │   ├── __init__.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── editor/
│   │   │           ├── __init__.py
│   │   │           ├── tool.py
│   │   │           └── executor.py
│   │   └── pyproject.toml
│   ├── openhands-tools-tracker/
│   │   ├── openhands/
│   │   │   ├── __init__.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── tracker/
│   │   │           ├── __init__.py
│   │   │           ├── tool.py
│   │   │           └── executor.py
│   │   └── pyproject.toml
│   ├── openhands-tools-browser/
│   │   ├── openhands/
│   │   │   ├── __init__.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       └── browser/
│   │   │           ├── __init__.py
│   │   │           ├── tool.py
│   │   │           └── executor.py
│   │   └── pyproject.toml
│   └── openhands-tools/
│       └── pyproject.toml (meta package)
└── pyproject.toml (workspace config)
```

## Testing

The implementation includes comprehensive testing:

- **Plugin Discovery**: Entry points are properly registered and discoverable
- **Dependency Isolation**: Each tool has only its required dependencies
- **Import Structure**: Clean namespace imports work correctly
- **Tool Functionality**: All tools can be instantiated and used

Run the demonstration:
```bash
cd agent-sdk
uv run python demo_plugin_architecture.py
```

## Next Steps

1. **Production Deployment**: Package and publish individual tool packages
2. **Documentation**: Update user documentation with new installation instructions
3. **Migration Guide**: Create detailed migration guide for existing users
4. **CI/CD**: Update build and test pipelines for multi-package structure
5. **Legacy Support**: Maintain backward compatibility during transition period

## Conclusion

The plugin architecture successfully meets all requirements:
- ✅ Selective installation with `openhands-tools[bash]`
- ✅ Clean imports without unwanted dependencies
- ✅ Plugin discovery through entry points
- ✅ Namespace package structure
- ✅ Dependency isolation per tool

The implementation provides a solid foundation for extensible, maintainable tool management in the OpenHands ecosystem.