"""Tests for pendant_handlers_land.py.

Pendants: PT_GIAY_BAY, PT_CUOP_NHA, PT_MANG_NHEN, PT_SIEU_TAXI.

Tests:
- GiayBay: waives toll + moves to Travel tile
- GiayBay: does NOT fire when not player's turn (D-51)
- GiayBay: sets giay_bay_active flag in ctx
- CuopNha: steals property after toll
- CuopNha: not blocked by ChongMuaNha (stealing != acquisition)
- CuopNha: does NOT fire when not player's turn (D-51)
- MangNhen R1: free toll
- MangNhen R2: steal property (independent of R1)
- MangNhen: both R1 + R2 active simultaneously
- SieuTaxi R1: instant travel from Travel tile
- SieuTaxi R2: free toll when GiayBay not active
- SieuTaxi R2: skipped when GiayBay already active
- D-45 priority: free toll pendants checked before boost pendants
- SieuTaxi R2: fires regardless of is_player_turn (D-52)
"""

import pytest
from unittest.mock import patch

from ctp.core.models import Player
from ctp.core.board import Board, SpaceId, Tile
from ctp.config.schemas import PendantEntry, PendantRankRates
from ctp.skills.pendant_handlers_land import (
    handle_giay_bay,
    handle_cuop_nha,
    handle_mang_nhen,
    handle_sieu_taxi,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_player(player_id: str = "p1", cash: float = 1_000_000,
                 pendant_rank: str = "SR") -> Player:
    p = Player(player_id=player_id, cash=cash)
    p.pendant_rank = pendant_rank
    return p


def _make_pendant_cfg(pendant_id: str, triggers: list[str],
                      rates: dict, rates_2: dict | None = None) -> PendantEntry:
    rank_rates = PendantRankRates(**rates)
    rank_rates_2 = PendantRankRates(**rates_2) if rates_2 else None
    return PendantEntry(
        id=pendant_id,
        name=pendant_id,
        triggers=triggers,
        rank_rates=rank_rates,
        rank_rates_2=rank_rates_2,
    )


def _make_tile(position: int, space_id: SpaceId = SpaceId.CITY,
               owner_id: str | None = None, building_level: int = 2) -> Tile:
    tile = Tile(position=position, space_id=space_id, opt=1)
    tile.owner_id = owner_id
    tile.building_level = building_level
    return tile


def _make_board_with_travel(travel_positions: list[int] | None = None) -> Board:
    """Tạo board giả với 32 tiles, đặt TRAVEL tiles tại các vị trí cho trước."""
    # Sử dụng Board giả không cần config thật
    # Tạo mock board chỉ với board.board attribute
    class MockBoard:
        def __init__(self):
            self.board = []
            for pos in range(1, 33):
                space_id = SpaceId.TRAVEL if (travel_positions and pos in travel_positions) else SpaceId.CITY
                tile = Tile(position=pos, space_id=space_id, opt=1)
                self.board.append(tile)

    return MockBoard()


_GIAY_BAY_CFG = _make_pendant_cfg(
    "PT_GIAY_BAY",
    ["ON_LAND_OPPONENT_WITH_TOLL"],
    {"B": 1, "A": 3, "S": 5, "R": 10, "SR": 100},  # SR=100 để test
)

_CUOP_NHA_CFG = _make_pendant_cfg(
    "PT_CUOP_NHA",
    ["ON_LAND_OPPONENT"],
    {"B": 5, "A": 7, "S": 10, "R": 15, "SR": 100},
)

_MANG_NHEN_CFG = _make_pendant_cfg(
    "PT_MANG_NHEN",
    ["ON_LAND_OPPONENT"],
    {"B": 3, "A": 5, "S": 8, "R": 20, "SR": 100},   # R1 rates
    {"B": 5, "A": 7, "S": 10, "R": 15, "SR": 100},  # R2 rates
)

_SIEU_TAXI_CFG = _make_pendant_cfg(
    "PT_SIEU_TAXI",
    ["ON_LAND_TRAVEL", "ON_LAND_OPPONENT"],
    {"B": 30, "A": 40, "S": 50, "R": 66, "SR": 100},   # R1 rates
    {"B": 3, "A": 5, "S": 8, "R": 20, "SR": 100},       # R2 rates
)


# ---------------------------------------------------------------------------
# PT_GIAY_BAY tests
# ---------------------------------------------------------------------------

class TestGiayBay:
    """Tests cho PT_GIAY_BAY pendant handler."""

    def test_giay_bay_waives_toll_and_moves_to_travel(self):
        """GiayBay active: waive toll + teleport đến Travel tile."""
        player = _make_player(pendant_rank="SR")
        board = _make_board_with_travel([5, 15])
        opponent = _make_player("p2")
        tile = _make_tile(8, SpaceId.CITY, owner_id="p2")
        ctx = {
            "is_player_turn": True,
            "board": board,
            "players": [player, opponent],
            "tile": tile,
        }

        with patch("random.randint", return_value=50):  # 50 < 100 -> active
            result = handle_giay_bay(player, ctx, _GIAY_BAY_CFG, None)

        assert result is not None
        assert result["type"] == "toll_waive_and_travel"
        assert result["travel_pos"] in [5, 15]

    def test_giay_bay_does_not_fire_when_not_player_turn(self):
        """D-51: GiayBay KHÔNG fire khi không phải lượt player."""
        player = _make_player(pendant_rank="SR")
        board = _make_board_with_travel([5])
        ctx = {
            "is_player_turn": False,
            "board": board,
            "players": [player],
        }

        result = handle_giay_bay(player, ctx, _GIAY_BAY_CFG, None)
        assert result is None

    def test_giay_bay_sets_active_flag_in_ctx(self):
        """GiayBay active phải set ctx['giay_bay_active'] = True."""
        player = _make_player(pendant_rank="SR")
        board = _make_board_with_travel([5])
        ctx = {
            "is_player_turn": True,
            "board": board,
            "players": [player],
        }

        with patch("random.randint", return_value=0):  # active
            handle_giay_bay(player, ctx, _GIAY_BAY_CFG, None)

        assert ctx.get("giay_bay_active") is True

    def test_giay_bay_only_toll_waive_when_no_travel_tile(self):
        """Nếu không có Travel tile: chỉ miễn toll, không teleport."""
        player = _make_player(pendant_rank="SR")
        board = _make_board_with_travel([])  # không có Travel tile
        ctx = {
            "is_player_turn": True,
            "board": board,
            "players": [player],
        }

        with patch("random.randint", return_value=0):  # active
            result = handle_giay_bay(player, ctx, _GIAY_BAY_CFG, None)

        assert result is not None
        assert result["type"] == "toll_waive"

    def test_giay_bay_fails_rate_check_returns_none(self):
        """GiayBay không active: trả về None."""
        player = _make_player(pendant_rank="B")  # rate=1
        board = _make_board_with_travel([5])
        ctx = {
            "is_player_turn": True,
            "board": board,
            "players": [player],
        }

        with patch("random.randint", return_value=99):  # 99 >= 1 -> not active
            result = handle_giay_bay(player, ctx, _GIAY_BAY_CFG, None)

        assert result is None


# ---------------------------------------------------------------------------
# PT_CUOP_NHA tests
# ---------------------------------------------------------------------------

class TestCuopNha:
    """Tests cho PT_CUOP_NHA pendant handler."""

    def test_cuop_nha_steals_property_after_toll(self):
        """CuopNha active: đổi owner_id của tile và cập nhật owned_properties."""
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(8)
        tile = _make_tile(8, SpaceId.CITY, owner_id="p2", building_level=3)
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        with patch("random.randint", return_value=0):  # active
            result = handle_cuop_nha(player, ctx, _CUOP_NHA_CFG, None)

        assert result is not None
        assert result["type"] == "property_stolen"
        assert result["position"] == 8
        assert tile.owner_id == "p1"
        assert 8 in player.owned_properties
        assert 8 not in opponent.owned_properties

    def test_cuop_nha_building_level_preserved(self):
        """CuopNha: building level được giữ nguyên (CITY)."""
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(10)
        tile = _make_tile(10, SpaceId.CITY, owner_id="p2", building_level=5)
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        with patch("random.randint", return_value=0):
            handle_cuop_nha(player, ctx, _CUOP_NHA_CFG, None)

        assert tile.building_level == 5  # giữ nguyên

    def test_cuop_nha_not_blocked_by_chong_mua_nha(self):
        """CuopNha không bị block bởi PT_CHONG_MUA_NHA (cướp != mua)."""
        # Pendant CuopNha không có logic check acquisition_blocked
        # Bài test này xác nhận handler không kiểm tra acquisition_blocked_turns
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(6)
        tile = _make_tile(6, SpaceId.CITY, owner_id="p2")
        tile.acquisition_blocked_turns = 5  # PT_XI_CHO block
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        with patch("random.randint", return_value=0):  # active
            result = handle_cuop_nha(player, ctx, _CUOP_NHA_CFG, None)

        # CuopNha vẫn thực hiện dù acquisition_blocked_turns > 0
        assert result is not None
        assert result["type"] == "property_stolen"

    def test_cuop_nha_does_not_fire_when_not_player_turn(self):
        """D-51: CuopNha KHÔNG fire khi không phải lượt player."""
        player = _make_player(pendant_rank="SR")
        tile = _make_tile(8, owner_id="p2")
        ctx = {
            "is_player_turn": False,
            "tile": tile,
            "players": [player],
        }

        result = handle_cuop_nha(player, ctx, _CUOP_NHA_CFG, None)
        assert result is None

    def test_cuop_nha_resort_only_changes_owner_id(self):
        """CuopNha trên RESORT: chỉ đổi owner_id, không thay level (D-28)."""
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(20)
        tile = _make_tile(20, SpaceId.RESORT, owner_id="p2", building_level=0)
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        with patch("random.randint", return_value=0):
            result = handle_cuop_nha(player, ctx, _CUOP_NHA_CFG, None)

        assert result is not None
        assert tile.owner_id == "p1"
        assert tile.building_level == 0  # không thay đổi


# ---------------------------------------------------------------------------
# PT_MANG_NHEN tests
# ---------------------------------------------------------------------------

class TestMangNhen:
    """Tests cho PT_MANG_NHEN pendant handler — dual-rate."""

    def test_mang_nhen_r1_free_toll(self):
        """MangNhen R1 active: trả về toll_waived=True."""
        player = _make_player(pendant_rank="SR")
        opponent = _make_player("p2")
        tile = _make_tile(8, SpaceId.CITY, owner_id="p2")
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        # R1 active (random=0 < 100), R2 not active (random=99 >= 100... giả sử)
        call_count = [0]
        def fake_randint(a, b):
            call_count[0] += 1
            if call_count[0] == 1:
                return 0   # R1 active
            return 99  # R2 not active

        with patch("random.randint", side_effect=fake_randint):
            result = handle_mang_nhen(player, ctx, _MANG_NHEN_CFG, None)

        assert result is not None
        assert result.get("toll_waived") is True

    def test_mang_nhen_r2_steal_property(self):
        """MangNhen R2 active (R1 not active): cướp property."""
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(8)
        tile = _make_tile(8, SpaceId.CITY, owner_id="p2")
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        call_count = [0]
        def fake_randint(a, b):
            call_count[0] += 1
            if call_count[0] == 1:
                return 99  # R1 not active
            return 0   # R2 active

        with patch("random.randint", side_effect=fake_randint):
            result = handle_mang_nhen(player, ctx, _MANG_NHEN_CFG, None)

        assert result is not None
        assert result.get("property_stolen") == 8
        assert tile.owner_id == "p1"

    def test_mang_nhen_both_r1_and_r2_active(self):
        """MangNhen: cả R1 và R2 cùng active — toll waived VÀ property stolen."""
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(8)
        tile = _make_tile(8, SpaceId.CITY, owner_id="p2")
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        with patch("random.randint", return_value=0):  # cả hai active
            result = handle_mang_nhen(player, ctx, _MANG_NHEN_CFG, None)

        assert result is not None
        assert result.get("toll_waived") is True
        assert result.get("property_stolen") == 8
        assert tile.owner_id == "p1"

    def test_mang_nhen_r1_and_r2_independent(self):
        """MangNhen R1 và R2 check độc lập — R2 check dù R1 không active."""
        player = _make_player("p1", pendant_rank="SR")
        opponent = _make_player("p2")
        opponent.add_property(8)
        tile = _make_tile(8, SpaceId.CITY, owner_id="p2")
        ctx = {
            "is_player_turn": True,
            "tile": tile,
            "players": [player, opponent],
        }

        # R1 fail, R2 active
        call_count = [0]
        def fake_randint(a, b):
            call_count[0] += 1
            if call_count[0] == 1:
                return 99  # R1 not active
            return 0   # R2 active

        with patch("random.randint", side_effect=fake_randint):
            result = handle_mang_nhen(player, ctx, _MANG_NHEN_CFG, None)

        # R2 check vẫn xảy ra dù R1 không active
        assert call_count[0] == 2  # cả hai rate đều được check
        assert result is not None

    def test_mang_nhen_does_not_fire_when_not_player_turn(self):
        """D-51: MangNhen KHÔNG fire khi không phải lượt player."""
        player = _make_player(pendant_rank="SR")
        tile = _make_tile(8, owner_id="p2")
        ctx = {
            "is_player_turn": False,
            "tile": tile,
            "players": [player],
        }

        result = handle_mang_nhen(player, ctx, _MANG_NHEN_CFG, None)
        assert result is None


# ---------------------------------------------------------------------------
# PT_SIEU_TAXI tests
# ---------------------------------------------------------------------------

class TestSieuTaxi:
    """Tests cho PT_SIEU_TAXI pendant handler — dual trigger."""

    def test_sieu_taxi_r1_instant_travel_from_travel_tile(self):
        """SieuTaxi R1 active trên Travel tile: instant travel đến tile khác."""
        player = _make_player(pendant_rank="SR")
        player.position = 5
        board = _make_board_with_travel([5])
        ctx = {
            "trigger": "ON_LAND_TRAVEL",
            "is_player_turn": True,
            "board": board,
            "players": [player],
        }

        with patch("random.randint", return_value=0):  # active
            result = handle_sieu_taxi(player, ctx, _SIEU_TAXI_CFG, None)

        assert result is not None
        assert result["type"] == "instant_travel"
        assert "destination" in result
        assert result["destination"] != player.position  # đến tile khác

    def test_sieu_taxi_r2_free_toll_when_giay_bay_not_active(self):
        """SieuTaxi R2: free toll khi GiayBay CHƯA active."""
        player = _make_player(pendant_rank="SR")
        ctx = {
            "trigger": "ON_LAND_OPPONENT",
            "is_player_turn": True,
            "players": [player],
            # giay_bay_active không có trong ctx
        }

        with patch("random.randint", return_value=0):  # active
            result = handle_sieu_taxi(player, ctx, _SIEU_TAXI_CFG, None)

        assert result is not None
        assert result["type"] == "toll_waive"

    def test_sieu_taxi_r2_skipped_when_giay_bay_active(self):
        """D-45 priority: SieuTaxi R2 KHÔNG check khi GiayBay đã active."""
        player = _make_player(pendant_rank="SR")
        ctx = {
            "trigger": "ON_LAND_OPPONENT",
            "is_player_turn": True,
            "players": [player],
            "giay_bay_active": True,  # GiayBay đã active trước đó
        }

        with patch("random.randint", return_value=0):  # không quan trọng
            result = handle_sieu_taxi(player, ctx, _SIEU_TAXI_CFG, None)

        assert result is None

    def test_sieu_taxi_r2_fires_regardless_of_turn(self):
        """D-52: SieuTaxi R2 fire bất kể is_player_turn (kể cả khi bị kéo bởi skill đối thủ)."""
        player = _make_player(pendant_rank="SR")
        ctx = {
            "trigger": "ON_LAND_OPPONENT",
            "is_player_turn": False,  # không phải lượt player
            "players": [player],
        }

        with patch("random.randint", return_value=0):  # active
            result = handle_sieu_taxi(player, ctx, _SIEU_TAXI_CFG, None)

        assert result is not None
        assert result["type"] == "toll_waive"

    def test_sieu_taxi_r1_fails_rate_check(self):
        """SieuTaxi R1 không active: trả về None."""
        player = _make_player(pendant_rank="B")  # rate=30
        board = _make_board_with_travel([5])
        ctx = {
            "trigger": "ON_LAND_TRAVEL",
            "is_player_turn": True,
            "board": board,
            "players": [player],
        }

        with patch("random.randint", return_value=99):  # 99 >= 30 -> not active (B rate)
            result = handle_sieu_taxi(player, ctx, _SIEU_TAXI_CFG, None)

        assert result is None


# ---------------------------------------------------------------------------
# D-45 toll priority order test
# ---------------------------------------------------------------------------

class TestD45TollPriority:
    """D-45: free-toll pendants check trước boost pendants."""

    def test_free_toll_pendants_check_before_boost(self):
        """D-45: Trong event ON_LAND_OPPONENT, GiayBay/MangNhen/SieuTaxi check toll
        trước khi tính boost. Verify qua: nếu GiayBay active, ctx['giay_bay_active']
        được set và SieuTaxi R2 bị skip."""
        player = _make_player(pendant_rank="SR")
        board = _make_board_with_travel([5])
        ctx = {
            "is_player_turn": True,
            "board": board,
            "players": [player],
        }

        # GiayBay check trước
        with patch("random.randint", return_value=0):  # active
            giay_bay_result = handle_giay_bay(player, ctx, _GIAY_BAY_CFG, None)

        assert giay_bay_result is not None
        assert ctx.get("giay_bay_active") is True

        # SieuTaxi R2 phải bị skip vì giay_bay_active=True
        ctx_opponent = {
            "trigger": "ON_LAND_OPPONENT",
            "is_player_turn": True,
            "players": [player],
            "giay_bay_active": ctx["giay_bay_active"],
        }

        with patch("random.randint", return_value=0):
            sieu_taxi_result = handle_sieu_taxi(player, ctx_opponent, _SIEU_TAXI_CFG, None)

        assert sieu_taxi_result is None  # bị skip đúng như D-45


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestHandlerRegistry:
    """Kiểm tra các handler được đăng ký vào PENDANT_HANDLERS."""

    def test_all_handlers_registered(self):
        """Tất cả 4 pendant handlers phải có trong PENDANT_HANDLERS."""
        from ctp.skills.pendant_handlers_land import (
            handle_giay_bay,
            handle_cuop_nha,
            handle_mang_nhen,
            handle_sieu_taxi,
        )
        from ctp.skills.registry import PENDANT_HANDLERS

        assert "PT_GIAY_BAY" in PENDANT_HANDLERS
        assert "PT_CUOP_NHA" in PENDANT_HANDLERS
        assert "PT_MANG_NHEN" in PENDANT_HANDLERS
        assert "PT_SIEU_TAXI" in PENDANT_HANDLERS

    def test_registered_handlers_are_correct_functions(self):
        """Các handler đăng ký phải là đúng hàm."""
        from ctp.skills.pendant_handlers_land import (
            handle_giay_bay,
            handle_cuop_nha,
            handle_mang_nhen,
            handle_sieu_taxi,
        )
        from ctp.skills.registry import PENDANT_HANDLERS

        assert PENDANT_HANDLERS["PT_GIAY_BAY"] is handle_giay_bay
        assert PENDANT_HANDLERS["PT_CUOP_NHA"] is handle_cuop_nha
        assert PENDANT_HANDLERS["PT_MANG_NHEN"] is handle_mang_nhen
        assert PENDANT_HANDLERS["PT_SIEU_TAXI"] is handle_sieu_taxi
