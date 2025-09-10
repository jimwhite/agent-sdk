# openhands.sdk.event.utils

Utility functions for event processing.

## Functions

### get_unmatched_actions(events: list) -> list[openhands.sdk.event.llm_convertible.ActionEvent]

Find actions in the event history that don't have matching observations.

Optimized to search in reverse chronological order since recent actions
are more likely to be unmatched (pending confirmation).

Args:
    events: List of events to search through

Returns:
    List of ActionEvent objects that don't have corresponding observations

