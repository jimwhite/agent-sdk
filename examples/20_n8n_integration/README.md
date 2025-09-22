# n8n Integration Example

This example demonstrates how to integrate OpenHands agents with n8n workflow automation platform.

## Files

- `n8n_integration.py` - Main integration example with N8nIntegration class
- `test_n8n_integration.py` - Comprehensive test suite
- `README.md` - This documentation file

## Features

### 1. Webhook Integration
- OpenHands agent responds to n8n webhook triggers
- Processes incoming webhook data from n8n workflows
- Generates intelligent responses using the OpenHands agent
- Returns structured responses back to n8n

### 2. HTTP Request Integration  
- OpenHands agent makes requests to n8n workflows
- Triggers n8n workflows programmatically
- Retrieves workflow execution status and results
- Handles API authentication and error cases

### 3. Flask Web Server (Optional)
- `/webhook` endpoint for receiving n8n webhook calls
- `/trigger` endpoint for manually triggering workflows  
- `/health` endpoint for service monitoring
- Graceful handling when Flask is not available

## Usage

### Basic Usage
```python
from n8n_integration import N8nIntegration

# Initialize integration
integration = N8nIntegration(
    n8n_url="https://your-n8n-instance.com",
    api_key="your-api-key"
)

# Process webhook data
response = integration.process_webhook_data(webhook_data)

# Trigger workflow
result = integration.trigger_workflow("workflow-id", {"key": "value"})
```

### Flask Server
```python
# Run Flask server for webhook endpoints
integration.run_flask_server(host="0.0.0.0", port=5000)
```

## Running the Example

```bash
# Run the main example
python examples/20_n8n_integration/n8n_integration.py

# Run the tests
pytest examples/20_n8n_integration/test_n8n_integration.py
```

## Setup Instructions

To use this integration:

1. Set up n8n instance (local or cloud)
2. Create a workflow with webhook trigger
3. Set environment variables:
   - `N8N_BASE_URL` (default: http://localhost:5678)
   - `N8N_API_KEY` (for cloud instances)
   - `WEBHOOK_PORT` (default: 8080)
4. Run this script to start the webhook server
5. Configure n8n webhook to point to this server

## Production-Ready Features

- Configurable n8n instance URL and authentication
- Intelligent data processing with OpenHands agent
- Robust error handling and logging
- Optional Flask dependency with import guards
- Comprehensive test coverage