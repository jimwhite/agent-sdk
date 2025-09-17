"""Browser-use tool implementation for web automation."""

from typing import Sequence

from openhands.sdk.llm import ImageContent, TextContent
from openhands.sdk.tool import (
    Schema,
    SchemaField,
    SchemaInstance,
    Tool,
    ToolAnnotations,
    ToolDataConverter,
)
from openhands.sdk.utils import maybe_truncate
from openhands.tools.browser_use.impl import BrowserToolExecutor


# Maximum output size for browser observations
MAX_BROWSER_OUTPUT_SIZE = 50000


def make_browser_observation_schema() -> Schema:
    """Common output schema for all browser tools."""
    return Schema(
        name="openhands.tools.browser_use.output",
        fields=[
            SchemaField.create(
                name="output",
                description="The output message from the browser operation",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="error",
                description="Error message if any",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="screenshot_data",
                description="Base64 screenshot data if available",
                type=str,
                required=False,
                default=None,
            ),
        ],
    )


class BrowserDataConverter(ToolDataConverter):
    """Data converter for browser tools."""

    def agent_observation(
        self, observation: SchemaInstance
    ) -> Sequence[TextContent | ImageContent]:
        observation.validate_data()

        error = observation.data.get("error")
        if error:
            return [TextContent(text=f"Error: {error}")]

        output = observation.data.get("output", "")
        content: list[TextContent | ImageContent] = [
            TextContent(text=maybe_truncate(output, MAX_BROWSER_OUTPUT_SIZE))
        ]

        screenshot_data = observation.data.get("screenshot_data")
        if screenshot_data:
            # Convert base64 to data URL format for ImageContent
            data_url = f"data:image/png;base64,{screenshot_data}"
            content.append(ImageContent(image_urls=[data_url]))

        return content


