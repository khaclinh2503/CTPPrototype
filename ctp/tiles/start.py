"""StartStrategy - start tile with passing bonus."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class StartStrategy(TileStrategy):
    """Strategy for Start tile.

    - On land: No effect in Phase 1
    - On pass: Gives passing bonus (15% of cash)
    """

    # Default passing bonus rate if not in config
    DEFAULT_PASSING_BONUS_RATE = 0.15

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player landing on the start tile.

        In Phase 1, landing on Start has no effect.

        Args:
            player: The player who landed.
            tile: The start tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            Empty list (no events).
        """
        # No effect when landing on Start in Phase 1
        return []

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player passing the start tile.

        Gives passing bonus (15% of cash).

        Args:
            player: The player who passed.
            tile: The start tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from passing Start.
        """
        events = []

        # Calculate passing bonus (15% of cash)
        bonus_rate = self.DEFAULT_PASSING_BONUS_RATE
        bonus = int(player.cash * bonus_rate)

        player.cash += bonus

        events.append(GameEvent(
            event_type=EventType.BONUS_RECEIVED,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "amount": bonus,
                "rate": bonus_rate,
                "reason": "passing_start"
            }
        ))
        event_bus.publish(events[-1])

        return events