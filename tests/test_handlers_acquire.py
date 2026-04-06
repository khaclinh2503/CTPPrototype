"""Tests cho ACQUIRE-trigger skill handlers: SK_MC2 và SK_TRUM_DU_LICH.

Tests:
- MC2: claims random unowned CITY với đúng building_level
- MC2: không có unowned CITY -> trả về None (fail silently)
- TrumDuLich E1: claims random unowned CITY (giống MC2)
- MC2 + TrumDuLich E1 stack: MC2 claim trước, TrumDuLich claim tile khác
- TrumDuLich E2: trả về resort_acquisition tại Resort đối thủ
- TrumDuLich E2: fail silently khi player không đủ tiền
- TrumDuLich E2: toll đã trả trước, sau đó mới check skill (handler không tự trả toll)
"""

import pytest
from unittest.mock import patch

from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.core.constants import BASE_UNIT
from ctp.skills.handlers_acquire import (
    handle_mc2,
    handle_trum_du_lich,
    _claim_random_unowned_city,
    SKILL_HANDLERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def land_config():
    """LandSpace config với 3 CITY tiles (opt 1, 2, 3), mỗi tile có 1 building level."""
    return {
        "1": {
            "1": {
                "color": 1,
                "building": {
                    "1": {"build": 10, "toll": 1},
                    "2": {"build": 5, "toll": 3},
                },
            },
            "2": {
                "color": 1,
                "building": {
                    "1": {"build": 10, "toll": 1},
                    "2": {"build": 5, "toll": 3},
                },
            },
            "3": {
                "color": 2,
                "building": {
                    "1": {"build": 8, "toll": 1},
                    "2": {"build": 6, "toll": 4},
                },
            },
        }
    }


@pytest.fixture
def resort_config():
    """Resort config với initCost để tính acquisition price."""
    return {"initCost": 100, "tollRate": 0.05}


@pytest.fixture
def space_positions():
    """Board layout:
    - pos 1: START
    - pos 2,3,4: CITY (opt 1,2,3)
    - pos 5: RESORT (opt 101)
    - pos 6-32: CITY (opt 4-30, dùng opt 1 làm fallback)
    """
    positions = {}
    positions["1"] = {"spaceId": SpaceId.START, "opt": 0}
    positions["2"] = {"spaceId": SpaceId.CITY, "opt": 1}
    positions["3"] = {"spaceId": SpaceId.CITY, "opt": 2}
    positions["4"] = {"spaceId": SpaceId.CITY, "opt": 3}
    positions["5"] = {"spaceId": SpaceId.RESORT, "opt": 101}
    for i in range(6, 33):
        positions[str(i)] = {"spaceId": SpaceId.CITY, "opt": 1}  # reuse opt 1 config
    return positions


@pytest.fixture
def board(space_positions, land_config, resort_config):
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=None,
    )


@pytest.fixture
def player_a():
    return Player(player_id="A", cash=1_000_000, rank="S", star=5)


@pytest.fixture
def player_b():
    return Player(player_id="B", cash=1_000_000, rank="S", star=5)


def _make_cfg():
    """Stub cfg — không cần rate config trong unit test vì handlers không tự check rate."""
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.always_active = True
    return cfg


# ---------------------------------------------------------------------------
# Tests: SK_MC2
# ---------------------------------------------------------------------------

class TestHandleMC2:
    def test_claims_random_unowned_city_with_correct_level(self, board, player_a):
        """MC2 claim 1 CITY unowned với building_level = acquired_level."""
        # Đặt pos 2, 3, 4 là unowned (default)
        ctx = {
            "board": board,
            "acquired_level": 2,
            "excluded_positions": [],
        }
        # Force chọn tile pos=2
        with patch("ctp.skills.handlers_acquire.random.choice", return_value=board.get_tile(2)):
            result = handle_mc2(player_a, ctx, _make_cfg(), None)

        assert result is not None
        assert result["type"] == "city_claimed"
        assert result["skill"] == "SK_MC2"
        assert result["position"] == 2
        assert result["level"] == 2

        # Tile phải thuộc player_a
        tile = board.get_tile(2)
        assert tile.owner_id == "A"
        assert tile.building_level == 2
        assert 2 in player_a.owned_properties

    def test_no_unowned_city_returns_none(self, board, player_a, player_b):
        """MC2 fail silently khi không còn CITY trống."""
        # Đặt tất cả CITY tiles có chủ
        for tile in board.board:
            if tile.space_id == SpaceId.CITY:
                tile.owner_id = "B"

        ctx = {"board": board, "acquired_level": 1}
        result = handle_mc2(player_a, ctx, _make_cfg(), None)
        assert result is None

    def test_updates_excluded_positions_in_ctx(self, board, player_a):
        """MC2 phải thêm claimed tile vào ctx['excluded_positions'] để stack hoạt động."""
        ctx = {"board": board, "acquired_level": 1}
        with patch("ctp.skills.handlers_acquire.random.choice", return_value=board.get_tile(2)):
            result = handle_mc2(player_a, ctx, _make_cfg(), None)

        assert result is not None
        assert 2 in ctx.get("excluded_positions", [])


# ---------------------------------------------------------------------------
# Tests: SK_TRUM_DU_LICH E1 (ON_ACQUIRE)
# ---------------------------------------------------------------------------

