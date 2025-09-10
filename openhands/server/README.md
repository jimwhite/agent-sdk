# OpenHands Agent SDK Server

A REST API server for managing OpenHands agent conversations with automatic OpenAPI schema generation.

## Features

- **Single Executable**: FastAPI-based server that can be built into a standalone binary
- **Conversation Management**: Create, manage, and interact with agent conversations
- **Master Key Authentication**: Secure API access with environment-based authentication
- **Automatic OpenAPI Generation**: Dynamic schema generation from SDK classes
- **1-1 Method Mapping**: Direct correspondence between API endpoints and SDK methods

## Installation

### From Source

```bash
# Install the server package
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"

# Or with build dependencies for PyInstaller
pip install -e ".[build]"
```

### Binary Distribution

Download the pre-built binary from releases or build it yourself:

```bash
# Install build dependencies
pip install -e ".[build]"

# Build the binary
pyinstaller openhands-server.spec

# The binary will be in dist/openhands-server
```

## Usage

### Environment Setup

```bash
# Required: Set the master key for API authentication
export OPENHANDS_MASTER_KEY="your-secret-master-key"

# Optional: Enable debug mode
export OPENHANDS_DEBUG=true
```

### Running the Server

#### From Python

```bash
# Using the CLI entry point
openhands-server --host 0.0.0.0 --port 8000

# Using uvicorn directly
uvicorn openhands.server.main:app --host 0.0.0.0 --port 8000
```

#### From Binary

```bash
# Run the standalone binary
./dist/openhands-server --host 0.0.0.0 --port 8000
```

### CLI Options

```
usage: openhands-server [-h] [--host HOST] [--port PORT] [--workers WORKERS]
                       [--reload] [--log-level {critical,error,warning,info,debug,trace}]
                       [--access-log]

OpenHands Agent SDK Server

options:
  -h, --help            show this help message and exit
  --host HOST           Host to bind the server to (default: 127.0.0.1)
  --port PORT           Port to bind the server to (default: 8000)
  --workers WORKERS     Number of worker processes (default: 1)
  --reload              Enable auto-reload for development
  --log-level {critical,error,warning,info,debug,trace}
                        Log level (default: info)
  --access-log          Enable access log

Environment Variables:
  OPENHANDS_MASTER_KEY    Master key for API authentication (required)
  OPENHANDS_DEBUG         Enable debug mode (optional, default: false)
```

## API Documentation

Once the server is running, you can access:

- **Interactive API docs**: `http://localhost:8000/docs`
- **OpenAPI specification**: `http://localhost:8000/openapi.json`
- **Health check**: `http://localhost:8000/alive` (no authentication required)

## API Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/alive` | Health check | None |
| GET | `/conversations` | List all conversations | Required |
| POST | `/conversations` | Create new conversation | Required |
| GET | `/conversations/{id}` | Get conversation details | Required |
| DELETE | `/conversations/{id}` | Delete conversation | Required |
| POST | `/conversations/{id}/messages` | Send message to agent | Required |
| GET | `/conversations/{id}/events` | Get conversation events | Required |
| GET | `/conversations/{id}/stats` | Get conversation statistics | Required |

## Authentication

All endpoints except `/alive` require authentication using the master key:

```bash
curl -H "Authorization: Bearer your-secret-master-key" \
     http://localhost:8000/conversations
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=openhands.server
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
pyright
```

### Building Binary

```bash
# Install build dependencies
pip install -e ".[build]"

# Build binary
pyinstaller openhands-server.spec

# Test the binary
./dist/openhands-server --help
```

## Architecture

The server is structured as follows:

```
openhands/server/
├── cli.py                    # CLI entry point
├── main.py                   # FastAPI application
├── middleware/
│   └── auth.py              # Authentication middleware
├── models/
│   ├── requests.py          # Request models
│   └── responses.py         # Response models
├── routers/
│   └── conversations.py     # API endpoints
├── services/
│   └── conversation_manager.py  # Business logic
└── utils/
    └── openapi_generator.py # OpenAPI schema generation
```

## License

MIT License - see the main repository for details.