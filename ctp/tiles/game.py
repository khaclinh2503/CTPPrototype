"""GameStrategy - MiniGame tile stub.

MiniGame full mechanics will be implemented in Plan 02.
For now, on_land returns an empty list (no-op stub).
"""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board
from ctp.core.events import GameEvent


class GameStrategy(TileStrategy):
    """Strategy for MiniGame tile (spaceId=4).

    Stub implementation — full mini-game logic (red/black 3-round betting)
    will be implemented in Plan 02.
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a mini-game tile.

        Stub: returns empty list (no effect yet).

        Returns:
            Empty list.
        """
        return []

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a mini-game tile.

        Returns:
            Empty list (no pass effect).
        """
        return []
