"""Tests for special pendant handlers: PT_DKXX2, PT_XICH_NGOC, PT_CHONG_MUA_NHA, PT_SIEU_SAO_CHEP.

Tests:
1.  DKXX2: boosts dkxx_bonus_pool by rank rate on activation
2.  XichNgoc R1 (ON_PRISON_ESCAPE_CHECK): returns prison_doubles_boost with correct %
3.  XichNgoc R1: returns None when rate check fails
4.  XichNgoc R2 (ON_DKXX_CHECK): boosts dkxx_bonus_pool (same as DKXX2)
5.  XichNgoc R2: returns None when rate check fails
6.  ChongMuaNha: blocks at L1 (15% active_factor)
7.  ChongMuaNha: blocks at L3 (60% active_factor)
8.  ChongMuaNha: blocks at L4+ (100% active_factor)
9.  ChongMuaNha: SR rank at L3 = 42% compound block rate
10. ChongMuaNha: returns None (no block) for steal mechanics — no tile provided
11. SieuSaoChep R1: creates L5 on random owned property below L5
12. SieuSaoChep R1: fails silently if no property below L5
13. SieuSaoChep R1: signals D-50 cascade via cascade_upgrade key
14. SieuSaoChep R2: doubles cash at game start
15. SieuSaoChep R2: returns None when rate check fails
"""

import random
import pytest
from unittest.mock import patch, MagicMock

from ctp.core.models import Player
from ctp.core.board import Board, Tile, SpaceId
from ctp.config.schemas import PendantEntry, PendantRankRates

# Force import of handler module to populate PENDANT_HANDLERS registry
import ctp.skills.pendant_handlers_special  # noqa: F401
from ctp.skills.registry import PENDANT_HANDLERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(pendant_rank: str = "SR", cash: float = 1000.0) -> Player:
    p = Player(player_id="P1", cash=cash)
    p.pendant_rank = pendant_rank
    p.dkxx_bonus_pool = 0.0
    return p


def _make_pendant_entry(pendant_id: str, triggers: list[str],
                        rank_rates: dict, rank_rates_2: dict | None = None) -> PendantEntry:
    rr = PendantRankRates(**rank_rates)
    rr2 = PendantRankRates(**rank_rates_2) if rank_rates_2 else None
    return PendantEntry(
        id=pendant_id,
        name=pendant_id,
        triggers=triggers,
        rank_rates=rr,
        rank_rates_2=rr2,
    )


def _make_tile(position: int = 5, building_level: int = 1) -> Tile:
    tile = Tile(position=position, space_id=SpaceId.CITY, opt=1)
    tile.building_level = building_level
    return tile


def _make_board_with_tiles(tiles: list[Tile]) -> MagicMock:
    """Make a mock board that returns given tiles by position."""
    board = MagicMock()
    tile_map = {t.position: t for t in tiles}
    board.get_tile.side_effect = lambda pos: tile_map[pos]
    return board


# ---------------------------------------------------------------------------
# PT_DKXX2 tests
# ---------------------------------------------------------------------------

class TestPTDKXX2:
    """Tests for PT_DKXX2 handler."""

    def setup_method(self):
        self.cfg = _make_pendant_entry(
            "PT_DKXX2",
            triggers=["ON_DKXX_CHECK"],
            rank_rates={"B": 2, "A": 3, "S": 4, "R": 12, "SR": 18},
        )
        self.handler = PENDANT_HANDLERS["PT_DKXX2"]

    def test_boosts_dkxx_bonus_pool_by_rank_rate(self):
        """DKXX2 boosts dkxx_bonus_pool by the rank rate amount."""
        player = _make_player(pendant_rank="SR")
        result = self.handler(player, {}, self.cfg, None)

        assert player.dkxx_bonus_pool == 18
        assert result == {"type": "dkxx_boost", "amount": 18}

    def test_boosts_by_b_rank_rate(self):
        """DKXX2 at rank B uses rate 2."""
        player = _make_player(pendant_rank="B")
        result = self.handler(player, {}, self.cfg, None)

        assert player.dkxx_bonus_pool == 2
        assert result["amount"] == 2

    def test_accumulated_dkxx_pool(self):
        """DKXX2 accumulates into an existing dkxx_bonus_pool."""
        player = _make_player(pendant_rank="A")
        player.dkxx_bonus_pool = 5.0
        self.handler(player, {}, self.cfg, None)

        assert player.dkxx_bonus_pool == 8.0  # 5 + 3


# ---------------------------------------------------------------------------
# PT_XICH_NGOC tests
# ---------------------------------------------------------------------------

