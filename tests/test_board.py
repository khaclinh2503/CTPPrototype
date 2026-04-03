"""Tests for Board - Phase 02.1: map_id field and find_nearest_tile_by_space_id()."""

import json
import pytest
from pathlib import Path

from ctp.core.board import Board, SpaceId

CONFIG_DIR = Path(__file__).parent.parent / "ctp" / "config"


def _load_board() -> Board:
    """Load Board from Board.json config."""
    with open(CONFIG_DIR / "Board.json", encoding="utf-8") as f:
        data = json.load(f)
    space_positions = data["SpacePosition0"]
    land_config = data["LandSpace"]
    resort_config = data.get("ResortSpace")
    festival_config = data.get("FestivalSpace")
    prison_config = data.get("PrisonSpace")
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config,
        prison_config=prison_config,
    )


class TestBoardPhase021:
    """Tests for Board.map_id and find_nearest_tile_by_space_id() added in Phase 02.1."""

    def test_board_default_map_id(self):
        """Test 1: Board khởi tạo không có map_id arg → board.map_id == 1."""
        board = _load_board()
        assert board.map_id == 1

    def test_board_custom_map_id(self):
        """Test 2: Board khởi tạo với map_id=2 → board.map_id == 2."""
        with open(CONFIG_DIR / "Board.json", encoding="utf-8") as f:
            data = json.load(f)
        space_positions = data["SpacePosition0"]
        land_config = data["LandSpace"]
        board = Board(
            space_positions=space_positions,
            land_config=land_config,
            map_id=2,
        )
        assert board.map_id == 2

    def test_find_nearest_prison_from_pos_1(self):
        """Test 3: find_nearest_tile_by_space_id(from_pos=1, SpaceId.PRISON) → 9."""
        board = _load_board()
        result = board.find_nearest_tile_by_space_id(1, SpaceId.PRISON)
        assert result == 9

    def test_find_nearest_tax_from_pos_15(self):
        """Test 4: find_nearest_tile_by_space_id(from_pos=15, SpaceId.TAX) → 31."""
        board = _load_board()
        # TAX is at pos 31, going forward from 15 = 16 steps
        result = board.find_nearest_tile_by_space_id(15, SpaceId.TAX)
        assert result == 31

    def test_find_nearest_nonexistent_space_returns_none(self):
        """Test 5: find_nearest_tile_by_space_id với space_id không tồn tại → None."""
        board = _load_board()
        # GOD (10) và WATER_SLIDE (40) không có trên Map 1 SpacePosition0
        result = board.find_nearest_tile_by_space_id(1, SpaceId.GOD)
        assert result is None