# ============================================
# `browser_navigate`
# ============================================
def make_browser_navigate_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.navigate.input",
        fields=[
            SchemaField.create(
                name="url",
                description="The URL to navigate to",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="new_tab",
                description="Whether to open in a new tab. Default: False",
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_NAVIGATE_DESCRIPTION = """Navigate to a URL in the browser.

This tool allows you to navigate to any web page. You can optionally open the URL in a new tab.

Parameters:
- url: The URL to navigate to (required)
- new_tab: Whether to open in a new tab (optional, default: False)

Examples:
- Navigate to Google: url="https://www.google.com"
- Open GitHub in new tab: url="https://github.com", new_tab=True
"""  # noqa: E501


class BrowserNavigateTool(Tool):
    """Tool for browser navigation."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_navigate",
            description=BROWSER_NAVIGATE_DESCRIPTION,
            input_schema=make_browser_navigate_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_navigate",
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_click`
# ============================================
def make_browser_click_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.click.input",
        fields=[
            SchemaField.create(
                name="index",
                description=(
                    "The index of the element to click (from browser_get_state)"
                ),
                type=int,
                required=True,
            ),
            SchemaField.create(
                name="new_tab",
                description=(
                    "Whether to open any resulting navigation in a new tab. "
                    "Default: False"
                ),
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_CLICK_DESCRIPTION = """Click an element on the page by its index.

Use this tool to click on interactive elements like buttons, links, or form controls. 
The index comes from the browser_get_state tool output.

Parameters:
- index: The index of the element to click (from browser_get_state)
- new_tab: Whether to open any resulting navigation in a new tab (optional)

Important: Only use indices that appear in your current browser_get_state output.
"""  # noqa: E501


class BrowserClickTool(Tool):
    """Tool for clicking browser elements."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_click",
            description=BROWSER_CLICK_DESCRIPTION,
            input_schema=make_browser_click_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_click",
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_type`
# ============================================
def make_browser_type_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.type.input",
        fields=[
            SchemaField.create(
                name="index",
                description="The index of the input element (from browser_get_state)",
                type=int,
                required=True,
            ),
            SchemaField.create(
                name="text",
                description="The text to type",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_TYPE_DESCRIPTION = """Type text into an input field.

Use this tool to enter text into form fields, search boxes, or other text input elements.
The index comes from the browser_get_state tool output.

Parameters:
- index: The index of the input element (from browser_get_state)
- text: The text to type

Important: Only use indices that appear in your current browser_get_state output.
"""  # noqa: E501


class BrowserTypeTool(Tool):
    """Tool for typing text into browser elements."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_type",
            description=BROWSER_TYPE_DESCRIPTION,
            input_schema=make_browser_type_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_type",
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_get_state`
# ============================================
def make_browser_get_state_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.get_state.input",
        fields=[
            SchemaField.create(
                name="include_screenshot",
                description=(
                    "Whether to include a screenshot of the current page. "
                    "Default: False"
                ),
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_GET_STATE_DESCRIPTION = """Get the current state of the page including all interactive elements.

This tool returns the current page content with numbered interactive elements that you can 
click or type into. Use this frequently to understand what's available on the page.

Parameters:
- include_screenshot: Whether to include a screenshot (optional, default: False)
"""  # noqa: E501


class BrowserGetStateTool(Tool):
    """Tool for getting browser state."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_get_state",
            description=BROWSER_GET_STATE_DESCRIPTION,
            input_schema=make_browser_get_state_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_get_state",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_get_content`
# ============================================
def make_browser_get_content_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.get_content.input",
        fields=[
            SchemaField.create(
                name="extract_links",
                description="Whether to include links in the content (default: False)",
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="start_from_char",
                description=(
                    "Character index to start from in the page content (default: 0)"
                ),
                type=int,
                required=False,
                default=0,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_GET_CONTENT_DESCRIPTION = """Extract the main content of the current page in clean markdown format. It has been filtered to remove noise and advertising content.

If the content was truncated and you need more information, use start_from_char parameter to continue from where truncation occurred.
"""  # noqa: E501


class BrowserGetContentTool(Tool):
    """Tool for getting page content in markdown."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_get_content",
            description=BROWSER_GET_CONTENT_DESCRIPTION,
            input_schema=make_browser_get_content_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_get_content",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_scroll`
# ============================================
def make_browser_scroll_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.scroll.input",
        fields=[
            SchemaField.create(
                name="direction",
                description=(
                    "Direction to scroll. Options: 'up', 'down'. Default: 'down'"
                ),
                type=str,
                required=False,
                default="down",
                enum=["up", "down"],
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_SCROLL_DESCRIPTION = """Scroll the page up or down.

Use this tool to scroll through page content when elements are not visible or when you need
to see more content.

Parameters:
- direction: Direction to scroll - "up" or "down" (optional, default: "down")
"""  # noqa: E501


class BrowserScrollTool(Tool):
    """Tool for scrolling the browser page."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_scroll",
            description=BROWSER_SCROLL_DESCRIPTION,
            input_schema=make_browser_scroll_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_scroll",
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_go_back`
# ============================================
def make_browser_go_back_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.go_back.input",
        fields=[
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_GO_BACK_DESCRIPTION = """Go back to the previous page in browser history.

Use this tool to navigate back to the previously visited page, similar to clicking the 
browser's back button.
"""  # noqa: E501


class BrowserGoBackTool(Tool):
    """Tool for going back in browser history."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_go_back",
            description=BROWSER_GO_BACK_DESCRIPTION,
            input_schema=make_browser_go_back_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_go_back",
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_list_tabs`
# ============================================
def make_browser_list_tabs_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.list_tabs.input",
        fields=[
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_LIST_TABS_DESCRIPTION = """List all open browser tabs.

This tool shows all currently open tabs with their IDs, titles, and URLs. Use the tab IDs
with browser_switch_tab or browser_close_tab.
"""  # noqa: E501


class BrowserListTabsTool(Tool):
    """Tool for listing browser tabs."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_list_tabs",
            description=BROWSER_LIST_TABS_DESCRIPTION,
            input_schema=make_browser_list_tabs_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_list_tabs",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_switch_tab`
# ============================================
def make_browser_switch_tab_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.switch_tab.input",
        fields=[
            SchemaField.create(
                name="tab_id",
                description=(
                    "4 Character Tab ID of the tab to switch to "
                    "(from browser_list_tabs)"
                ),
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_SWITCH_TAB_DESCRIPTION = """Switch to a different browser tab.

Use this tool to switch between open tabs. Get the tab_id from browser_list_tabs.

Parameters:
- tab_id: 4 Character Tab ID of the tab to switch to
"""


class BrowserSwitchTabTool(Tool):
    """Tool for switching browser tabs."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_switch_tab",
            description=BROWSER_SWITCH_TAB_DESCRIPTION,
            input_schema=make_browser_switch_tab_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_switch_tab",
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=False,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# `browser_close_tab`
# ============================================
def make_browser_close_tab_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.browser_use.close_tab.input",
        fields=[
            SchemaField.create(
                name="tab_id",
                description=(
                    "4 Character Tab ID of the tab to close (from browser_list_tabs)"
                ),
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


BROWSER_CLOSE_TAB_DESCRIPTION = """Close a specific browser tab.

Use this tool to close tabs you no longer need. Get the tab_id from browser_list_tabs.

Parameters:
- tab_id: 4 Character Tab ID of the tab to close
"""


class BrowserCloseTabTool(Tool):
    """Tool for closing browser tabs."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor):
        return cls(
            name="browser_close_tab",
            description=BROWSER_CLOSE_TAB_DESCRIPTION,
            input_schema=make_browser_close_tab_input_schema(),
            output_schema=make_browser_observation_schema(),
            annotations=ToolAnnotations(
                title="browser_close_tab",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=False,
            ),
            executor=executor,
            data_converter=BrowserDataConverter(),
        )


# ============================================
# Browser Tool Set
# ============================================
class BrowserToolSet(Tool):
    """A collection of browser automation tools."""

    @classmethod
    def create(cls, executor: BrowserToolExecutor) -> list[Tool]:
        """Create all browser tools with the given executor."""
        return [
            BrowserNavigateTool.create(executor),
            BrowserClickTool.create(executor),
            BrowserTypeTool.create(executor),
            BrowserGetStateTool.create(executor),
            BrowserGetContentTool.create(executor),
            BrowserScrollTool.create(executor),
            BrowserGoBackTool.create(executor),
            BrowserListTabsTool.create(executor),
            BrowserSwitchTabTool.create(executor),
            BrowserCloseTabTool.create(executor),
        ]
