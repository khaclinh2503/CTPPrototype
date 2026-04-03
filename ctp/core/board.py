"""Board, Tile, and SpaceId for CTP game."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class SpaceId(IntEnum):
    """Space types from Board.json spaceId field.

    Maps to the spaceId values in Board.json SpacePosition entries.
    Updated in Phase 2 to match actual game semantics.
    """

    FESTIVAL    = 1   # Festival/reward tile
    CHANCE      = 2   # Fortune/Event card (merged FORTUNE_CARD + FORTUNE_EVENT)
    CITY        = 3   # Land property tile (18 tiles on map 1)
    GAME        = 4   # Mini-game tile
    PRISON      = 5   # Prison tile
    RESORT      = 6   # Resort property tile
    START       = 7   # Start tile (unchanged)
    TAX         = 8   # Tax tile
    TRAVEL      = 9   # Travel/teleport tile
    GOD         = 10  # God tile (Map 2)
    WATER_SLIDE = 40  # Water slide tile (Map 3)


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
    is_golden: bool = False   # x2 toll khi check in
    visit_count: int = 0      # số lần người khác đã vào trả tiền (dùng cho resort đơn)
    festival_level: int = 0   # số lần ô này được chọn làm festival (1→2x, 2→3x, 3+→4x)


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
        prison_config: Optional[dict] = None,
        travel_config: Optional[dict] = None,
        map_id: int = 1,          # [NEW per D-02] 1=Map1, 2=Map2, 3=Map3
    ):
        """Initialize board from config data.

        Args:
            space_positions: Dict mapping position str (1-32) to space config.
                Example: {"1": {"spaceId": 7, "opt": 0}}
            land_config: LandSpace config dict, e.g., {"1": {"1": {...}}}
            resort_config: Optional ResortSpace config.
            festival_config: Optional FestivalSpace config.
            prison_config: Optional PrisonSpace config (escapeCostRate, limitTurns).
        """
        self.land_config = land_config
        self.resort_config = resort_config
        self.festival_config = festival_config
        self.prison_config = prison_config
        self.travel_config = travel_config
        self.map_id: int = map_id  # map_id để filter card mapNotAvail
        self.festival_level: int = 0
        self.festival_tile_position: int | None = None  # Ô đang tổ chức lễ hội
        self.elevated_tile: int | None = None  # chỉ 1 ô được nâng trên toàn map

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

    def get_prison_config(self) -> Optional[dict]:
        """Get prison space configuration (escapeCostRate, limitTurns)."""
        return self.prison_config

    def get_festival_config(self) -> Optional[dict]:
        """Get festival space configuration.

        Returns:
            Festival config dict or None if not configured.
        """
        return self.festival_config

    def find_nearest_tile_by_space_id(
        self, from_pos: int, space_id: SpaceId
    ) -> int | None:
        """Tìm tile gần nhất theo chiều tiến từ from_pos có space_id khớp.

        Tìm kiếm theo hướng tiến (forward), wrap-around, tìm trong tối đa 32 bước.
        Không tính ô from_pos chính nó.

        Args:
            from_pos: Vị trí xuất phát (1-32).
            space_id: Loại tile cần tìm (SpaceId enum).

        Returns:
            Position (1-32) của tile gần nhất, hoặc None nếu không có.
        """
        for steps in range(1, 33):
            candidate = ((from_pos - 1 + steps) % 32) + 1
            tile = self.get_tile(candidate)
            if tile.space_id == space_id:
                return candidate
        return None

    def get_color_group_positions(self, opt: int) -> list[int]:
        """Get all board positions of CITY tiles that share the same color as opt.

        Args:
            opt: Land tile opt index.

        Returns:
            List of tile positions (1-32) with the same color group.
        """
        map_cfg = self.land_config.get("1", {})
        target = map_cfg.get(str(opt), {})
        target_color = target.get("color")
        if target_color is None:
            return []

        same_color_opts = {
            int(o) for o, cfg in map_cfg.items() if cfg.get("color") == target_color
        }

        return [
            tile.position
            for tile in self.board
            if tile.space_id == SpaceId.CITY and tile.opt in same_color_opts
        ]

    def elevate_tile(self, position: int) -> bool:
        """Elevate a tile. Returns False if a tile is already elevated on the map."""
        if self.elevated_tile is not None:
            return False
        self.elevated_tile = position
        return True

    def lower_tile(self, position: int) -> None:
        """Lower an elevated tile (called when player is blocked by it)."""
        if self.elevated_tile == position:
            self.elevated_tile = None

    def is_elevated(self, position: int) -> bool:
        """Check if a tile is currently elevated."""
        return self.elevated_tile == position

    def find_elevated_in_path(self, old_pos: int, steps: int) -> int | None:
        """Find the first elevated tile in the movement path.

        Args:
            old_pos: Starting position (1-32).
            steps: Number of steps to move forward.

        Returns:
            Position of first elevated tile encountered, or None.
        """
        for i in range(1, steps + 1):
            pos = ((old_pos - 1 + i) % 32) + 1
            if self.is_elevated(pos):
                return pos
        return None