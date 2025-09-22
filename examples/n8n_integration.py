"""
n8n Integration Example

This example demonstrates how to integrate OpenHands SDK with n8n workflows.
It shows two main integration patterns:

1. Webhook Integration: OpenHands agent responds to n8n webhook triggers
2. HTTP Request Integration: OpenHands agent makes requests to n8n workflows

Prerequisites:
- n8n instance running (local or cloud)
- n8n workflow with webhook trigger configured
- Environment variables set for API keys and n8n instance URL

Example n8n workflow setup:
1. Create a new workflow in n8n
2. Add a Webhook trigger node
3. Add any processing nodes you need
4. Optionally add a Respond to Webhook node to return data

This example shows how OpenHands can:
- Receive webhook data from n8n workflows
- Process the data using AI capabilities
- Send responses back to n8n
- Trigger n8n workflows programmatically
"""

import json
import os
from typing import Any, Dict, Optional

import requests
from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Conversation,
    get_logger,
)
from openhands.sdk.event.llm_convertible import MessageEvent
from openhands.sdk.llm.message import TextContent
from openhands.sdk.preset.default import get_default_agent


try:
    from flask import Flask, jsonify, request  # type: ignore
except ImportError:
    Flask = None  # type: ignore
    jsonify = None  # type: ignore
    request = None  # type: ignore


logger = get_logger(__name__)

# Configuration
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY")  # Optional, for n8n cloud instances
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))


# Configure LLM (only if not in test mode)
def _get_llm():
    api_key = os.getenv("LITELLM_API_KEY")
    if api_key is None:
        # Allow running without API key for testing
        if os.getenv("PYTEST_CURRENT_TEST"):
            return None
        raise ValueError("LITELLM_API_KEY environment variable is not set.")

    return LLM(
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )


llm = _get_llm()


# Initialize OpenHands agent (only if LLM is available)
def _get_agent():
    if llm is None:
        return None
    cwd = os.getcwd()
    return get_default_agent(
        llm=llm,
        working_dir=cwd,
        cli_mode=True,
    )


agent = _get_agent()

# Flask app for webhook handling (only if Flask is available)
app = Flask(__name__) if Flask is not None else None