class TestPTXichNgoc:
    """Tests for PT_XICH_NGOC handler."""

    def setup_method(self):
        self.cfg = _make_pendant_entry(
            "PT_XICH_NGOC",
            triggers=["ON_PRISON_ESCAPE_CHECK", "ON_DKXX_CHECK"],
            rank_rates={"B": 20, "A": 40, "S": 60, "R": 80, "SR": 100},
            rank_rates_2={"B": 2, "A": 4, "S": 6, "R": 10, "SR": 14},
        )
        self.handler = PENDANT_HANDLERS["PT_XICH_NGOC"]

    def test_r1_returns_prison_doubles_boost(self):
        """XichNgoc R1: returns prison_doubles_boost with correct % at SR."""
        player = _make_player(pendant_rank="SR")
        ctx = {"trigger": "ON_PRISON_ESCAPE_CHECK"}
        # SR rate1 = 100 → random.randint(0,99) < 100 always true
        result = self.handler(player, ctx, self.cfg, None)

        assert result is not None
        assert result["type"] == "prison_doubles_boost"
        assert result["boost_pct"] == 100

    def test_r1_returns_none_when_rate_fails(self):
        """XichNgoc R1: returns None when rate check fails (rate=0)."""
        player = _make_player(pendant_rank="B")  # rate1=20
        ctx = {"trigger": "ON_PRISON_ESCAPE_CHECK"}
        # Force fail by patching randint to return 99 (>= 20 so fails)
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=99):
            result = self.handler(player, ctx, self.cfg, None)

        assert result is None

    def test_r2_boosts_dkxx_bonus_pool(self):
        """XichNgoc R2: boosts dkxx_bonus_pool on ON_DKXX_CHECK (same as DKXX2)."""
        player = _make_player(pendant_rank="SR")
        ctx = {"trigger": "ON_DKXX_CHECK"}
        # SR rate2=14 → force pass
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=0):
            result = self.handler(player, ctx, self.cfg, None)

        assert player.dkxx_bonus_pool == 14
        assert result == {"type": "dkxx_boost", "amount": 14}

    def test_r2_returns_none_when_rate_fails(self):
        """XichNgoc R2: returns None when rate check fails."""
        player = _make_player(pendant_rank="B")  # rate2=2
        ctx = {"trigger": "ON_DKXX_CHECK"}
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=99):
            result = self.handler(player, ctx, self.cfg, None)

        assert result is None
        assert player.dkxx_bonus_pool == 0.0


# ---------------------------------------------------------------------------
# PT_CHONG_MUA_NHA tests
# ---------------------------------------------------------------------------

class TestPTChongMuaNha:
    """Tests for PT_CHONG_MUA_NHA handler."""

    def setup_method(self):
        self.cfg = _make_pendant_entry(
            "PT_CHONG_MUA_NHA",
            triggers=["ON_OPPONENT_LAND_YOURS"],
            rank_rates={"B": 10, "A": 20, "S": 43, "R": 62, "SR": 70},
        )
        self.handler = PENDANT_HANDLERS["PT_CHONG_MUA_NHA"]

    def test_blocks_at_l1_active_factor_15pct(self):
        """ChongMuaNha: L1 tile has active_factor=0.15 → lower block probability."""
        player = _make_player(pendant_rank="SR")  # pendant_rate=0.70
        tile = _make_tile(building_level=1)
        ctx = {"tile": tile}
        # block_rate = 0.15 * 0.70 = 0.105 → 10.5% → random < 10.5
        # Force pass with randint=5 (< 10.5)
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=5):
            result = self.handler(player, ctx, self.cfg, None)

        assert result == {"type": "acquisition_blocked"}

    def test_blocks_at_l3_active_factor_60pct(self):
        """ChongMuaNha: L3 tile has active_factor=0.60."""
        player = _make_player(pendant_rank="SR")  # pendant_rate=0.70
        tile = _make_tile(building_level=3)
        ctx = {"tile": tile}
        # block_rate = 0.60 * 0.70 = 0.42 → 42% → random < 42
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=10):
            result = self.handler(player, ctx, self.cfg, None)

        assert result == {"type": "acquisition_blocked"}

    def test_blocks_at_l4_plus_full_rate(self):
        """ChongMuaNha: L4+ tile has active_factor=1.0 → full pendant rate."""
        player = _make_player(pendant_rank="SR")  # pendant_rate=0.70
        tile = _make_tile(building_level=4)
        ctx = {"tile": tile}
        # block_rate = 1.0 * 0.70 = 0.70 → 70% → random < 70
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=50):
            result = self.handler(player, ctx, self.cfg, None)

        assert result == {"type": "acquisition_blocked"}

    def test_sr_rank_at_l3_compound_rate_42pct(self):
        """ChongMuaNha: SR (70%) at L3 (60%) = block_rate 42%, confirmed by example in GD."""
        player = _make_player(pendant_rank="SR")
        tile = _make_tile(building_level=3)
        ctx = {"tile": tile}
        # block_rate = 0.60 * 0.70 = 0.42 → 42%
        # random=41 → 41 < 42 → block
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=41):
            result = self.handler(player, ctx, self.cfg, None)
        assert result == {"type": "acquisition_blocked"}

        # random=42 → 42 < 42 is False → no block
        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=42):
            result = self.handler(player, ctx, self.cfg, None)
        assert result is None

    def test_no_block_when_tile_missing_from_ctx(self):
        """ChongMuaNha: returns None if ctx has no tile (steal mechanics have no tile key)."""
        player = _make_player(pendant_rank="SR")
        ctx = {}  # no "tile" key — e.g., PT_CUOP_NHA / PT_MANG_NHEN steal paths skip this
        result = self.handler(player, ctx, self.cfg, None)

        assert result is None


