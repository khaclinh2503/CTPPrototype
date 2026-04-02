"""GameEvent and EventBus for CTP game state machine."""

from dataclasses import dataclass, field
from typing import Any, Callable
from collections import deque
from enum import Enum, auto


class EventType(Enum):
    """Event types for game actions.

    These events drive the game state machine and allow components
    to react to game actions without tight coupling.
    """

    DICE_ROLL = auto()
    PLAYER_MOVE = auto()
    TILE_LANDED = auto()
    PROPERTY_PURCHASED = auto()
    PROPERTY_SOLD = auto()
    RENT_PAID = auto()
    TAX_PAID = auto()
    BONUS_RECEIVED = auto()
    PRISON_ENTERED = auto()
    PRISON_EXITED = auto()
    FESTIVAL_UPDATED = auto()
    CARD_DRAWN = auto()
    PLAYER_BANKRUPT = auto()
    GAME_STARTED = auto()
    GAME_ENDED = auto()
    TURN_STARTED = auto()
    TURN_ENDED = auto()
    PLAYER_ELIMINATED = auto()


@dataclass
class GameEvent:
    """Event emitted during game execution.

    Attributes:
        event_type: Type of event (EventType enum).
        player_id: Player ID associated with this event (None for game-level events).
        data: Additional event data (e.g., {"roll": 5} for DICE_ROLL).
        timestamp: Game time when event occurred (can be set by game clock).
    """

    event_type: EventType
    player_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0  # Can be set by game clock


class EventBus:
    """Simple event bus for game event dispatching.

    This implements the publish-subscribe pattern to allow game
    components to react to events without tight coupling.

    Example:
        bus = EventBus()

        def on_dice_roll(event):
            print(f"Player {event.player_id} rolled {event.data['roll']}")

        bus.subscribe(EventType.DICE_ROLL, on_dice_roll)
        bus.publish(GameEvent(EventType.DICE_ROLL, player_id="p1", data={"roll": 5}))
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: dict[EventType, list[Callable[[GameEvent], None]]] = {}
        self._event_queue: deque[GameEvent] = deque()
        self._event_history: list[GameEvent] = []

    def subscribe(self, event_type: EventType, handler: Callable[[GameEvent], None]) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Type of event to subscribe to.
            handler: Callback function that receives GameEvent.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[GameEvent], None]) -> None:
        """Unregister a handler for an event type.

        Args:
            event_type: Type of event to unsubscribe from.
            handler: Callback function to remove.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass  # Handler not found

    def publish(self, event: GameEvent) -> None:
        """Publish an event to all subscribers.

        The event is added to the queue, history, and immediately
        dispatched to all matching handlers.

        Args:
            event: GameEvent to publish.
        """
        self._event_queue.append(event)
        self._event_history.append(event)
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                handler(event)

    def get_events(self, event_type: EventType | None = None) -> list[GameEvent]:
        """Get all events, optionally filtered by type.

        Args:
            event_type: If provided, only return events of this type.

        Returns:
            List of GameEvent objects.
        """
        if event_type is None:
            return list(self._event_history)
        return [e for e in self._event_history if e.event_type == event_type]

    def clear(self) -> None:
        """Clear event queue and history."""
        self._event_queue.clear()
        self._event_history.clear()

    @property
    def event_count(self) -> int:
        """Get total number of events in history."""
        return len(self._event_history)