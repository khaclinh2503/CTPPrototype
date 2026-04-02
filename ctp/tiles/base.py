"""TileStrategy abstract base class for CTP game tiles."""

from abc import ABC, abstractmethod
from ctp.core.models import Player
from ctp.core.board import Tile, Board
from ctp.core.events import GameEvent


class TileStrategy(ABC):
    """Abstract base class for tile resolution strategies.

    Each tile type on the board has its own strategy that defines
    what happens when a player lands on or passes through that tile.
    """

    @abstractmethod
    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Resolve what happens when player lands on this tile.

        Args:
            player: The player who landed on the tile.
            tile: The tile they landed on.
            board: The game board (for accessing configs).
            event_bus: Event bus for publishing game events.

        Returns:
            List of GameEvents produced by this tile resolution.
        """
        pass

    @abstractmethod
    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Resolve what happens when player passes this tile (moving through it).

        Args:
            player: The player who passed through the tile.
            tile: The tile they passed.
            board: The game board (for accessing configs).
            event_bus: Event bus for publishing game events.

        Returns:
            List of GameEvents produced by passing this tile.
        """
        pass