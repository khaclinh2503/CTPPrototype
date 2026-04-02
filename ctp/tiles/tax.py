"""TaxStrategy - tax payment tile."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import calc_invested_build_cost


class TaxStrategy(TileStrategy):
    """Strategy for Tax tiles (spaceId=8).

    Player pays tax = taxRate (0.1) * total invested build cost of all owned properties.
    If player has no properties, tax = 0.
    """

    # Default tax rate
    DEFAULT_TAX_RATE = 0.1

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a tax tile.

        Tax = taxRate * sum(calc_invested_build_cost for each owned property).

        Args:
            player: The player who landed.
            tile: The tax tile.
            board: The game board.
            event_bus: Event bus for publishing events.
            players: All players (unused for tax, included for interface consistency).

        Returns:
            List of events from this tile resolution.
        """
        events = []

        tax_rate = self.DEFAULT_TAX_RATE

        # Calculate total invested build cost across all owned properties
        total_property_value = sum(
            calc_invested_build_cost(board, pos)
            for pos in player.owned_properties
        )

        # Tax = taxRate * total invested value
        tax_amount = int(tax_rate * total_property_value)

        # Deduct tax (even if it makes cash negative - bankruptcy handler resolves)
        player.cash -= tax_amount

        events.append(GameEvent(
            event_type=EventType.TAX_PAID,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "amount": tax_amount,
                "rate": tax_rate,
                "total_property_value": total_property_value
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a tax tile.

        Passing tax has no effect.

        Returns:
            Empty list (no events).
        """
        return []