class N8nIntegration:
    """
    Integration class for n8n workflows with OpenHands SDK.

    This class provides methods to:
    - Handle incoming webhooks from n8n
    - Trigger n8n workflows programmatically
    - Process data using OpenHands agent capabilities
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}

        if api_key:
            self.headers["X-N8N-API-KEY"] = api_key

    def trigger_workflow(
        self, workflow_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger an n8n workflow programmatically.

        Args:
            workflow_id: The ID of the n8n workflow to trigger
            data: Optional data to send to the workflow

        Returns:
            Response from the n8n API
        """
        url = f"{self.base_url}/api/v1/workflows/{workflow_id}/execute"

        payload = {}
        if data:
            payload["data"] = data

        try:
            response = requests.post(
                url, json=payload, headers=self.headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to trigger n8n workflow {workflow_id}: {e}")
            raise

    def get_workflow_executions(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get execution history for a specific workflow.

        Args:
            workflow_id: The ID of the n8n workflow

        Returns:
            Execution history from the n8n API
        """
        url = f"{self.base_url}/api/v1/executions"
        params = {"workflowId": workflow_id}

        try:
            response = requests.get(
                url, params=params, headers=self.headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get executions for workflow {workflow_id}: {e}")
            raise

    def process_webhook_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook data using OpenHands agent.

        Args:
            webhook_data: Data received from n8n webhook

        Returns:
            Processed response from OpenHands agent
        """
        try:
            # Check if agent is available
            if agent is None:
                return {
                    "success": False,
                    "error": "OpenHands agent not available (LLM not configured)",
                    "response": None,
                }

            # Extract relevant information from webhook data
            task_description = webhook_data.get(
                "task", "Process the provided data and provide insights"
            )
            input_data = webhook_data.get("data", webhook_data)

            # Create a conversation with the agent
            conversation = Conversation(agent=agent)

            # Prepare the message for the agent
            message = (
                f"I received data from an n8n workflow. "
                f"Task: {task_description}\n\n"
                f"Data to process:\n{json.dumps(input_data, indent=2)}\n\n"
                f"Please analyze this data and provide insights or perform "
                f"the requested task."
            )

            # Send message and get response
            conversation.send_message(message)
            conversation.run()

            # Get the last response from the conversation events
            events = list(conversation.state.events)
            response_content = "No response generated"

            # Look for the last MessageEvent with assistant content
            for event in reversed(events):
                if isinstance(event, MessageEvent) and event.llm_message is not None:
                    message = event.llm_message
                    if hasattr(message, "role") and message.role == "assistant":
                        # Extract text content from the message
                        if hasattr(message, "content") and message.content:
                            content_parts = message.content
                            response_content = ""
                            for part in content_parts:
                                if isinstance(part, TextContent):
                                    response_content += part.text
                        break

            return {
                "success": True,
                "response": response_content,
                "processed_data": input_data,
                "task": task_description,
            }

        except Exception as e:
            logger.error(f"Error processing webhook data: {e}")
            return {"success": False, "error": str(e), "processed_data": webhook_data}


# Initialize n8n integration
n8n_integration = N8nIntegration(N8N_BASE_URL, N8N_API_KEY)


if app is not None:

    @app.route("/webhook/n8n", methods=["POST"])
    def handle_n8n_webhook():
        """
        Handle incoming webhooks from n8n workflows.

        This endpoint receives data from n8n, processes it using OpenHands agent,
        and returns the results back to n8n.
        """
        try:
            # Get webhook data
            webhook_data = request.get_json() or {}  # type: ignore

            logger.info(
                f"Received n8n webhook data: {json.dumps(webhook_data, indent=2)}"
            )

            # Process the data using OpenHands agent
            result = n8n_integration.process_webhook_data(webhook_data)

            logger.info(f"Processed webhook data: {json.dumps(result, indent=2)}")

            return jsonify(result), 200  # type: ignore

        except Exception as e:
            logger.error(f"Error handling n8n webhook: {e}")
            return jsonify({"success": False, "error": str(e)}), 500  # type: ignore

    @app.route("/trigger/<workflow_id>", methods=["POST"])
    def trigger_n8n_workflow(workflow_id: str):
        """
        Trigger an n8n workflow from OpenHands.

        This endpoint allows triggering n8n workflows programmatically,
        optionally with data processed by OpenHands agent.
        """
        try:
            # Get request data
            request_data = request.get_json() or {}  # type: ignore

            # Optionally process the data with OpenHands first
            if request_data.get("process_with_openhands", False):
                processed_result = n8n_integration.process_webhook_data(request_data)
                trigger_data = processed_result
            else:
                trigger_data = request_data

            # Trigger the n8n workflow
            result = n8n_integration.trigger_workflow(workflow_id, trigger_data)

            logger.info(
                f"Triggered n8n workflow {workflow_id}: {json.dumps(result, indent=2)}"
            )

            return jsonify(
                {"success": True, "workflow_id": workflow_id, "result": result}
            ), 200  # type: ignore

        except Exception as e:
            logger.error(f"Error triggering n8n workflow {workflow_id}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500  # type: ignore

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify(
            {
                "status": "healthy",
                "n8n_base_url": N8N_BASE_URL,
                "webhook_port": WEBHOOK_PORT,
            }
        ), 200  # type: ignore


def run_webhook_server():
    """
    Run the webhook server to handle n8n integrations.

    This server provides endpoints for:
    - Receiving webhooks from n8n workflows
    - Triggering n8n workflows programmatically
    - Health checks
    """
    if app is None:
        raise ImportError(
            "Flask is required for webhook server. Install with: pip install flask"
        )

    logger.info(f"Starting n8n integration webhook server on port {WEBHOOK_PORT}")
    logger.info(f"n8n base URL: {N8N_BASE_URL}")
    logger.info("Available endpoints:")
    logger.info("  POST /webhook/n8n - Handle incoming n8n webhooks")
    logger.info("  POST /trigger/<workflow_id> - Trigger n8n workflows")
    logger.info("  GET /health - Health check")

    app.run(host="0.0.0.0", port=WEBHOOK_PORT, debug=False)


def demonstrate_n8n_integration():
    """
    Demonstrate various n8n integration patterns.

    This function shows examples of:
    1. Processing sample webhook data
    2. Triggering workflows (if configured)
    3. Error handling
    """
    logger.info("=== n8n Integration Demonstration ===")

    # Example 1: Process sample webhook data
    logger.info("\n1. Processing sample webhook data...")
    sample_webhook_data = {
        "task": "Analyze customer feedback and provide sentiment analysis",
        "data": {
            "customer_id": "12345",
            "feedback": "The product is amazing! Great quality and fast delivery.",
            "rating": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        },
    }

    result = n8n_integration.process_webhook_data(sample_webhook_data)
    logger.info(f"Processing result: {json.dumps(result, indent=2)}")

    # Example 2: Demonstrate workflow triggering (requires actual n8n setup)
    logger.info("\n2. Workflow triggering example (requires n8n setup)...")
    logger.info("To trigger a workflow, you would use:")
    logger.info("n8n_integration.trigger_workflow('workflow-id', {'key': 'value'})")

    # Example 3: Show error handling
    logger.info("\n3. Error handling demonstration...")
    try:
        # This will fail if n8n is not running
        result = n8n_integration.get_workflow_executions("non-existent-workflow")
        logger.info(f"Executions result: {result}")
    except Exception as e:
        logger.info(f"Expected error (n8n not configured): {e}")

    logger.info("\n=== Integration Setup Instructions ===")
    logger.info("To use this integration:")
    logger.info("1. Set up n8n instance (local or cloud)")
    logger.info("2. Create a workflow with webhook trigger")
    logger.info("3. Set environment variables:")
    logger.info("   - N8N_BASE_URL (default: http://localhost:5678)")
    logger.info("   - N8N_API_KEY (for cloud instances)")
    logger.info("   - WEBHOOK_PORT (default: 8080)")
    logger.info("4. Run this script to start the webhook server")
    logger.info("5. Configure n8n webhook to point to this server")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Run as webhook server
        run_webhook_server()
    else:
        # Run demonstration
        demonstrate_n8n_integration()

        # Optionally start the server
        start_server = input("\nWould you like to start the webhook server? (y/n): ")
        if start_server.lower() in ["y", "yes"]:
            run_webhook_server()
