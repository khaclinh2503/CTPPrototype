"""StartStrategy - start tile with fixed passing bonus."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import STARTING_CASH


class StartStrategy(TileStrategy):
    """Strategy for Start tile (spaceId=7).

    - On land: No effect
    - On pass: Gives fixed bonus = passingBonusRate * STARTING_CASH (not % of current cash)
    """

    # Default passing bonus rate
    DEFAULT_PASSING_BONUS_RATE = 0.15

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on the start tile.

        Landing on Start has no effect.

        Returns:
            Empty list (no events).
        """
        return []

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing the start tile.

        Gives fixed passing bonus = DEFAULT_PASSING_BONUS_RATE * STARTING_CASH.
        Bonus is always 150,000 regardless of player's current cash.

        Args:
            player: The player who passed.
            tile: The start tile.
            board: The game board.
            event_bus: Event bus for publishing events.
            players: All players (unused, for interface consistency).

        Returns:
            List of events from passing Start.
        """
        events = []

        # Fixed bonus based on STARTING_CASH, not player's current cash
        bonus_rate = self.DEFAULT_PASSING_BONUS_RATE
        bonus = int(STARTING_CASH * bonus_rate)  # Always 150,000

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
