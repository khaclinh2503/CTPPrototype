"""PrisonStrategy - jail/penalty tile."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class PrisonStrategy(TileStrategy):
    """Strategy for Prison tiles.

    When player lands on prison, they lose a specific number of turns
    based on PrisonSpace.limitTurnByMapId[map_id].
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player landing on a prison tile.

        Args:
            player: The player who landed.
            tile: The prison tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Get prison config from board (not directly stored on board yet)
        # Default to 2 turns for map 1
        prison_turns = 2

        # Set player's prison turns
        player.prison_turns_remaining = prison_turns

        events.append(GameEvent(
            event_type=EventType.PRISON_ENTERED,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "turns": prison_turns
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player passing a prison tile.

        Passing prison has no effect.

        Returns:
            Empty list (no events).
        """
        return []