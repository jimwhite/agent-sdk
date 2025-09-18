"""Browser tool executor implementation using browser-use MCP server wrapper."""

import json
import logging

from openhands.sdk.tool import SchemaInstance, ToolExecutor
from openhands.sdk.utils import to_camel_case
from openhands.sdk.utils.async_executor import AsyncExecutor
from openhands.tools.browser_use.definition import make_browser_observation_schema
from openhands.tools.browser_use.server import CustomBrowserUseServer


# Suppress browser-use logging for cleaner integration
logging.getLogger("browser_use").setLevel(logging.WARNING)

RETURN_SCHEMA_INSTANCE_NAME = "BrowserObservation"


class BrowserToolExecutor(ToolExecutor):
    """Executor that wraps browser-use MCP server for OpenHands integration."""

    def __init__(
        self,
        session_timeout_minutes: int = 30,
        headless: bool = True,
        allowed_domains: list[str] | None = None,
        **config,
    ):
        self._server = CustomBrowserUseServer(
            session_timeout_minutes=session_timeout_minutes
        )
        self._config = {
            "headless": headless,
            "allowed_domains": allowed_domains or [],
            **config,
        }
        self._initialized = False
        self._async_executor = AsyncExecutor()

    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        """Submit an action to run in the background loop and wait for result."""
        return self._async_executor.run_async(
            self._execute_action, action, timeout=300.0
        )

    async def _execute_action(self, action: SchemaInstance) -> SchemaInstance:
        """Execute browser action asynchronously."""
        from openhands.tools.browser_use.definition import (
            BrowserClickTool,
            BrowserCloseTabTool,
            BrowserGetContentTool,
            BrowserGetStateTool,
            BrowserGoBackTool,
            BrowserListTabsTool,
            BrowserNavigateTool,
            BrowserScrollTool,
            BrowserSwitchTabTool,
            BrowserTypeTool,
        )

        action.validate_data()

        action_name = action.name.removesuffix("Action")

        try:
            result = ""
            # Route to appropriate method based on action type

            if action_name == to_camel_case(BrowserNavigateTool.__name__):
                url = action.data.get("url")
                new_tab = action.data.get("new_tab")
                assert url is not None, "Parameter `url` is required."
                assert new_tab is not None, "Parameter `new_tab` is required."
                result = await self.navigate(url, new_tab)
            elif action_name == to_camel_case(BrowserClickTool.__name__):
                index = action.data.get("index")
                new_tab = action.data.get("new_tab")
                assert index is not None, "Parameter `index` is required."
                assert new_tab is not None, "Parameter `new_tab` is required."
                result = await self.click(index, new_tab)
            elif action_name == to_camel_case(BrowserTypeTool.__name__):
                index = action.data.get("index")
                text = action.data.get("text")
                assert index is not None, "Parameter `index` is required."
                assert text is not None, "Parameter `text` is required."
                result = await self.type_text(index, text)
            elif action_name == to_camel_case(BrowserGetStateTool.__name__):
                include_screenshot = action.data.get("include_screenshot")
                assert include_screenshot is not None, (
                    "Parameter `include_screenshot` is required."
                )
                return await self.get_state(include_screenshot)
            elif action_name == to_camel_case(BrowserGetContentTool.__name__):
                extract_links = action.data.get("extract_links")
                start_from_char = action.data.get("start_from_char")
                assert extract_links is not None, (
                    "Parameter `extract_links` is required."
                )
                assert start_from_char is not None, (
                    "Parameter `start_from_char` is required."
                )
                result = await self.get_content(extract_links, start_from_char)
            elif action_name == to_camel_case(BrowserScrollTool.__name__):
                direction = action.data.get("direction")
                assert direction is not None, "Parameter `direction` is required."
                result = await self.scroll(direction)
            elif action_name == to_camel_case(BrowserGoBackTool.__name__):
                result = await self.go_back()
            elif action_name == to_camel_case(BrowserListTabsTool.__name__):
                result = await self.list_tabs()
            elif action_name == to_camel_case(BrowserSwitchTabTool.__name__):
                tab_id = action.data.get("tab_id")
                assert tab_id is not None, "Parameter `tab_id` is required."
                result = await self.switch_tab(tab_id)
            elif action_name == to_camel_case(BrowserCloseTabTool.__name__):
                tab_id = action.data.get("tab_id")
                assert tab_id is not None, "Parameter `tab_id` is required."
                result = await self.close_tab(tab_id)
            else:
                error_msg = f"Unsupported action type: {type(action)}"
                return SchemaInstance(
                    name=RETURN_SCHEMA_INSTANCE_NAME,
                    definition=make_browser_observation_schema(),
                    data={"output": "", "error": error_msg},
                )

            return SchemaInstance(
                name=RETURN_SCHEMA_INSTANCE_NAME,
                definition=make_browser_observation_schema(),
                data={"output": result},
            )
        except Exception as e:
            error_msg = f"Browser operation failed: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return SchemaInstance(
                name=RETURN_SCHEMA_INSTANCE_NAME,
                definition=make_browser_observation_schema(),
                data={"output": "", "error": error_msg},
            )

    async def _ensure_initialized(self):
        """Ensure browser session is initialized."""
        if not self._initialized:
            # Initialize browser session with our config
            await self._server._init_browser_session(**self._config)
            self._initialized = True

    # Navigation & Browser Control Methods
    async def navigate(self, url: str, new_tab: bool = False) -> str:
        """Navigate to a URL."""
        await self._ensure_initialized()
        return await self._server._navigate(url, new_tab)

    async def go_back(self) -> str:
        """Go back in browser history."""
        await self._ensure_initialized()
        return await self._server._go_back()

    # Page Interaction
    async def click(self, index: int, new_tab: bool = False) -> str:
        """Click an element by index."""
        await self._ensure_initialized()
        return await self._server._click(index, new_tab)

    async def type_text(self, index: int, text: str) -> str:
        """Type text into an element."""
        await self._ensure_initialized()
        return await self._server._type_text(index, text)

    async def scroll(self, direction: str = "down") -> str:
        """Scroll the page."""
        await self._ensure_initialized()
        return await self._server._scroll(direction)

    async def get_state(self, include_screenshot: bool = False) -> SchemaInstance:
        """Get current browser state with interactive elements."""
        await self._ensure_initialized()
        result_json = await self._server._get_browser_state(include_screenshot)

        if include_screenshot:
            try:
                result_data = json.loads(result_json)
                screenshot_data = result_data.pop("screenshot", None)

                # Return clean JSON + separate screenshot data
                clean_json = json.dumps(result_data, indent=2)
                return SchemaInstance(
                    name=RETURN_SCHEMA_INSTANCE_NAME,
                    definition=make_browser_observation_schema(),
                    data={"output": clean_json, "screenshot_data": screenshot_data},
                )
            except json.JSONDecodeError:
                # If JSON parsing fails, return as-is
                pass

        return SchemaInstance(
            name=RETURN_SCHEMA_INSTANCE_NAME,
            definition=make_browser_observation_schema(),
            data={"output": result_json},
        )

    # Tab Management
    async def list_tabs(self) -> str:
        """List all open tabs."""
        await self._ensure_initialized()
        return await self._server._list_tabs()

    async def switch_tab(self, tab_id: str) -> str:
        """Switch to a different tab."""
        await self._ensure_initialized()
        return await self._server._switch_tab(tab_id)

    async def close_tab(self, tab_id: str) -> str:
        """Close a specific tab."""
        await self._ensure_initialized()
        return await self._server._close_tab(tab_id)

    # Content Extraction
    async def get_content(self, extract_links: bool, start_from_char: int) -> str:
        """Extract page content, optionally with links."""
        await self._ensure_initialized()
        return await self._server._get_content(
            extract_links=extract_links, start_from_char=start_from_char
        )

    async def close_browser(self) -> str:
        """Close the browser session."""
        if self._initialized:
            result = await self._server._close_browser()
            self._initialized = False
            return result
        return "No browser session to close"

    async def cleanup(self):
        """Cleanup browser resources."""
        try:
            await self.close_browser()
            if hasattr(self._server, "_close_all_sessions"):
                await self._server._close_all_sessions()
        except Exception as e:
            logging.warning(f"Error during browser cleanup: {e}")

    def close(self):
        """Close the browser executor and cleanup resources."""
        try:
            # Run cleanup in the async executor with a shorter timeout
            self._async_executor.run_async(self.cleanup, timeout=30.0)
        except Exception as e:
            logging.warning(f"Error during browser cleanup: {e}")
        finally:
            # Always close the async executor
            self._async_executor.close()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass  # Ignore cleanup errors during deletion
