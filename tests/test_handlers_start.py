"""Tests cho handlers_start.py: SK_GRAMMY, SK_MU_PHEP, calc_total_passing_bonus.

Coverage:
- Grammy: claims random unowned CITY, sets L4
- Grammy: no unowned CITY -> returns None
- Grammy: does not affect Resort tiles
- MuPhep: always active (no random check needed)
- MuPhep B1★: value=41
- MuPhep S5★: value=86
- MuPhep: returns passing_bonus_modifier with correct percent
- calc_total_passing_bonus: single modifier 86% on 150000 = 279000
- calc_total_passing_bonus: stacking MuPhep 86% + SO_10 50% on 150000 = 354000 (D-47)
"""

import pytest
from unittest.mock import MagicMock, patch

from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.skills.handlers_start import (
    handle_grammy,
    handle_mu_phep,
    calc_total_passing_bonus,
    so_10_passing_bonus_modifier,
    SKILL_HANDLERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_board_with_city_tiles(num_city=3, num_resort=2):
    """Tạo board stub với num_city ô CITY và num_resort ô RESORT."""
    board = MagicMock()
    tiles = []
    for i in range(num_city):
        t = Tile(position=i + 2, space_id=SpaceId.CITY, opt=i + 1)
        tiles.append(t)
    for j in range(num_resort):
        t = Tile(position=num_city + j + 2, space_id=SpaceId.RESORT, opt=j + 101)
        tiles.append(t)
    board.board = tiles
    return board


def _make_player(rank="A", star=1, player_id="P1"):
    return Player(player_id=player_id, cash=500_000, rank=rank, star=star)


def _make_mu_phep_cfg(rank="B", base_rate=41.0, min_star=1, chance=2.0):
    """Tạo SkillEntry stub cho SK_MU_PHEP với rank_config."""
    rc = MagicMock()
    rc.base_rate = base_rate
    rc.min_star = min_star
    rc.chance = chance
    cfg = MagicMock()
    cfg.rank_config = {rank: rc}
    cfg.always_active = True
    return cfg


def _make_grammy_cfg():
    cfg = MagicMock()
    cfg.always_active = False
    return cfg


# ---------------------------------------------------------------------------
# SK_GRAMMY Tests
# ---------------------------------------------------------------------------

class TestHandleGrammy:
    def test_claims_random_unowned_city_and_sets_l4(self):
        """Grammy claims 1 random unowned CITY và set building_level=4 (D-23)."""
        board = _make_board_with_city_tiles(num_city=3)
        player = _make_player(rank="A", star=1)
        ctx = {"board": board, "players": [player]}
        cfg = _make_grammy_cfg()
        engine = MagicMock()

        result = handle_grammy(player, ctx, cfg, engine)

        assert result is not None
        assert result["type"] == "grammy_claim"
        pos = result["position"]
        # Tile tương ứng phải được claim
        claimed_tile = next(t for t in board.board if t.position == pos)
        assert claimed_tile.owner_id == "P1"
        assert claimed_tile.building_level == 4  # D-23: nhà cấp 3 = L4
        assert pos in player.owned_properties

    def test_no_unowned_city_returns_none(self):
        """Grammy không có ô CITY trống -> trả None."""
        board = _make_board_with_city_tiles(num_city=2)
        player = _make_player()
        # Mark all CITY as owned
        for t in board.board:
            if t.space_id == SpaceId.CITY:
                t.owner_id = "P2"
        ctx = {"board": board, "players": [player]}
        cfg = _make_grammy_cfg()
        engine = MagicMock()

        result = handle_grammy(player, ctx, cfg, engine)

        assert result is None

    def test_does_not_affect_resort_tiles(self):
        """Grammy chỉ ảnh hưởng ô CITY, không chạm vào RESORT."""
        board = _make_board_with_city_tiles(num_city=1, num_resort=2)
        player = _make_player()
        ctx = {"board": board, "players": [player]}
        cfg = _make_grammy_cfg()
        engine = MagicMock()

        handle_grammy(player, ctx, cfg, engine)

        resort_tiles = [t for t in board.board if t.space_id == SpaceId.RESORT]
        for rt in resort_tiles:
            assert rt.owner_id is None, "Grammy không được claim Resort tile"
            assert rt.building_level == 0, "Grammy không được build trên Resort"

    def test_grammy_registered_in_skill_handlers(self):
        """SK_GRAMMY phải được đăng ký trong SKILL_HANDLERS."""
        assert "SK_GRAMMY" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_GRAMMY"] is handle_grammy


# ---------------------------------------------------------------------------
# SK_MU_PHEP Tests
# ---------------------------------------------------------------------------

class TestHandleMuPhep:
    def test_always_active_no_rate_check_needed(self):
        """MuPhep always_active=True: handler trả kết quả không phụ thuộc random."""
        player = _make_player(rank="B", star=1)
        cfg = _make_mu_phep_cfg(rank="B", base_rate=41.0, min_star=1, chance=2.0)
        ctx = {"board": MagicMock(), "players": [player]}
        engine = MagicMock()

        # Gọi 5 lần để kiểm tra luôn trả về kết quả (không có None do random)
        results = [handle_mu_phep(player, ctx, cfg, engine) for _ in range(5)]
        assert all(r is not None for r in results), "MuPhep phải always active"

    def test_b1_star_value_equals_41(self):
        """MuPhep B1★: value = 41 + (1-1)*2 = 41."""
        player = _make_player(rank="B", star=1)
        cfg = _make_mu_phep_cfg(rank="B", base_rate=41.0, min_star=1, chance=2.0)
        ctx = {"board": MagicMock(), "players": [player]}
        engine = MagicMock()

        result = handle_mu_phep(player, ctx, cfg, engine)

        assert result is not None
        assert result["type"] == "passing_bonus_modifier"
        assert result["percent_increase"] == pytest.approx(41.0)

    def test_s5_star_value_equals_86(self):
        """MuPhep S5★: value = 66 + (5-1)*5 = 86."""
        player = _make_player(rank="S", star=5)
        rc = MagicMock()
        rc.base_rate = 66.0
        rc.min_star = 1
        rc.chance = 5.0
        cfg = MagicMock()
        cfg.rank_config = {"S": rc}
        cfg.always_active = True
        ctx = {"board": MagicMock(), "players": [player]}
        engine = MagicMock()

        result = handle_mu_phep(player, ctx, cfg, engine)

        assert result is not None
        assert result["percent_increase"] == pytest.approx(86.0)

    def test_returns_passing_bonus_modifier_type(self):
        """MuPhep trả về dict với type='passing_bonus_modifier'."""
        player = _make_player(rank="A", star=3)
        rc = MagicMock()
        rc.base_rate = 51.0
        rc.min_star = 1
        rc.chance = 3.0
        cfg = MagicMock()
        cfg.rank_config = {"A": rc}
        cfg.always_active = True
        ctx = {"board": MagicMock(), "players": [player]}
        engine = MagicMock()

        result = handle_mu_phep(player, ctx, cfg, engine)

        assert result["type"] == "passing_bonus_modifier"
        # A3★: 51 + (3-1)*3 = 57
        assert result["percent_increase"] == pytest.approx(57.0)

    def test_rank_r_uses_s_config(self):
        """MuPhep Rank R dùng S config (D-03)."""
        player = _make_player(rank="R", star=5)
        rc = MagicMock()
        rc.base_rate = 66.0
        rc.min_star = 1
        rc.chance = 5.0
        cfg = MagicMock()
        cfg.rank_config = {"S": rc}  # chỉ có S config (R dùng S)
        cfg.always_active = True
        ctx = {"board": MagicMock(), "players": [player]}
        engine = MagicMock()

        result = handle_mu_phep(player, ctx, cfg, engine)

        assert result is not None
        assert result["percent_increase"] == pytest.approx(86.0)

    def test_mu_phep_registered_in_skill_handlers(self):
        """SK_MU_PHEP phải được đăng ký trong SKILL_HANDLERS."""
        assert "SK_MU_PHEP" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_MU_PHEP"] is handle_mu_phep


# ---------------------------------------------------------------------------
# calc_total_passing_bonus Tests (D-47)
# ---------------------------------------------------------------------------

class TestCalcTotalPassingBonus:
    def test_single_modifier_86_percent_on_150000(self):
        """Single modifier 86% on 150,000 = 279,000 (D-47)."""
        modifiers = [{"type": "passing_bonus_modifier", "percent_increase": 86}]
        result = calc_total_passing_bonus(150_000, modifiers)
        assert result == pytest.approx(279_000)

    def test_stacking_mu_phep_86_plus_so10_50_on_150000(self):
        """D-47: Additive stacking MuPhep 86% + SO_10 50% on 150,000 = 354,000."""
        modifiers = [
            {"type": "passing_bonus_modifier", "percent_increase": 86},
            {"type": "passing_bonus_modifier", "percent_increase": 50},
        ]
        result = calc_total_passing_bonus(150_000, modifiers)
        assert result == pytest.approx(354_000)

    def test_no_modifiers_returns_base(self):
        """Không có modifier -> trả về base_bonus không đổi."""
        result = calc_total_passing_bonus(150_000, [])
        assert result == pytest.approx(150_000)

    def test_ignores_non_passing_bonus_modifiers(self):
        """Modifier có type khác không được tính vào passing bonus."""
        modifiers = [
            {"type": "grammy_claim", "position": 5},
            {"type": "passing_bonus_modifier", "percent_increase": 41},
        ]
        result = calc_total_passing_bonus(150_000, modifiers)
        # Chỉ tính 41%: 150,000 * 1.41 = 211,500
        assert result == pytest.approx(211_500)
