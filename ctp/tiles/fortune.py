"""FortuneStrategy - stub for Fortune tiles (card/event)."""

import json
import os
from typing import Any
from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType

_card_data_cache: dict[str, Any] | None = None


def _load_raw_card_data() -> dict[str, Any]:
    """Load và cache raw card data từ Card.json.

    Returns:
        Dict mapping card_id -> {"effect": "EF_XX", ...}
    """
    global _card_data_cache
    if _card_data_cache is not None:
        return _card_data_cache
    card_json_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "Card.json"
    )
    with open(card_json_path, encoding="utf-8") as f:
        raw = json.load(f)
    _card_data_cache = raw.get("Card", {})
    return _card_data_cache


class FortuneStrategy(TileStrategy):
    """Strategy for Fortune (card/event) tiles.

    This is a STUB implementation per D-03:
    - Creates CARD_DRAWN event but applies no effect
    - Card effects (EF_X codes) not implemented until Phase 3
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a fortune tile.

        STUB: Creates CARD_DRAWN event but applies no effect.

        Args:
            player: The player who landed.
            tile: The fortune tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Stub: Record card draw but apply no effect
        card_id = f"card_{tile.opt}" if tile.opt else "fortune_card"

        events.append(GameEvent(
            event_type=EventType.CARD_DRAWN,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "card_id": card_id,
                "tile_type": "chance",
                "effect_applied": False,  # Stub - no effect in Phase 1
                "note": "Card effects not implemented until Phase 3"
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a fortune tile.

        Passing fortune has no effect.

        Returns:
            Empty list (no events).
        """
        return []