import re
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    Event,
    EventWithMetrics,
    MessageEvent,
    ObservationEvent,
    PauseEvent,
    SystemPromptEvent,
)
from openhands.sdk.event.condenser import Condensation


# Default color scheme - optimized for readability on both light and dark backgrounds
_DEFAULT_COLORS = {
    # External inputs - using colors with better contrast
    "observation": "bright_cyan",  # Changed from "yellow" for better readability
    "message_user": "gold3",
    "pause": "bright_magenta",  # Changed from "bright_yellow" for better readability
    # Internal system stuff
    "system": "magenta",
    "thought": "bright_black",
    "error": "red",
    # Agent actions
    "action": "blue",
    "message_assistant": "blue",
    # Metrics colors
    "metrics_reasoning": "bright_cyan",  # Changed from "yellow" for better readability
}

# Predefined color themes for different preferences
LIGHT_THEME = {
    # Colors optimized for light backgrounds
    "observation": "blue",
    "message_user": "dark_orange",
    "pause": "purple",
    "system": "dark_magenta",
    "thought": "dim",
    "error": "red",
    "action": "dark_blue",
    "message_assistant": "dark_blue",
    "metrics_reasoning": "blue",
}

DARK_THEME = {
    # Colors optimized for dark backgrounds (similar to original)
    "observation": "yellow",
    "message_user": "gold3",
    "pause": "bright_yellow",
    "system": "magenta",
    "thought": "bright_black",
    "error": "red",
    "action": "blue",
    "message_assistant": "blue",
    "metrics_reasoning": "yellow",
}

HIGH_CONTRAST_THEME = {
    # High contrast colors for accessibility
    "observation": "bright_white",
    "message_user": "bright_yellow",
    "pause": "bright_magenta",
    "system": "bright_cyan",
    "thought": "white",
    "error": "bright_red",
    "action": "bright_blue",
    "message_assistant": "bright_blue",
    "metrics_reasoning": "bright_white",
}

# Legacy color constants for backward compatibility
_OBSERVATION_COLOR = _DEFAULT_COLORS["observation"]
_MESSAGE_USER_COLOR = _DEFAULT_COLORS["message_user"]
_PAUSE_COLOR = _DEFAULT_COLORS["pause"]
_SYSTEM_COLOR = _DEFAULT_COLORS["system"]
_THOUGHT_COLOR = _DEFAULT_COLORS["thought"]
_ERROR_COLOR = _DEFAULT_COLORS["error"]
_ACTION_COLOR = _DEFAULT_COLORS["action"]
_MESSAGE_ASSISTANT_COLOR = _DEFAULT_COLORS["message_assistant"]

DEFAULT_HIGHLIGHT_REGEX = {
    r"^Reasoning:": f"bold {_THOUGHT_COLOR}",
    r"^Thought:": f"bold {_THOUGHT_COLOR}",
    r"^Action:": f"bold {_ACTION_COLOR}",
    r"^Arguments:": f"bold {_ACTION_COLOR}",
    r"^Tool:": f"bold {_OBSERVATION_COLOR}",
    r"^Result:": f"bold {_OBSERVATION_COLOR}",
    # Markdown-style
    r"\*\*(.*?)\*\*": "bold",
    r"\*(.*?)\*": "italic",
}

_PANEL_PADDING = (1, 1)


