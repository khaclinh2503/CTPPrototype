"""Tests for pendant_handlers_own.py.

Tests:
- TuTruong R1: refund correct % of invested cost (always fires)
- TuTruong R2: pulls opponents within 4 tiles at L5
- TuTruong R2: does not fire at non-L5
- BanTayVang: pulls all opponents on same side at L5
- BanTayVang: skips opponent already at position (D-48)
- TuiBaGang E1: returns toll_boost with correct %
- TuiBaGang E2: steals correct % from same-tile opponents
- KetVang E1: returns toll_boost with correct %
- KetVang E2: refunds correct % of invested cost
- TuiBaGang E1 + KetVang E1 stack: total boost = sum of both %
"""

import pytest
from unittest.mock import MagicMock, patch

from ctp.core.models import Player
from ctp.core.board import Board, Tile, SpaceId
from ctp.skills.pendant_handlers_own import (
    handle_tu_truong,
    handle_ban_tay_vang,
    handle_tui_ba_gang,
    handle_ket_vang,
    PENDANT_HANDLERS,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_player(player_id: str = "P1", position: int = 5,
                 pendant_rank: str = "SR", cash: float = 100_000) -> Player:
    return Player(
        player_id=player_id,
        cash=cash,
        position=position,
        pendant_rank=pendant_rank,
    )


def _make_board_with_city_l5(position: int = 5) -> Board:
    """Create a minimal Board with one CITY tile at L5 at `position`."""
    space_positions = {str(p): {"spaceId": 3, "opt": 1} for p in range(1, 33)}
    # Make corners be START tiles to avoid confusion
    for corner in [1, 9, 17, 25]:
        space_positions[str(corner)] = {"spaceId": 7, "opt": 0}

    land_config = {
        "1": {
            "1": {
                "color": "red",
                "building": {
                    "1": {"build": 100},
                    "2": {"build": 200},
                    "3": {"build": 300},
                    "4": {"build": 400},
                    "5": {"build": 500},
                },
            }
        }
    }
    board = Board(space_positions, land_config)
    tile = board.get_tile(position)
    tile.building_level = 5
    tile.space_id = SpaceId.CITY
    return board


def _make_board_with_city_l3(position: int = 5) -> Board:
    """Create a Board with CITY tile at L3 (not L5)."""
    board = _make_board_with_city_l5(position)
    board.get_tile(position).building_level = 3
    return board


def _make_cfg():
    """Create a minimal mock config object."""
    cfg = MagicMock()
    cfg.always_active = True
    return cfg


# ---------------------------------------------------------------------------
# Tests: PT_TU_TRUONG
# ---------------------------------------------------------------------------

class TestTuTruong:
    def test_r1_refunds_correct_percent_sr_rank(self):
        """R1 at SR rank: refund 50% of invested build cost."""
        player = _make_player(pendant_rank="SR", cash=0)
        board = _make_board_with_city_l5(position=5)

        # At L5, invested = (100+200+300+400+500) * 1000 = 1_500_000
        ctx = {"board": board, "players": [], "trigger": "ON_LAND_OWN"}
        result = handle_tu_truong(player, ctx, _make_cfg(), None)

        assert result is not None
        assert "refund" in result
        expected_invested = (100 + 200 + 300 + 400 + 500) * 1000
        assert result["refund"] == pytest.approx(expected_invested * 0.50)
        assert player.cash == pytest.approx(expected_invested * 0.50)

    def test_r1_refunds_correct_percent_b_rank(self):
        """R1 at B rank: refund 4% of invested build cost."""
        player = _make_player(pendant_rank="B", cash=0)
        board = _make_board_with_city_l5(position=5)

        ctx = {"board": board, "players": [], "trigger": "ON_LAND_OWN"}
        result = handle_tu_truong(player, ctx, _make_cfg(), None)

        assert result is not None
        assert "refund" in result
        expected_invested = (100 + 200 + 300 + 400 + 500) * 1000
        assert result["refund"] == pytest.approx(expected_invested * 0.04)

    def test_r2_pulls_opponents_within_4_tiles_at_l5(self):
        """R2 at L5: opponent within 4 tiles is pulled."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        # Opponent at position 7 — distance 2 (within 4)
        opp = _make_player(player_id="P2", position=7)

        board = _make_board_with_city_l5(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            result = handle_tu_truong(player, ctx, _make_cfg(), None)

        assert opp.position == 5, "Opponent should be pulled to player position"
        assert result is not None
        assert "pulled" in result
        assert "P2" in result["pulled"]

    def test_r2_does_not_fire_at_non_l5(self):
        """R2 should NOT fire at non-L5 tile (building_level != 5)."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        opp = _make_player(player_id="P2", position=7)

        board = _make_board_with_city_l3(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        result = handle_tu_truong(player, ctx, _make_cfg(), None)

        # Opponent must not move (R2 didn't fire)
        assert opp.position == 7
        # Result may have refund (R1) but no 'pulled'
        assert "pulled" not in (result or {})

    def test_r2_skips_opponents_outside_4_tile_radius(self):
        """R2: opponent more than 4 tiles away should NOT be pulled."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        opp = _make_player(player_id="P2", position=12)  # distance = 7

        board = _make_board_with_city_l5(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            result = handle_tu_truong(player, ctx, _make_cfg(), None)

        assert opp.position == 12, "Opponent outside 4-tile radius should not move"

    def test_r2_skips_bankrupt_opponents(self):
        """R2: bankrupt opponents are skipped."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        opp = _make_player(player_id="P2", position=7)
        opp.is_bankrupt = True

        board = _make_board_with_city_l5(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            handle_tu_truong(player, ctx, _make_cfg(), None)

        assert opp.position == 7, "Bankrupt opponent should not be moved"


# ---------------------------------------------------------------------------
# Tests: PT_BAN_TAY_VANG
# ---------------------------------------------------------------------------

class TestBanTayVang:
    def test_pulls_all_opponents_on_same_side_at_l5(self):
        """BanTayVang: pulls all opponents on the same board side at L5."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        # Positions 2-8 (non-corners) are on the same side as position 5
        opp1 = _make_player(player_id="P2", position=3)
        opp2 = _make_player(player_id="P3", position=7)

        board = _make_board_with_city_l5(position=5)
        ctx = {"board": board, "players": [player, opp1, opp2], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            result = handle_ban_tay_vang(player, ctx, _make_cfg(), None)

        assert opp1.position == 5
        assert opp2.position == 5
        assert result is not None
        assert "pulled" in result
        assert set(result["pulled"]) == {"P2", "P3"}

    def test_skips_opponent_already_at_position_d48(self):
        """D-48: BanTayVang skips opponents already at player.position."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        opp = _make_player(player_id="P2", position=5)  # already at same tile

        board = _make_board_with_city_l5(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            result = handle_ban_tay_vang(player, ctx, _make_cfg(), None)

        # No pull should happen
        assert result is None or (result is not None and "P2" not in result.get("pulled", []))

    def test_does_not_fire_at_non_l5(self):
        """BanTayVang should NOT fire when building_level != 5."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        opp = _make_player(player_id="P2", position=3)

        board = _make_board_with_city_l3(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            result = handle_ban_tay_vang(player, ctx, _make_cfg(), None)

        assert result is None
        assert opp.position == 3

    def test_skips_opponents_on_different_side(self):
        """BanTayVang: opponents on a different board side are not pulled."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR")
        # Position 14 is on a different side (side 1: 9-17, side 0: 1-9)
        opp = _make_player(player_id="P2", position=14)

        board = _make_board_with_city_l5(position=5)
        ctx = {"board": board, "players": [player, opp], "trigger": "ON_LAND_OWN"}

        with patch("ctp.skills.pendant_handlers_own.random.randint", return_value=0):
            result = handle_ban_tay_vang(player, ctx, _make_cfg(), None)

        assert opp.position == 14, "Opponent on different side should not be pulled"


# ---------------------------------------------------------------------------
# Tests: PT_TUI_BA_GANG
# ---------------------------------------------------------------------------

class TestTuiBaGang:
    def test_e1_returns_toll_boost_sr_rank(self):
        """TuiBaGang E1: returns toll_boost dict with correct % at SR rank."""
        player = _make_player(pendant_rank="SR")
        ctx = {"trigger": "ON_OPPONENT_LAND_YOURS", "players": []}

        result = handle_tui_ba_gang(player, ctx, _make_cfg(), None)

        assert result is not None
        assert result["type"] == "toll_boost"
        assert result["percent"] == 60

    def test_e1_returns_toll_boost_b_rank(self):
        """TuiBaGang E1: correct toll_boost % at B rank."""
        player = _make_player(pendant_rank="B")
        ctx = {"trigger": "ON_OPPONENT_LAND_YOURS", "players": []}

        result = handle_tui_ba_gang(player, ctx, _make_cfg(), None)

        assert result is not None
        assert result["percent"] == 10

    def test_e2_steals_correct_percent_from_same_tile_opponent(self):
        """TuiBaGang E2: steals correct % from same-tile opponent."""
        player = _make_player(player_id="P1", position=5, pendant_rank="SR", cash=0)
        opp = _make_player(player_id="P2", position=5, cash=10_000)

        ctx = {
            "trigger": "ON_SAME_TILE",
            "players": [player, opp],
        }

        result = handle_tui_ba_gang(player, ctx, _make_cfg(), None)

        # SR rank: steal 36%
        expected_steal = 10_000 * 0.36
        assert result is not None
        assert result["type"] == "steal"
        assert result["stolen"] == pytest.approx(expected_steal)
        assert player.cash == pytest.approx(expected_steal)
        assert opp.cash == pytest.approx(10_000 - expected_steal)

    def test_e2_skips_opponents_on_different_tile(self):
        """TuiBaGang E2: does NOT steal from opponents at a different position."""
        player = _make_player(player_id="P1", position=5, cash=0)
        opp = _make_player(player_id="P2", position=8, cash=10_000)

        ctx = {"trigger": "ON_SAME_TILE", "players": [player, opp]}

        result = handle_tui_ba_gang(player, ctx, _make_cfg(), None)

        assert result is None
        assert opp.cash == 10_000


# ---------------------------------------------------------------------------
# Tests: PT_KET_VANG
# ---------------------------------------------------------------------------

class TestKetVang:
    def test_e1_returns_toll_boost_sr_rank(self):
        """KetVang E1: returns toll_boost dict with correct % at SR rank."""
        player = _make_player(pendant_rank="SR")
        ctx = {"trigger": "ON_OPPONENT_LAND_YOURS"}

        result = handle_ket_vang(player, ctx, _make_cfg(), None)

        assert result is not None
        assert result["type"] == "toll_boost"
        assert result["percent"] == 60

    def test_e1_returns_toll_boost_a_rank(self):
        """KetVang E1: correct toll_boost % at A rank."""
        player = _make_player(pendant_rank="A")
        ctx = {"trigger": "ON_OPPONENT_LAND_YOURS"}

        result = handle_ket_vang(player, ctx, _make_cfg(), None)

        assert result is not None
        assert result["percent"] == 20

    def test_e2_refunds_correct_percent_of_invested_cost(self):
        """KetVang E2: refunds correct % of invested build cost."""
        player = _make_player(pendant_rank="SR", cash=0)
        board = _make_board_with_city_l5(position=5)

        ctx = {"trigger": "ON_LAND_OWN", "board": board}

        result = handle_ket_vang(player, ctx, _make_cfg(), None)

        assert result is not None
        assert result["type"] == "refund"
        # SR rank: refund 60% of invested
        expected_invested = (100 + 200 + 300 + 400 + 500) * 1000
        assert result["amount"] == pytest.approx(expected_invested * 0.60)
        assert player.cash == pytest.approx(expected_invested * 0.60)

    def test_e2_refunds_b_rank(self):
        """KetVang E2: refunds 10% at B rank."""
        player = _make_player(pendant_rank="B", cash=0)
        board = _make_board_with_city_l5(position=5)

        ctx = {"trigger": "ON_LAND_OWN", "board": board}

        result = handle_ket_vang(player, ctx, _make_cfg(), None)

        expected_invested = (100 + 200 + 300 + 400 + 500) * 1000
        assert result["amount"] == pytest.approx(expected_invested * 0.10)


# ---------------------------------------------------------------------------
# Tests: Toll boost stacking (TuiBaGang E1 + KetVang E1)
# ---------------------------------------------------------------------------

class TestTollBoostStacking:
    def test_tui_ba_gang_and_ket_vang_e1_stack_additively(self):
        """TuiBaGang E1 + KetVang E1 toll_boost stacks additively (sum of both %)."""
        player = _make_player(pendant_rank="SR")
        ctx = {"trigger": "ON_OPPONENT_LAND_YOURS", "players": []}

        tbg_result = handle_tui_ba_gang(player, ctx, _make_cfg(), None)
        kv_result = handle_ket_vang(player, ctx, _make_cfg(), None)

        assert tbg_result is not None
        assert kv_result is not None

        # Both return toll_boost type
        assert tbg_result["type"] == "toll_boost"
        assert kv_result["type"] == "toll_boost"

        # Combined boost = sum of both %
        total_boost = tbg_result["percent"] + kv_result["percent"]
        assert total_boost == 60 + 60  # SR: 60 + 60 = 120

    def test_stacking_at_b_rank(self):
        """Stacking at B rank: TuiBaGang(10%) + KetVang(10%) = 20%."""
        player = _make_player(pendant_rank="B")
        ctx = {"trigger": "ON_OPPONENT_LAND_YOURS", "players": []}

        tbg_result = handle_tui_ba_gang(player, ctx, _make_cfg(), None)
        kv_result = handle_ket_vang(player, ctx, _make_cfg(), None)

        total = tbg_result["percent"] + kv_result["percent"]
        assert total == 10 + 10


# ---------------------------------------------------------------------------
# Tests: Handler registry
# ---------------------------------------------------------------------------

class TestHandlerRegistry:
    def test_all_4_handlers_registered(self):
        """All 4 pendant handlers are registered in PENDANT_HANDLERS."""
        # Import triggers the module-level registration
        from ctp.skills.pendant_handlers_own import PENDANT_HANDLERS  # noqa: F811
        assert "PT_TU_TRUONG" in PENDANT_HANDLERS
        assert "PT_BAN_TAY_VANG" in PENDANT_HANDLERS
        assert "PT_TUI_BA_GANG" in PENDANT_HANDLERS
        assert "PT_KET_VANG" in PENDANT_HANDLERS
