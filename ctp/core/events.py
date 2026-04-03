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
    PROPERTY_ACQUIRED = auto()   # A buys property from B (forced acquisition)
    PROPERTY_UPGRADED = auto()   # Property upgraded (revisit, 2nd+ visit)
    PROPERTY_BUILT = auto()      # House built as part of initial purchase
    MINIGAME_RESULT = auto()     # Mini-game outcome
    FESTIVAL_FEE_PAID = auto()  # Player pays festival fee to system
    RENT_OWED = auto()          # Player owes rent but can't afford (deferred to bankruptcy)
    DEBT_SETTLED = auto()       # Creditor receives actual amount after debtor liquidation
    GOD_BUILD = auto()           # Player built/bought via God tile
    TILE_ELEVATED = auto()       # A tile was elevated by God action
    TILE_LOWERED = auto()        # An elevated tile was triggered and lowered
    WATER_SLIDE_WAVE_SET = auto()   # Wave created/replaced on Water Slide tile
    WATER_SLIDE_PUSHED = auto()     # Player pushed to wave dest by wave zone
    # Phase 02.1: Card effect events
    CARD_EFFECT_ANGEL = auto()               # EF_20: toll waived 100%
    CARD_EFFECT_DISCOUNT_TOLL = auto()       # EF_2: toll 50%
    CARD_EFFECT_SHIELD_BLOCKED = auto()      # EF_3: attack blocked by shield
    CARD_EFFECT_ESCAPE_USED = auto()         # EF_19: prison escape card used / player dùng escape card thoát tù
    CARD_EFFECT_PINWHEEL_BYPASS = auto()     # EF_22: bypass elevated tile / player bypass elevated tile bằng Pinwheel
    CARD_EFFECT_FORCE_SELL = auto()          # EF_4: force sell opponent tile
    CARD_EFFECT_SWAP_CITY = auto()           # EF_5: swap city ownership
    CARD_EFFECT_DOWNGRADE = auto()           # EF_6/7: downgrade tile level
    CARD_EFFECT_VIRUS = auto()               # EF_7/8/9: virus debuff applied
    CARD_EFFECT_GO_TO_START = auto()         # EF_14: teleport to START
    CARD_EFFECT_GO_TO_PRISON = auto()        # EF_13: teleport to PRISON
    CARD_EFFECT_DOUBLE_TOLL_DEBUFF = auto()  # EF_16: self double toll debuff
    CARD_EFFECT_GO_TO_FESTIVAL = auto()      # EF_10: teleport to FESTIVAL tile
    CARD_EFFECT_GO_TO_FESTIVAL_TILE = auto() # EF_11: teleport to tile with festival marker
    CARD_EFFECT_GO_TO_TRAVEL = auto()        # EF_12: teleport to TRAVEL tile
    CARD_EFFECT_GO_TO_TAX = auto()           # EF_26: teleport to TAX tile
    CARD_EFFECT_GO_TO_GOD = auto()           # EF_21: teleport to nearest GOD tile
    CARD_EFFECT_HOST_FESTIVAL = auto()       # EF_15: set festival marker free
    CARD_EFFECT_DONATE_CITY = auto()         # EF_17: donate tile to another player
    CARD_EFFECT_CHARITY = auto()             # EF_18: charity — all pay poorest
    CARD_EFFECT_GO_TO_WATER_SLIDE = auto()  # EF_30: teleport to nearest WATER_SLIDE tile


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