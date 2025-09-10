# openhands.sdk.conversation.visualizer

## Classes

### ConversationVisualizer

Handles visualization of conversation events with Rich formatting.

Provides Rich-formatted output with panels and complete content display.

#### Functions

##### on_event(self, event: Annotated[openhands.sdk.event.base.EventBase, DiscriminatedUnion[EventBase]]) -> None

Main event handler that displays events with Rich formatting.

## Functions

### create_default_visualizer(highlight_regex: Optional[Dict[str, str]] = None, **kwargs) -> openhands.sdk.conversation.visualizer.ConversationVisualizer

Create a default conversation visualizer instance.

Args:
    highlight_regex: Dictionary mapping regex patterns to Rich color styles
                   for highlighting keywords in the visualizer.
                   For example: {"Reasoning:": "bold blue",
                   "Thought:": "bold green"}