class ConversationVisualizer:
    """Handles visualization of conversation events with Rich formatting.

    Provides Rich-formatted output with panels and complete content display.
    """

    def __init__(
        self,
        highlight_regex: Dict[str, str] | None = None,
        skip_user_messages: bool = False,
        color_theme: Dict[str, str] | None = None,
    ):
        """Initialize the visualizer.

        Args:
            highlight_regex: Dictionary mapping regex patterns to Rich color styles
                           for highlighting keywords in the visualizer.
                           For example: {"Reasoning:": "bold blue",
                           "Thought:": "bold green"}
            skip_user_messages: If True, skip displaying user messages. Useful for
                                scenarios where user input is not relevant to show.
            color_theme: Dictionary mapping color roles to Rich color names.
                        Available roles: observation, message_user, pause, system,
                        thought, error, action, message_assistant, metrics_reasoning.
                        For example: {"observation": "orange", "pause": "cyan"}
        """
        self._console = Console()
        self._skip_user_messages = skip_user_messages
        self._highlight_patterns: Dict[str, str] = highlight_regex or {}

        # Set up color theme
        self._colors = _DEFAULT_COLORS.copy()
        if color_theme:
            self._colors.update(color_theme)

    def on_event(self, event: Event) -> None:
        """Main event handler that displays events with Rich formatting."""
        panel = self._create_event_panel(event)
        if panel:
            self._console.print(panel)
            self._console.print()  # Add spacing between events

    def _apply_highlighting(self, text: Text) -> Text:
        """Apply regex-based highlighting to text content.

        Args:
            text: The Rich Text object to highlight

        Returns:
            A new Text object with highlighting applied
        """
        if not self._highlight_patterns:
            return text

        # Create a copy to avoid modifying the original
        highlighted = text.copy()

        # Apply each pattern using Rich's built-in highlight_regex method
        for pattern, style in self._highlight_patterns.items():
            pattern_compiled = re.compile(pattern, re.MULTILINE)
            highlighted.highlight_regex(pattern_compiled, style)

        return highlighted

    def _create_event_panel(self, event: Event) -> Panel | None:
        """Create a Rich Panel for the event with appropriate styling."""
        # Use the event's visualize property for content
        content = event.visualize

        if not content.plain.strip():
            return None

        # Apply highlighting if configured
        if self._highlight_patterns:
            content = self._apply_highlighting(content)

        # Determine panel styling based on event type
        if isinstance(event, SystemPromptEvent):
            system_color = self._colors["system"]
            return Panel(
                content,
                title=f"[bold {system_color}]System Prompt[/bold {system_color}]",
                border_style=system_color,
                padding=_PANEL_PADDING,
                expand=True,
            )
        elif isinstance(event, ActionEvent):
            action_color = self._colors["action"]
            return Panel(
                content,
                title=f"[bold {action_color}]Agent Action[/bold {action_color}]",
                subtitle=self._format_metrics_subtitle(event),
                border_style=action_color,
                padding=_PANEL_PADDING,
                expand=True,
            )
        elif isinstance(event, ObservationEvent):
            observation_color = self._colors["observation"]
            return Panel(
                content,
                title=f"[bold {observation_color}]Observation"
                f"[/bold {observation_color}]",
                border_style=observation_color,
                padding=_PANEL_PADDING,
                expand=True,
            )
        elif isinstance(event, MessageEvent):
            if (
                self._skip_user_messages
                and event.llm_message
                and event.llm_message.role == "user"
            ):
                return
            assert event.llm_message is not None
            # Role-based styling
            role_colors = {
                "user": self._colors["message_user"],
                "assistant": self._colors["message_assistant"],
            }
            role_color = role_colors.get(event.llm_message.role, "white")

            title_text = (
                f"[bold {role_color}]Message from {event.source.capitalize()}"
                f"[/bold {role_color}]"
            )
            return Panel(
                content,
                title=title_text,
                subtitle=self._format_metrics_subtitle(event),
                border_style=role_color,
                padding=_PANEL_PADDING,
                expand=True,
            )
        elif isinstance(event, AgentErrorEvent):
            error_color = self._colors["error"]
            return Panel(
                content,
                title=f"[bold {error_color}]Agent Error[/bold {error_color}]",
                subtitle=self._format_metrics_subtitle(event),
                border_style=error_color,
                padding=_PANEL_PADDING,
                expand=True,
            )
        elif isinstance(event, PauseEvent):
            pause_color = self._colors["pause"]
            return Panel(
                content,
                title=f"[bold {pause_color}]User Paused[/bold {pause_color}]",
                border_style=pause_color,
                padding=_PANEL_PADDING,
                expand=True,
            )
        elif isinstance(event, Condensation):
            system_color = self._colors["system"]
            return Panel(
                content,
                title=f"[bold {system_color}]Condensation[/bold {system_color}]",
                subtitle=self._format_metrics_subtitle(event),
                border_style=system_color,
                expand=True,
            )
        else:
            # Fallback panel for unknown event types
            error_color = self._colors["error"]
            return Panel(
                content,
                title=f"[bold {error_color}]UNKNOWN Event: {event.__class__.__name__}"
                f"[/bold {error_color}]",
                subtitle=f"({event.source})",
                border_style=error_color,
                padding=_PANEL_PADDING,
                expand=True,
            )

    def _format_metrics_subtitle(self, event: EventWithMetrics) -> str | None:
        """Format LLM metrics as a visually appealing subtitle string with icons,
        colors, and k/m abbreviations (cache hit rate only)."""
        if not event.metrics or not event.metrics.accumulated_token_usage:
            return None

        usage = event.metrics.accumulated_token_usage
        cost = event.metrics.accumulated_cost or 0.0

        # helper: 1234 -> "1.2K", 1200000 -> "1.2M"
        def abbr(n: int | float) -> str:
            n = int(n or 0)
            if n >= 1_000_000_000:
                s = f"{n / 1_000_000_000:.2f}B"
            elif n >= 1_000_000:
                s = f"{n / 1_000_000:.2f}M"
            elif n >= 1_000:
                s = f"{n / 1_000:.2f}K"
            else:
                return str(n)
            return s.replace(".0", "")

        input_tokens = abbr(usage.prompt_tokens or 0)
        output_tokens = abbr(usage.completion_tokens or 0)

        # Cache hit rate (prompt + cache)
        prompt = usage.prompt_tokens or 0
        cache_read = usage.cache_read_tokens or 0
        cache_rate = f"{(cache_read / prompt * 100):.2f}%" if prompt > 0 else "N/A"
        reasoning_tokens = usage.reasoning_tokens or 0

        # Cost
        cost_str = f"{cost:.4f}" if cost > 0 else "$0.00"

        # Build with color scheme
        parts: list[str] = []
        parts.append(f"[cyan]↑ input {input_tokens}[/cyan]")
        parts.append(f"[magenta]cache hit {cache_rate}[/magenta]")
        if reasoning_tokens > 0:
            reasoning_color = self._colors["metrics_reasoning"]
            parts.append(
                f"[{reasoning_color}] reasoning {abbr(reasoning_tokens)}"
                f"[/{reasoning_color}]"
            )
        parts.append(f"[blue]↓ output {output_tokens}[/blue]")
        parts.append(f"[green]$ {cost_str}[/green]")

        return "Tokens: " + " • ".join(parts)


def create_default_visualizer(
    highlight_regex: Dict[str, str] | None = None, **kwargs
) -> ConversationVisualizer:
    """Create a default conversation visualizer instance.

    Args:
        highlight_regex: Dictionary mapping regex patterns to Rich color styles
                       for highlighting keywords in the visualizer.
                       For example: {"Reasoning:": "bold blue",
                       "Thought:": "bold green"}
        **kwargs: Additional arguments passed to ConversationVisualizer,
                 including color_theme for customizing colors.
    """
    return ConversationVisualizer(
        highlight_regex=DEFAULT_HIGHLIGHT_REGEX
        if highlight_regex is None
        else highlight_regex,
        **kwargs,
    )
