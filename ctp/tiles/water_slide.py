"""WaterSlideStrategy - Water Slide tile stub.

Water Slide mechanics (Map 3 only) will be described and implemented later.
"""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board
from ctp.core.events import GameEvent


class WaterSlideStrategy(TileStrategy):
    """Strategy for Water Slide tile (spaceId=40).

    Stub implementation — Map 3 only, mechanics deferred to post-Phase 4.
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a Water Slide tile.

        Stub: returns empty list.

        Returns:
            Empty list.
        """
        return []

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a Water Slide tile.

        Returns:
            Empty list.
        """
        return []
