from typing import Any

from .wire import WireCodec


class RemoteHandle:
    """
    Dynamic per-instance wrapper. It forwards attribute reads to stored state
    and turns unknown attributes into RPC calls.
    """

    def __init__(self, *, class_name: str, state: dict[str, Any], gateway_call):
        self._class_name = class_name
        self._state = state
        self._call = gateway_call  # (class_name, method, payload) -> response
        # and exposes .registry for codecs

    def __getattr__(self, name: str) -> Any:
        if isinstance(self._state, dict) and name in self._state:
            return WireCodec.from_wire(self._state[name], self._call.registry)

        def _method(*args, **kwargs):
            payload = {
                "class": self._class_name,
                "method": name,
                "instance": self._state,
                "args": WireCodec.to_wire(list(args)),
                "kwargs": WireCodec.to_wire(kwargs),
            }
            resp = self._call(self._class_name, name, payload)
            if isinstance(resp, dict) and "instance" in resp:
                self._state = resp["instance"]
            result = resp.get("result", resp)
            return WireCodec.from_wire(result, self._call.registry)

        return _method

    def model_dump(self) -> dict[str, Any]:
        return WireCodec.from_wire(self._state, self._call.registry)
