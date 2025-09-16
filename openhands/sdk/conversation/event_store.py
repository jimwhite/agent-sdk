# state.py
import json
import operator
from typing import Iterator, SupportsIndex, overload

from openhands.sdk.conversation.persistence_const import (
    EVENT_FILE_PATTERN,
    EVENT_NAME_RE,
    EVENTS_DIR,
)
from openhands.sdk.event import Event, EventBase, EventID
from openhands.sdk.event.condenser import (
    Condensation,
    CondensationSummaryEvent,
)
from openhands.sdk.event.llm_convertible import (
    ActionEvent,
    MessageEvent,
    ObservationEvent,
    SystemPromptEvent,
)
from openhands.sdk.io import FileStore
from openhands.sdk.logger import get_logger
from openhands.sdk.utils.protocol import ListLike


def _parse_event(data: dict) -> Event:
    """Heuristically parse event JSON into a concrete Event subclass.

    Removes legacy 'kind' field if present. Falls back to EventBase validation
    if no subtype matches, which will likely raise ValidationError for extras.
    """
    data = dict(data)
    data.pop("kind", None)

    if "llm_message" in data and "source" in data:
        return MessageEvent.model_validate(data)
    if "action" in data and "tool_call" in data and "tool_name" in data:
        return ActionEvent.model_validate(data)
    if "observation" in data and "tool_call_id" in data:
        return ObservationEvent.model_validate(data)
    if "system_prompt" in data and "tools" in data:
        return SystemPromptEvent.model_validate(data)
    if "forgotten_event_ids" in data or "summary_offset" in data:
        return Condensation.model_validate(data)
    if "summary" in data and "source" in data and "llm_message" not in data:
        return CondensationSummaryEvent.model_validate(data)
    # User rejection event
    if {
        "action_id",
        "tool_name",
        "tool_call_id",
        "rejection_reason",
    }.issubset(data.keys()):
        from openhands.sdk.event.llm_convertible import UserRejectObservation

        return UserRejectObservation.model_validate(data)
    # Heuristic: a minimal user-sourced event with only base fields is a PauseEvent
    if "source" in data and set(data.keys()) <= {"id", "timestamp", "source"}:
        from openhands.sdk.event.user_action import PauseEvent

        if data.get("source") == "user":
            return PauseEvent.model_validate(data)
        return EventBase.model_validate(data)
    # Last resort
    return EventBase.model_validate(data)


logger = get_logger(__name__)


class EventLog(ListLike[Event]):
    def __init__(self, fs: FileStore, dir_path: str = EVENTS_DIR) -> None:
        self._fs = fs
        self._dir = dir_path
        self._id_to_idx: dict[EventID, int] = {}
        self._idx_to_id: dict[int, EventID] = {}
        self._length = self._scan_and_build_index()

    def get_index(self, event_id: EventID) -> int:
        """Return the integer index for a given event_id."""
        try:
            return self._id_to_idx[event_id]
        except KeyError:
            raise KeyError(f"Unknown event_id: {event_id}")

    def get_id(self, idx: int) -> EventID:
        """Return the event_id for a given index."""
        if idx < 0:
            idx += self._length
        if idx < 0 or idx >= self._length:
            raise IndexError("Event index out of range")
        return self._idx_to_id[idx]

    @overload
    def __getitem__(self, idx: SupportsIndex, /) -> Event: ...
    @overload
    def __getitem__(self, idx: slice, /) -> list[Event]: ...

    def __getitem__(self, idx: SupportsIndex | slice, /) -> Event | list[Event]:
        if isinstance(idx, slice):
            start, stop, step = idx.indices(self._length)
            return [self[i] for i in range(start, stop, step)]
        # idx is int-like (SupportsIndex)
        i = operator.index(idx)
        if i < 0:
            i += self._length
        if i < 0 or i >= self._length:
            raise IndexError("Event index out of range")
        txt = self._fs.read(self._path(i))
        if not txt:
            raise FileNotFoundError(f"Missing event file: {self._path(i)}")
        return _parse_event(json.loads(txt))

    def __iter__(self) -> Iterator[Event]:
        for i in range(self._length):
            txt = self._fs.read(self._path(i))
            if not txt:
                continue
            evt = _parse_event(json.loads(txt))
            evt_id = evt.id
            # only backfill mapping if missing
            if i not in self._idx_to_id:
                self._idx_to_id[i] = evt_id
                self._id_to_idx.setdefault(evt_id, i)
            yield evt

    def append(self, item: Event) -> None:
        evt_id = item.id
        # Check for duplicate ID
        if evt_id in self._id_to_idx:
            existing_idx = self._id_to_idx[evt_id]
            raise ValueError(
                f"Event with ID '{evt_id}' already exists at index {existing_idx}"
            )

        path = self._path(self._length, event_id=evt_id)
        self._fs.write(path, item.model_dump_json(exclude_none=True))
        self._idx_to_id[self._length] = evt_id
        self._id_to_idx[evt_id] = self._length
        self._length += 1

    def __len__(self) -> int:
        return self._length

    def _path(self, idx: int, *, event_id: EventID | None = None) -> str:
        return f"{self._dir}/{
            EVENT_FILE_PATTERN.format(
                idx=idx, event_id=event_id or self._idx_to_id[idx]
            )
        }"

    def _scan_and_build_index(self) -> int:
        try:
            paths = self._fs.list(self._dir)
        except Exception:
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            return 0

        by_idx: dict[int, EventID] = {}
        for p in paths:
            name = p.rsplit("/", 1)[-1]
            m = EVENT_NAME_RE.match(name)
            if m:
                idx = int(m.group("idx"))
                evt_id = m.group("event_id")
                by_idx[idx] = evt_id
            else:
                logger.warning(f"Unrecognized event file name: {name}")

        if not by_idx:
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            return 0

        n = 0
        while True:
            if n not in by_idx:
                if any(i > n for i in by_idx.keys()):
                    logger.warning(
                        "Event index gap detected: "
                        f"expect next index {n} but got {sorted(by_idx.keys())}"
                    )
                break
            n += 1

        self._id_to_idx.clear()
        self._idx_to_id.clear()
        for i in range(n):
            evt_id = by_idx[i]
            self._idx_to_id[i] = evt_id
            if evt_id in self._id_to_idx:
                logger.warning(
                    f"Duplicate event ID '{evt_id}' found during scan. "
                    f"Keeping first occurrence at index {self._id_to_idx[evt_id]}, "
                    f"ignoring duplicate at index {i}"
                )
            else:
                self._id_to_idx[evt_id] = i
        return n
