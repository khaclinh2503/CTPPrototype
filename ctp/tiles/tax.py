"""TaxStrategy - tax payment tile."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class TaxStrategy(TileStrategy):
    """Strategy for Tax tiles.

    Player pays tax based on taxRate (percentage of cash).
    """

    # Default tax rate if not in config
    DEFAULT_TAX_RATE = 0.1

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player landing on a tax tile.

        Args:
            player: The player who landed.
            tile: The tax tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Calculate tax (10% of cash)
        tax_rate = self.DEFAULT_TAX_RATE
        tax_amount = int(player.cash * tax_rate)

        # Apply tax
        if player.cash >= tax_amount:
            player.cash -= tax_amount

        events.append(GameEvent(
            event_type=EventType.TAX_PAID,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "amount": tax_amount,
                "rate": tax_rate
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player passing a tax tile.

        Passing tax has no effect.

        Returns:
            Empty list (no events).
        """
        return []