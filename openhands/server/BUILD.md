# Building OpenHands Server Executable

This directory contains the necessary files to build a standalone executable for the OpenHands Server using PyInstaller.

## Files

- `openhands-server.spec` - PyInstaller specification file
- `build.py` - Python build script
- `build.sh` - Shell script wrapper for building
- `BUILD.md` - This documentation file

## Prerequisites

- Python 3.12+
- uv package manager
- OpenHands SDK and Tools packages

## Quick Start

1. **Install PyInstaller** (if not already installed):
   ```bash
   ./build.sh --install-pyinstaller
   ```

2. **Build the executable**:
   ```bash
   ./build.sh
   ```

3. **Run the executable**:
   ```bash
   export OPENHANDS_MASTER_KEY='your-secret-key'
   ./dist/openhands-server --host 0.0.0.0 --port 8000
   ```

## Build Options

### Using the shell script (recommended):
```bash
# Basic build
./build.sh

# Install PyInstaller and build
./build.sh --install-pyinstaller

# Skip cleanup
./build.sh --no-clean

# Skip testing
./build.sh --no-test

# Custom spec file
./build.sh --spec custom-server.spec
```

### Using the Python script directly:
```bash
# Basic build
uv run python build.py

# With options
uv run python build.py --no-clean --no-test
```

### Using PyInstaller directly:
```bash
uv run pyinstaller openhands-server.spec --clean
```

## Environment Variables

The server executable requires the following environment variable:

- `OPENHANDS_MASTER_KEY` - Master key for API authentication (required)

Optional environment variables:
- `OPENHANDS_DEBUG` - Enable debug mode (default: false)

## Output

The build process creates:
- `dist/openhands-server` - The standalone executable
- `build/` - Temporary build files (can be deleted)

## Testing

The build script automatically tests the executable by:
1. Checking that it starts without errors
2. Verifying the `--help` command works correctly

To skip testing, use the `--no-test` flag.

## Troubleshooting

### Common Issues

1. **Missing dependencies**: Make sure all required packages are installed in your environment
2. **Import errors**: Check that the spec file includes all necessary hidden imports
3. **Large executable size**: Consider excluding unnecessary modules in the spec file

### Debug Build

For debugging build issues, you can:
1. Run PyInstaller with verbose output:
   ```bash
   uv run pyinstaller openhands-server.spec --clean --log-level DEBUG
   ```

2. Test the executable manually:
   ```bash
   export OPENHANDS_MASTER_KEY='test-key'
   ./dist/openhands-server --help
   ```

## Customization

To customize the build:

1. **Modify the spec file** (`openhands-server.spec`):
   - Add/remove hidden imports
   - Include additional data files
   - Exclude unnecessary modules

2. **Update build scripts** as needed for your specific requirements

## Distribution

The resulting executable is self-contained and can be distributed without requiring Python or any dependencies to be installed on the target system.

Make sure to include documentation about required environment variables when distributing the executable.