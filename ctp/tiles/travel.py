"""TravelStrategy - teleport tile."""

import random
from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class TravelStrategy(TileStrategy):
    """Strategy for Travel tiles.

    Teleports player to a random destination and charges
    travel cost based on travelCostRate.
    """

    # Default travel cost rate if not in config
    DEFAULT_TRAVEL_COST_RATE = 0.02

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player landing on a travel tile.

        Args:
            player: The player who landed.
            tile: The travel tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Calculate travel cost (2% of cash)
        travel_cost_rate = self.DEFAULT_TRAVEL_COST_RATE
        travel_cost = int(player.cash * travel_cost_rate)

        if player.cash >= travel_cost:
            player.cash -= travel_cost

        # Teleport to a random position (simplified for Phase 1)
        # In a full implementation, this would consider unowned properties
        # For now, teleport to Start (position 1)
        old_position = player.position
        player.position = 1  # Go to Start

        events.append(GameEvent(
            event_type=EventType.PLAYER_MOVE,
            player_id=player.player_id,
            data={
                "old_pos": old_position,
                "new_pos": player.position,
                "travel_cost": travel_cost,
                "reason": "teleport"
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player passing a travel tile.

        Passing travel has no effect.

        Returns:
            Empty list (no events).
        """
        return []