class TestTrumDuLichE1:
    def test_claims_random_unowned_city(self, board, player_a):
        """TrumDuLich E1 claim 1 CITY unowned, giống MC2."""
        ctx = {
            "trigger": "ON_ACQUIRE",
            "board": board,
            "acquired_level": 3,
        }
        with patch("ctp.skills.handlers_acquire.random.choice", return_value=board.get_tile(3)):
            result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)

        assert result is not None
        assert result["type"] == "city_claimed"
        assert result["skill"] == "SK_TRUM_DU_LICH_E1"
        assert result["position"] == 3
        assert result["level"] == 3
        assert board.get_tile(3).owner_id == "A"

    def test_no_unowned_city_returns_none(self, board, player_a, player_b):
        """TrumDuLich E1 fail silently khi không còn CITY trống."""
        for tile in board.board:
            if tile.space_id == SpaceId.CITY:
                tile.owner_id = "B"

        ctx = {"trigger": "ON_ACQUIRE", "board": board, "acquired_level": 1}
        result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: MC2 + TrumDuLich E1 stack
# ---------------------------------------------------------------------------

class TestMC2TrumDuLichStack:
    def test_stack_mc2_claims_first_trum_du_lich_different_tile(self, board, player_a):
        """MC2 + TrumDuLich E1 stack: MC2 claim pos 2, TrumDuLich claim pos 3 (khác tile).

        MC2 cập nhật ctx['excluded_positions'] = [2]
        TrumDuLich E1 loại trừ pos 2, chọn pos 3.
        """
        ctx = {
            "board": board,
            "acquired_level": 1,
        }

        # MC2 fires trước: chọn pos=2
        with patch("ctp.skills.handlers_acquire.random.choice", return_value=board.get_tile(2)):
            mc2_result = handle_mc2(player_a, ctx, _make_cfg(), None)

        assert mc2_result is not None
        assert mc2_result["position"] == 2
        assert 2 in ctx.get("excluded_positions", [])

        # TrumDuLich E1 fires sau: pos=2 bị loại, chọn pos=3
        ctx["trigger"] = "ON_ACQUIRE"
        with patch("ctp.skills.handlers_acquire.random.choice", return_value=board.get_tile(3)):
            tdl_result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)

        assert tdl_result is not None
        assert tdl_result["position"] == 3
        assert tdl_result["position"] != mc2_result["position"]

        # Player sở hữu cả 2 tiles
        assert 2 in player_a.owned_properties
        assert 3 in player_a.owned_properties


# ---------------------------------------------------------------------------
# Tests: SK_TRUM_DU_LICH E2 (ON_LAND_RESORT)
# ---------------------------------------------------------------------------

class TestTrumDuLichE2:
    def test_returns_resort_acquisition_at_opponent_resort(self, board, player_a, player_b):
        """TrumDuLich E2 trả về resort_acquisition khi đứng tại Resort đối thủ."""
        resort_tile = board.get_tile(5)
        resort_tile.owner_id = "B"
        resort_tile.building_level = 1  # Đã xây để có initCost

        ctx = {
            "trigger": "ON_LAND_RESORT",
            "tile": resort_tile,
            "board": board,
            "players": [player_a, player_b],
        }

        result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)

        assert result is not None
        assert result["type"] == "resort_acquisition"
        assert result["skill"] == "SK_TRUM_DU_LICH_E2"
        assert result["tile_pos"] == 5
        # price = initCost * BASE_UNIT = 100 * 1000
        assert result["price"] == 100 * BASE_UNIT

    def test_fails_silently_when_player_cannot_afford(self, board, player_a, player_b):
        """TrumDuLich E2 fail silently khi player không đủ tiền."""
        resort_tile = board.get_tile(5)
        resort_tile.owner_id = "B"
        resort_tile.building_level = 1

        player_a.cash = 0  # Không đủ tiền

        ctx = {
            "trigger": "ON_LAND_RESORT",
            "tile": resort_tile,
            "board": board,
            "players": [player_a, player_b],
        }

        result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)
        assert result is None

    def test_toll_paid_first_handler_does_not_modify_cash(self, board, player_a, player_b):
        """TrumDuLich E2 handler không tự trả toll — toll đã được game engine xử lý trước.

        Handler chỉ trả về lệnh resort_acquisition; game engine sẽ thực hiện transfer.
        Player cash không thay đổi sau khi handler chạy.
        """
        resort_tile = board.get_tile(5)
        resort_tile.owner_id = "B"
        resort_tile.building_level = 1

        initial_cash = player_a.cash

        ctx = {
            "trigger": "ON_LAND_RESORT",
            "tile": resort_tile,
            "board": board,
            "players": [player_a, player_b],
        }

        result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)

        # Handler không tự trừ tiền — chỉ trả về lệnh cho engine xử lý
        assert player_a.cash == initial_cash
        assert result is not None
        assert result["type"] == "resort_acquisition"

    def test_does_not_trigger_on_own_resort(self, board, player_a):
        """TrumDuLich E2 không fire khi đứng tại Resort của chính mình."""
        resort_tile = board.get_tile(5)
        resort_tile.owner_id = "A"  # Của chính player_a

        ctx = {
            "trigger": "ON_LAND_RESORT",
            "tile": resort_tile,
            "board": board,
        }

        result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)
        assert result is None

    def test_does_not_trigger_on_unowned_resort(self, board, player_a):
        """TrumDuLich E2 không fire khi Resort chưa có chủ."""
        resort_tile = board.get_tile(5)
        resort_tile.owner_id = None

        ctx = {
            "trigger": "ON_LAND_RESORT",
            "tile": resort_tile,
            "board": board,
        }

        result = handle_trum_du_lich(player_a, ctx, _make_cfg(), None)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_sk_mc2_registered_in_skill_handlers(self):
        """SK_MC2 phải được đăng ký trong SKILL_HANDLERS."""
        assert "SK_MC2" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_MC2"] is handle_mc2

    def test_sk_trum_du_lich_registered_in_skill_handlers(self):
        """SK_TRUM_DU_LICH phải được đăng ký trong SKILL_HANDLERS."""
        assert "SK_TRUM_DU_LICH" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_TRUM_DU_LICH"] is handle_trum_du_lich
