# openhands.sdk.context.condenser.no_op_condenser

## Classes

### NoOpCondenser

Simple condenser that returns a view un-manipulated.

Primarily intended for testing purposes.

#### Functions

##### condense(self, view: openhands.sdk.context.view.View) -> openhands.sdk.context.view.View | openhands.sdk.event.condenser.Condensation

Condense a sequence of events into a potentially smaller list.

New condenser strategies should override this method to implement their own
condensation logic. Call `self.add_metadata` in the implementation to record any
relevant per-condensation diagnostic information.

Args:
    view: A view of the history containing all events that should be condensed.

Returns:
    View | Condensation: A condensed view of the events or an event indicating
    the history has been condensed.

