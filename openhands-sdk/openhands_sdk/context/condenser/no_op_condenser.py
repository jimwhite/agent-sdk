from openhands_sdk.context.condenser.base import CondenserBase
from openhands_sdk.context.view import View
from openhands_sdk.event.condenser import Condensation


class NoOpCondenser(CondenserBase):
    """Simple condenser that returns a view un-manipulated.

    Primarily intended for testing purposes.
    """

    def condense(self, view: View) -> View | Condensation:
        return view
