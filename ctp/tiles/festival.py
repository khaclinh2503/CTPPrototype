"""FestivalStrategy - festival corner with pot mechanics."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class FestivalStrategy(TileStrategy):
    """Strategy for Festival tiles.

    Festival mechanics:
    - Player landing pays holdCostRate into the pot
    - Player receives reward based on festival_level and increaseRate
    - festival_level increments on each landing (capped at maxFestival)
    """

    # Default festival config
    DEFAULT_HOLD_COST_RATE = 0.02
    DEFAULT_INCREASE_RATE = 2
    DEFAULT_MAX_FESTIVAL = 1

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a festival tile.

        Args:
            player: The player who landed.
            tile: The festival tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Get festival config
        festival_config = board.get_festival_config() or {}
        hold_cost_rate = festival_config.get("holdCostRate", self.DEFAULT_HOLD_COST_RATE)
        increase_rate = festival_config.get("increaseRate", self.DEFAULT_INCREASE_RATE)
        max_festival = festival_config.get("maxFestival", self.DEFAULT_MAX_FESTIVAL)

        # Player pays into pot
        hold_cost = int(player.cash * hold_cost_rate)
        if player.cash >= hold_cost:
            player.cash -= hold_cost

        # Calculate reward based on festival level
        base_reward = 100  # Base reward amount
        festival_level = board.festival_level
        reward = int(base_reward * (increase_rate ** festival_level))

        # Receive reward
        player.cash += reward

        # Increment festival level (capped)
        if festival_level < max_festival:
            board.festival_level += 1

        events.append(GameEvent(
            event_type=EventType.FESTIVAL_UPDATED,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "level": board.festival_level,
                "hold_cost": hold_cost,
                "reward": reward
            }
        ))
        event_bus.publish(events[-1])

        # Also emit bonus received event
        events.append(GameEvent(
            event_type=EventType.BONUS_RECEIVED,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "amount": reward,
                "reason": "festival"
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a festival tile.

        Passing festival has no effect.

        Returns:
            Empty list (no events).
        """
        return []