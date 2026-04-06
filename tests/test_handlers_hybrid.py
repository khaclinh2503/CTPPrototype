"""Tests for SK_AO_ANH and SK_BIEN_CAM hybrid skill handlers.

Tests:
- AoAnh: sets board.illusion_position on upgrade (any level)
- AoAnh: sets board.illusion_position on landing at own L5
- AoAnh: new illusion overwrites previous (even from other player)
- AoAnh: does not trigger on landing at non-owned tile
- AoAnh: does not trigger on landing at own tile that is not L5
- BienCam: only triggers on L5 upgrade (not L3, L4)
- BienCam: only triggers on landing at own L5
- BienCam: new stop_sign overwrites previous
- BienCam: affects creator too (unlike illusion — no illusion_owner_id set)
"""

import pytest
from unittest.mock import MagicMock

from ctp.skills.handlers_hybrid import handle_ao_anh, handle_bien_cam
from ctp.core.models import Player
from ctp.core.board import Tile, SpaceId


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(player_id="p1", rank="A", star=3) -> Player:
    p = Player(player_id, 1_000_000)
    p.rank = rank
    p.star = star
    return p


def _make_board():
    """Create a minimal mock Board with illusion_position and stop_sign_position."""
    board = MagicMock()
    board.illusion_position = None
    board.illusion_owner_id = None
    board.stop_sign_position = None
    # Minimal board.board for _choose_stop_sign_position
    board.board = []
    return board


def _make_tile(position=5, owner_id=None, building_level=0) -> Tile:
    return Tile(
        position=position,
        space_id=SpaceId.CITY,
        opt=1,
        owner_id=owner_id,
        building_level=building_level,
    )


def _make_cfg():
    cfg = MagicMock()
    return cfg


# ---------------------------------------------------------------------------
# SK_AO_ANH tests
# ---------------------------------------------------------------------------

class TestAoAnh:

    def test_sets_illusion_on_upgrade(self):
        """AoAnh: ON_UPGRADE any level sets board.illusion_position."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=7, owner_id="p1", building_level=3)
        ctx = {"trigger": "ON_UPGRADE", "tile": tile, "board": board}

        result = handle_ao_anh(player, ctx, _make_cfg(), None)

        assert result is not None
        assert board.illusion_position == 7
        assert board.illusion_owner_id == "p1"
        assert result["illusion_position"] == 7

    def test_sets_illusion_on_land_own_L5(self):
        """AoAnh: ON_LAND at own L5 sets board.illusion_position."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=10, owner_id="p1", building_level=5)
        ctx = {"trigger": "ON_LAND", "tile": tile, "board": board}

        result = handle_ao_anh(player, ctx, _make_cfg(), None)

        assert result is not None
        assert board.illusion_position == 10
        assert board.illusion_owner_id == "p1"

    def test_overwrites_previous_illusion_from_other_player(self):
        """AoAnh: new illusion overwrites old one regardless of who placed it."""
        player = _make_player("p1")
        board = _make_board()
        board.illusion_position = 3   # previously placed by someone else
        board.illusion_owner_id = "p2"
        tile = _make_tile(position=8, owner_id="p1", building_level=5)
        ctx = {"trigger": "ON_UPGRADE", "tile": tile, "board": board}

        result = handle_ao_anh(player, ctx, _make_cfg(), None)

        assert board.illusion_position == 8   # overwritten
        assert board.illusion_owner_id == "p1"

    def test_does_not_trigger_on_land_non_owned_tile(self):
        """AoAnh: ON_LAND at tile not owned by player returns None."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=5, owner_id="p2", building_level=5)
        ctx = {"trigger": "ON_LAND", "tile": tile, "board": board}

        result = handle_ao_anh(player, ctx, _make_cfg(), None)

        assert result is None
        assert board.illusion_position is None

    def test_does_not_trigger_on_land_own_tile_not_L5(self):
        """AoAnh: ON_LAND at own tile with building_level < 5 returns None."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=5, owner_id="p1", building_level=4)
        ctx = {"trigger": "ON_LAND", "tile": tile, "board": board}

        result = handle_ao_anh(player, ctx, _make_cfg(), None)

        assert result is None
        assert board.illusion_position is None


# ---------------------------------------------------------------------------
# SK_BIEN_CAM tests
# ---------------------------------------------------------------------------

class TestBienCam:

    def test_only_triggers_on_L5_upgrade(self):
        """BienCam: ON_UPGRADE to L5 places stop sign."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=6, owner_id="p1", building_level=5)
        choose_fn = lambda b: 12  # stub returns position 12
        ctx = {
            "trigger": "ON_UPGRADE",
            "tile": tile,
            "board": board,
            "new_level": 5,
            "choose_fn": choose_fn,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        assert result is not None
        assert board.stop_sign_position == 12
        assert result["stop_sign_position"] == 12

    def test_does_not_trigger_on_L3_upgrade(self):
        """BienCam: ON_UPGRADE to L3 returns None."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=6, owner_id="p1", building_level=3)
        ctx = {
            "trigger": "ON_UPGRADE",
            "tile": tile,
            "board": board,
            "new_level": 3,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        assert result is None
        assert board.stop_sign_position is None

    def test_does_not_trigger_on_L4_upgrade(self):
        """BienCam: ON_UPGRADE to L4 returns None."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=6, owner_id="p1", building_level=4)
        ctx = {
            "trigger": "ON_UPGRADE",
            "tile": tile,
            "board": board,
            "new_level": 4,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        assert result is None

    def test_triggers_on_land_own_L5(self):
        """BienCam: ON_LAND at own L5 places stop sign."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=14, owner_id="p1", building_level=5)
        choose_fn = lambda b: 20
        ctx = {
            "trigger": "ON_LAND",
            "tile": tile,
            "board": board,
            "choose_fn": choose_fn,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        assert result is not None
        assert board.stop_sign_position == 20

    def test_does_not_trigger_on_land_non_own_L5(self):
        """BienCam: ON_LAND at L5 owned by someone else returns None."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=14, owner_id="p2", building_level=5)
        ctx = {
            "trigger": "ON_LAND",
            "tile": tile,
            "board": board,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        assert result is None

    def test_new_stop_sign_overwrites_previous(self):
        """BienCam: placing new stop sign overwrites existing one."""
        player = _make_player("p1")
        board = _make_board()
        board.stop_sign_position = 5  # already placed by someone
        tile = _make_tile(position=7, owner_id="p1", building_level=5)
        choose_fn = lambda b: 18
        ctx = {
            "trigger": "ON_UPGRADE",
            "tile": tile,
            "board": board,
            "new_level": 5,
            "choose_fn": choose_fn,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        assert board.stop_sign_position == 18   # overwritten

    def test_stop_sign_affects_creator_no_immunity_field(self):
        """BienCam: handler does not set stop_sign_owner_id (affects everyone including creator)."""
        player = _make_player("p1")
        board = _make_board()
        tile = _make_tile(position=7, owner_id="p1", building_level=5)
        choose_fn = lambda b: 7
        ctx = {
            "trigger": "ON_UPGRADE",
            "tile": tile,
            "board": board,
            "new_level": 5,
            "choose_fn": choose_fn,
            "players": [],
        }

        result = handle_bien_cam(player, ctx, _make_cfg(), None)

        # Handler returns result with only stop_sign_position (no owner_id = no immunity)
        assert result is not None
        assert "stop_sign_position" in result
        assert "stop_sign_owner_id" not in result  # no immunity field in return value
        assert board.stop_sign_position == 7
