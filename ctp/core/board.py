"""Board, Tile, and SpaceId for CTP game."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class SpaceId(IntEnum):
    """Space types from Board.json spaceId field.

    Maps to the spaceId values in Board.json SpacePosition entries.
    """

    TAX = 1
    FORTUNE_CARD = 2  # Fortune tile (card draw)
    LAND = 3
    PRISON = 4
    FESTIVAL = 5
    FORTUNE_EVENT = 6  # Fortune tile (event variant, opt=101/102)
    START = 7
    TRAVEL = 8
    RESORT = 9


@dataclass
class Tile:
    """A single tile on the game board.

    Attributes:
        position: Tile position (1-32).
        space_id: Type of space (SpaceId enum).
        opt: Type-specific index (e.g., land index for LAND tiles).
        owner_id: Player ID who owns this tile (None if unowned).
        building_level: Building level (0 for non-land, 1-5 for land).
    """

    position: int
    space_id: SpaceId
    opt: int
    owner_id: Optional[str] = None
    building_level: int = 0


class Board:
    """Game board with 32 tiles.

    The board is constructed from SpacePosition0 dict and the LandSpace
    configuration. Each tile represents a position on the game board.

    Attributes:
        board: List of 32 Tile objects (index 0 = position 1).
        festival_level: Current festival level (affects rent multiplier).
    """

    def __init__(
        self,
        space_positions: dict[str, dict],
        land_config: dict,
        resort_config: Optional[dict] = None,
        festival_config: Optional[dict] = None,
    ):
        """Initialize board from config data.

        Args:
            space_positions: Dict mapping position str (1-32) to space config.
                Example: {"1": {"spaceId": 7, "opt": 0}}
            land_config: LandSpace config dict, e.g., {"1": {"1": {...}}}
            resort_config: Optional ResortSpace config.
            festival_config: Optional FestivalSpace config.
        """
        self.land_config = land_config
        self.resort_config = resort_config
        self.festival_config = festival_config
        self.festival_level: int = 0

        # Build 32 tiles from SpacePosition0
        self.board: list[Tile] = []
        for pos in range(1, 33):
            pos_str = str(pos)
            if pos_str in space_positions:
                entry = space_positions[pos_str]
                space_id = SpaceId(entry["spaceId"])
                opt = entry["opt"]
                tile = Tile(position=pos, space_id=space_id, opt=opt)
                self.board.append(tile)
            else:
                raise ValueError(f"Missing position {pos} in space_positions")

    def get_tile(self, position: int) -> Tile:
        """Get tile at given position (1-indexed).

        Args:
            position: Tile position (1-32).

        Returns:
            Tile at that position.
        """
        if not 1 <= position <= 32:
            raise ValueError(f"Position must be 1-32, got {position}")
        return self.board[position - 1]

    def get_land_config(self, opt: int) -> Optional[dict]:
        """Get land configuration for a given opt index.

        Args:
            opt: Land tile index (1-18 for map 1).

        Returns:
            Land config dict or None if not found.
        """
        map_id = "1"  # SpacePosition0 is map index 0 -> mapId "1"
        if map_id in self.land_config:
            return self.land_config[map_id].get(str(opt))
        return None

    def get_resort_config(self) -> Optional[dict]:
        """Get resort space configuration.

        Returns:
            Resort config dict or None if not configured.
        """
        return self.resort_config

    def get_festival_config(self) -> Optional[dict]:
        """Get festival space configuration.

        Returns:
            Festival config dict or None if not configured.
        """
        return self.festival_config