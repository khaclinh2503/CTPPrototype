"""Unit tests for ctp/skills/handlers_move.py.

Tests:
- CamCo: pass unowned CITY tile -> claims it, building_level stays 0
- CamCo: pass owned tile -> no effect
- CamCo: rate decay after 3 activations: rate drops by 1+3+5=9
- CamCo: does not fire during "teleport" movement_type
- PhaHuy: pass opponent CITY L3 -> tile becomes unowned L0, player gets 50% invested
- PhaHuy: does not fire on own property
- PhaHuy -> CamCo chain: PhaHuy destroys -> tile unowned -> CamCo claims
- check_traps: illusion stops movement, consumed after trigger
- check_traps: stop_sign stops movement, consumed after trigger
- check_traps: teleport movement_type bypasses traps
"""

import pytest
from unittest.mock import MagicMock, patch

from ctp.core.board import Board, Tile, SpaceId
from ctp.core.models import Player
from ctp.skills.handlers_move import handle_cam_co, handle_pha_huy, check_traps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(player_id: str = "P1", cash: float = 100_000, skills: list = None) -> Player:
    p = Player(player_id=player_id, cash=cash)
    p.skills = skills or []
    p.cam_co_current_rate = 100.0  # always activates in tests
    p.cam_co_decay_index = 0
    return p


def _make_city_tile(position: int = 5, owner_id: str = None, building_level: int = 0) -> Tile:
    t = Tile(position=position, space_id=SpaceId.CITY, opt=1)
    t.owner_id = owner_id
    t.building_level = building_level
    return t


def _make_resort_tile(position: int = 10, owner_id: str = None, building_level: int = 1) -> Tile:
    t = Tile(position=position, space_id=SpaceId.RESORT, opt=0)
    t.owner_id = owner_id
    t.building_level = building_level
    return t


def _make_mock_board(illusion_pos=None, stop_sign_pos=None, illusion_owner_id=None):
    board = MagicMock()
    board.illusion_position = illusion_pos
    board.stop_sign_position = stop_sign_pos
    board.illusion_owner_id = illusion_owner_id
    return board


# ---------------------------------------------------------------------------
# SK_CAM_CO tests
# ---------------------------------------------------------------------------

class TestHandleCamCo:
    """Tests for SK_CAM_CO (Cắm Cờ) handler."""

    def test_cam_co_claims_unowned_city_tile(self):
        """CamCo: pass unowned CITY tile -> claims it, building_level stays 0."""
        player = _make_player()
        tile = _make_city_tile(position=5, owner_id=None, building_level=0)
        ctx = {
            "tile": tile,
            "board": MagicMock(),
            "movement_type": "dice_walk",
            "players": [player],
        }
        cfg = MagicMock()

        result = handle_cam_co(player, ctx, cfg, engine=None)

        assert result is not None
        assert result["action"] == "cam_co_claimed"
        assert result["position"] == 5
        assert tile.owner_id == player.player_id
        assert tile.building_level == 0  # building_level stays 0
        assert 5 in player.owned_properties

    def test_cam_co_no_effect_on_owned_tile(self):
        """CamCo: pass owned tile (by someone) -> no effect."""
        player = _make_player()
        tile = _make_city_tile(position=5, owner_id="P2")
        ctx = {
            "tile": tile,
            "board": MagicMock(),
            "movement_type": "dice_walk",
            "players": [player],
        }
        cfg = MagicMock()

        result = handle_cam_co(player, ctx, cfg, engine=None)

        assert result is None
        assert tile.owner_id == "P2"  # unchanged

    def test_cam_co_rate_decay_after_3_activations(self):
        """CamCo: rate decay after 3 activations -> rate drops by 1+3+5=9."""
        player = _make_player()
        player.cam_co_current_rate = 50.0
        player.cam_co_decay_index = 0

        cfg = MagicMock()
        board = MagicMock()

        # Patch random so rate check always passes (returns 0 < any positive rate)
        with patch("ctp.skills.handlers_move.random.randint", return_value=0):
            # Activate 3 times on 3 different unowned CITY tiles
            for pos in [5, 6, 7]:
                tile = _make_city_tile(position=pos)
                ctx = {
                    "tile": tile,
                    "board": board,
                    "movement_type": "dice_walk",
                    "players": [player],
                }
                result = handle_cam_co(player, ctx, cfg, engine=None)
                assert result is not None  # each should activate

        # After 3 activations: decay = 1 + 3 + 5 = 9
        assert player.cam_co_current_rate == 50.0 - 9.0
        assert player.cam_co_decay_index == 3

    def test_cam_co_no_fire_during_teleport(self):
        """CamCo: does not fire during 'teleport' movement_type (D-57)."""
        player = _make_player()
        tile = _make_city_tile(position=5, owner_id=None)
        ctx = {
            "tile": tile,
            "board": MagicMock(),
            "movement_type": "teleport",
            "players": [player],
        }
        cfg = MagicMock()

        result = handle_cam_co(player, ctx, cfg, engine=None)

        assert result is None
        assert tile.owner_id is None  # not claimed

    def test_cam_co_fires_during_sweep_walk(self):
        """CamCo: fires during 'sweep_walk' (D-57)."""
        player = _make_player()
        tile = _make_city_tile(position=5)
        ctx = {
            "tile": tile,
            "board": MagicMock(),
            "movement_type": "sweep_walk",
            "players": [player],
        }
        cfg = MagicMock()

        result = handle_cam_co(player, ctx, cfg, engine=None)

        assert result is not None
        assert tile.owner_id == player.player_id


