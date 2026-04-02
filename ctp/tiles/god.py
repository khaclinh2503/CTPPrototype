"""GodStrategy - God tile stub.

God space mechanics (Map 2/3) will be described and implemented later.
"""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board
from ctp.core.events import GameEvent


class GodStrategy(TileStrategy):
    """Strategy for God tile (spaceId=10).

    Stub implementation — mechanics deferred to post-Phase 4.
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a God tile.

        Stub: returns empty list.

        Returns:
            Empty list.
        """
        return []

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a God tile.

        Returns:
            Empty list.
        """
        return []
