"""Game constants and helper functions for CTP."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctp.core.board import Board

BASE_UNIT: int = 1_000       # Multiplier for all config values
STARTING_CASH: int = 1_000_000  # BASE_UNIT * 1000


def calc_invested_build_cost(board: "Board", position: int) -> int:
    """Calculate total build cost already invested (levels 1..building_level).

    Returns the actual monetary value (already multiplied by BASE_UNIT).

    Args:
        board: The game board.
        position: Tile position (1-32).

    Returns:
        Total invested build cost in game currency units, or 0 if not applicable.
    """
    from ctp.core.board import SpaceId  # local import to avoid circular

    tile = board.get_tile(position)
    if tile.building_level == 0:
        return 0

    if tile.space_id == SpaceId.CITY:
        config = board.get_land_config(tile.opt)
        if not config:
            return 0
        building = config.get("building", {})
        total = 0
        for lvl in range(1, tile.building_level + 1):
            level_data = building.get(str(lvl), {})
            total += level_data.get("build", 0)
        return total * BASE_UNIT

    if tile.space_id == SpaceId.RESORT:
        resort_config = board.get_resort_config()
        if not resort_config:
            return 0
        return resort_config.get("initCost", 0) * BASE_UNIT

    return 0