# ---------------------------------------------------------------------------
# SK_PHA_HUY tests
# ---------------------------------------------------------------------------

class TestHandlePhaHuy:
    """Tests for SK_PHA_HUY (Phá Hủy) handler."""

    def test_pha_huy_destroys_opponent_city_l3(self):
        """PhaHuy: pass opponent CITY L3 -> tile becomes unowned L0, player gets 50% invested."""
        player = _make_player(player_id="P1", cash=0)
        opponent = _make_player(player_id="P2", cash=500_000)
        tile = _make_city_tile(position=5, owner_id="P2", building_level=3)
        opponent.owned_properties = [5]

        board = MagicMock()
        # calc_invested_build_cost returns 60_000 for L3 tile
        with patch(
            "ctp.skills.handlers_move.calc_invested_build_cost", return_value=60_000
        ):
            ctx = {
                "tile": tile,
                "board": board,
                "movement_type": "dice_walk",
                "players": [player, opponent],
            }
            cfg = MagicMock()
            result = handle_pha_huy(player, ctx, cfg, engine=None)

        assert result is not None
        assert result["action"] == "pha_huy_destroyed"
        assert result["position"] == 5
        assert result["refund"] == 30_000  # 50% of 60_000
        assert player.cash == 30_000
        assert tile.building_level == 0
        assert tile.owner_id is None
        assert 5 not in opponent.owned_properties

    def test_pha_huy_no_effect_on_own_property(self):
        """PhaHuy: does not fire on own property."""
        player = _make_player(player_id="P1")
        tile = _make_city_tile(position=5, owner_id="P1")
        ctx = {
            "tile": tile,
            "board": MagicMock(),
            "movement_type": "dice_walk",
            "players": [player],
        }
        cfg = MagicMock()

        result = handle_pha_huy(player, ctx, cfg, engine=None)

        assert result is None
        assert tile.owner_id == "P1"  # unchanged

    def test_pha_huy_no_effect_during_teleport(self):
        """PhaHuy: does not fire during teleport movement_type (D-57)."""
        player = _make_player(player_id="P1")
        tile = _make_city_tile(position=5, owner_id="P2")
        ctx = {
            "tile": tile,
            "board": MagicMock(),
            "movement_type": "teleport",
            "players": [player],
        }
        cfg = MagicMock()

        result = handle_pha_huy(player, ctx, cfg, engine=None)

        assert result is None
        assert tile.owner_id == "P2"  # unchanged


# ---------------------------------------------------------------------------
# PhaHuy -> CamCo chain test
# ---------------------------------------------------------------------------