# ---------------------------------------------------------------------------
# PT_SIEU_SAO_CHEP tests
# ---------------------------------------------------------------------------

class TestPTSieuSaoChep:
    """Tests for PT_SIEU_SAO_CHEP handler."""

    def setup_method(self):
        self.cfg = _make_pendant_entry(
            "PT_SIEU_SAO_CHEP",
            triggers=["ON_OPPONENT_UPGRADE_SYMBOL", "ON_GAME_START"],
            rank_rates={"B": 5, "A": 7, "S": 10, "R": 15, "SR": 30},
            rank_rates_2={"B": 10, "A": 15, "S": 20, "R": 75, "SR": 90},
        )
        self.handler = PENDANT_HANDLERS["PT_SIEU_SAO_CHEP"]

    def test_r1_creates_l5_on_random_owned_property(self):
        """SieuSaoChep R1: upgrades a random owned property below L5 to L5."""
        player = _make_player(pendant_rank="SR")
        player.owned_properties = [3, 5]

        tile3 = _make_tile(position=3, building_level=3)
        tile5 = _make_tile(position=5, building_level=2)
        board = _make_board_with_tiles([tile3, tile5])

        ctx = {"trigger": "ON_OPPONENT_UPGRADE_SYMBOL", "board": board}

        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=0), \
             patch("ctp.skills.pendant_handlers_special.random.choice", return_value=3):
            result = self.handler(player, ctx, self.cfg, None)

        assert result is not None
        assert result["type"] == "create_landmark"
        assert result["position"] == 3
        assert tile3.building_level == 5

    def test_r1_fails_silently_if_no_property_below_l5(self):
        """SieuSaoChep R1: returns None if all owned properties are already L5."""
        player = _make_player(pendant_rank="SR")
        player.owned_properties = [7]

        tile7 = _make_tile(position=7, building_level=5)
        board = _make_board_with_tiles([tile7])

        ctx = {"trigger": "ON_OPPONENT_UPGRADE_SYMBOL", "board": board}

        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=0):
            result = self.handler(player, ctx, self.cfg, None)

        assert result is None

    def test_r1_signals_d50_cascade(self):
        """SieuSaoChep R1: result contains cascade_upgrade=True for D-50 FSM signal."""
        player = _make_player(pendant_rank="SR")
        player.owned_properties = [10]

        tile10 = _make_tile(position=10, building_level=2)
        board = _make_board_with_tiles([tile10])

        ctx = {"trigger": "ON_OPPONENT_UPGRADE_SYMBOL", "board": board}

        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=0), \
             patch("ctp.skills.pendant_handlers_special.random.choice", return_value=10):
            result = self.handler(player, ctx, self.cfg, None)

        assert result is not None
        assert result.get("cascade_upgrade") is True

    def test_r2_doubles_cash_at_game_start(self):
        """SieuSaoChep R2: doubles player.cash when ON_GAME_START activates."""
        player = _make_player(pendant_rank="SR", cash=500.0)
        ctx = {"trigger": "ON_GAME_START"}

        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=0):
            result = self.handler(player, ctx, self.cfg, None)

        assert player.cash == 1000.0
        assert result == {"type": "double_starting_cash"}

    def test_r2_returns_none_when_rate_fails(self):
        """SieuSaoChep R2: returns None when rate check fails."""
        player = _make_player(pendant_rank="B", cash=500.0)  # rate2=10
        ctx = {"trigger": "ON_GAME_START"}

        with patch("ctp.skills.pendant_handlers_special.random.randint", return_value=99):
            result = self.handler(player, ctx, self.cfg, None)

        assert result is None
        assert player.cash == 500.0  # unchanged
