"""Conversation router for OpenHands SDK."""

from fastapi import APIRouter

from openhands.sdk.tool.registry import list_registered_tools


router = APIRouter(prefix="/tools")


@router.get("/list")
async def list_available_tools() -> list[str]:
    """List all available tools."""
    tools = list_registered_tools()
    return tools