class TestPhaHuyCamCoChain:
    """Tests for PhaHuy -> CamCo chain behavior."""

    def test_pha_huy_to_cam_co_chain(self):
        """PhaHuy destroys opponent tile -> tile unowned -> CamCo claims it.

        After PhaHuy clears the tile, handle_pha_huy calls engine.fire("ON_MOVE_PASS")
        which triggers CamCo. We simulate by verifying the chain by calling directly.
        """
        player = _make_player(player_id="P1", cash=0, skills=["SK_PHA_HUY", "SK_CAM_CO"])
        player.cam_co_current_rate = 100.0  # always activates
        opponent = _make_player(player_id="P2", cash=0)
        tile = _make_city_tile(position=5, owner_id="P2", building_level=0)
        opponent.owned_properties = [5]

        board = MagicMock()

        # Mock engine that calls handle_cam_co directly for the ON_MOVE_PASS event
        mock_engine = MagicMock()
        ctx = {
            "tile": tile,
            "board": board,
            "movement_type": "dice_walk",
            "players": [player, opponent],
        }

        with patch("ctp.skills.handlers_move.calc_invested_build_cost", return_value=0):
            result = handle_pha_huy(player, ctx, cfg=MagicMock(), engine=mock_engine)

        assert result is not None
        assert result["action"] == "pha_huy_destroyed"
        # After PhaHuy: tile should be unowned
        assert tile.owner_id is None
        # Engine was called to fire ON_MOVE_PASS (which would trigger CamCo)
        mock_engine.fire.assert_called_once_with("ON_MOVE_PASS", player, ctx)

    def test_pha_huy_to_cam_co_chain_direct(self):
        """End-to-end chain: PhaHuy destroys, then CamCo directly claims same tile."""
        player = _make_player(player_id="P1", cash=0, skills=["SK_PHA_HUY", "SK_CAM_CO"])
        player.cam_co_current_rate = 100.0
        opponent = _make_player(player_id="P2", cash=0)
        tile = _make_city_tile(position=5, owner_id="P2", building_level=0)
        opponent.owned_properties = [5]

        board = MagicMock()

        # PhaHuy destroys tile -> unowned -> manually call CamCo to verify it works
        ctx = {
            "tile": tile,
            "board": board,
            "movement_type": "dice_walk",
            "players": [player, opponent],
        }

        with patch("ctp.skills.handlers_move.calc_invested_build_cost", return_value=0):
            handle_pha_huy(player, ctx, cfg=MagicMock(), engine=None)

        # Tile is now unowned — CamCo should be able to claim it
        assert tile.owner_id is None
        cam_result = handle_cam_co(player, ctx, cfg=MagicMock(), engine=None)
        assert cam_result is not None
        assert tile.owner_id == "P1"


# ---------------------------------------------------------------------------
# check_traps tests
# ---------------------------------------------------------------------------

class TestCheckTraps:
    """Tests for the check_traps() helper function."""

    def test_illusion_stops_movement_and_is_consumed(self):
        """check_traps: illusion stops movement and is consumed after trigger."""
        player = _make_player(player_id="P1")
        board = _make_mock_board(illusion_pos=5, illusion_owner_id="P2")

        should_stop, trap_type = check_traps(board, player, tile_position=5, movement_type="dice_walk")

        assert should_stop is True
        assert trap_type == "illusion"
        assert board.illusion_position is None  # consumed

    def test_stop_sign_stops_movement_and_is_consumed(self):
        """check_traps: stop_sign stops movement and is consumed after trigger."""
        player = _make_player(player_id="P1")
        board = _make_mock_board(stop_sign_pos=7)

        should_stop, trap_type = check_traps(board, player, tile_position=7, movement_type="dice_walk")

        assert should_stop is True
        assert trap_type == "stop_sign"
        assert board.stop_sign_position is None  # consumed

    def test_teleport_bypasses_traps(self):
        """check_traps: teleport movement_type bypasses all traps (D-55)."""
        player = _make_player(player_id="P1")
        board = _make_mock_board(illusion_pos=5, stop_sign_pos=5)

        should_stop, trap_type = check_traps(board, player, tile_position=5, movement_type="teleport")

        assert should_stop is False
        assert trap_type is None
        # Traps NOT consumed because immune
        assert board.illusion_position == 5
        assert board.stop_sign_position == 5

    def test_skill_walk_bypasses_traps(self):
        """check_traps: skill_walk movement_type bypasses all traps (D-55)."""
        player = _make_player(player_id="P1")
        board = _make_mock_board(illusion_pos=3, stop_sign_pos=3)

        should_stop, trap_type = check_traps(board, player, tile_position=3, movement_type="skill_walk")

        assert should_stop is False
        assert trap_type is None

    def test_illusion_does_not_affect_creator(self):
        """check_traps: illusion does NOT stop the player who placed it."""
        # Player P1 placed the illusion (illusion_owner_id = "P1")
        player = _make_player(player_id="P1")
        board = _make_mock_board(illusion_pos=5, illusion_owner_id="P1")

        should_stop, trap_type = check_traps(board, player, tile_position=5, movement_type="dice_walk")

        assert should_stop is False
        assert trap_type is None
        # Illusion not consumed (creator walked through)
        assert board.illusion_position == 5

    def test_no_traps_returns_false(self):
        """check_traps: no traps on tile -> returns (False, None)."""
        player = _make_player()
        board = _make_mock_board(illusion_pos=None, stop_sign_pos=None)

        should_stop, trap_type = check_traps(board, player, tile_position=5, movement_type="dice_walk")

        assert should_stop is False
        assert trap_type is None

    def test_travel_walk_susceptible_to_traps(self):
        """check_traps: travel_walk IS susceptible to traps (only teleport+skill_walk immune)."""
        player = _make_player(player_id="P1")
        board = _make_mock_board(stop_sign_pos=10, illusion_owner_id="P2")

        should_stop, trap_type = check_traps(board, player, tile_position=10, movement_type="travel_walk")

        assert should_stop is True
        assert trap_type == "stop_sign"
