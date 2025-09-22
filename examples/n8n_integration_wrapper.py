"""
Wrapper module for 20_n8n_integration.py to make it importable in tests.
"""

import importlib.util
import os


# Get the path to the actual n8n integration file
current_dir = os.path.dirname(__file__)
n8n_integration_path = os.path.join(current_dir, "20_n8n_integration.py")

# Import the module dynamically
spec = importlib.util.spec_from_file_location("n8n_integration", n8n_integration_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module from {n8n_integration_path}")
n8n_integration_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n8n_integration_module)

# Export all the important classes and functions
N8nIntegration = n8n_integration_module.N8nIntegration
agent = n8n_integration_module.agent
app = n8n_integration_module.app
n8n_integration = n8n_integration_module.n8n_integration
Conversation = n8n_integration_module.Conversation

# Export other important items that might be needed
__all__ = ["N8nIntegration", "agent", "app", "n8n_integration", "Conversation"]
