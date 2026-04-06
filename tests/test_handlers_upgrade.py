"""Unit tests for handlers_upgrade.py — SK_TEDDY, SK_O_KY_DIEU, SK_MONG_NGUA.

Tests:
- Teddy: E1 nang cap len L5 tu bat ky cap nao
- Teddy: E2 di chuyen den Travel tile voi 60% check
- Teddy: E1 tao L5 -> phat tin hieu ON_UPGRADE cascade (D-50)
- OKyDieu: chi trigger khi new_level=4 (khong trigger o cap 3, 5)
- OKyDieu: tra ve sweep_walk voi 32 buoc
- MongNgua: lay Resort chua co chu cung canh
- MongNgua: cuop Resort cua doi thu (chi doi owner_id per D-28)
- MongNgua: fail silently khi khong co Resort tren canh
- MongNgua: khong co tac dung neu player da so huu Resort
"""

import pytest
from unittest.mock import MagicMock, patch

from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.skills.handlers_upgrade import (
    handle_teddy,
    handle_o_ky_dieu,
    handle_mong_ngua,
    _find_resort_on_side,
)
from ctp.skills.registry import SKILL_HANDLERS
from ctp.config.schemas import RankConfig, SkillEntry, SkillsConfig, PendantsConfig, PetsConfig
from ctp.skills.engine import SkillEngine


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _make_minimal_board() -> Board:
    """Tao Board toi gian voi 32 o.

    Layout:
    - Pos 1: START (goc)
    - Pos 2: TRAVEL
    - Pos 8: RESORT (opt 101) -- cung canh hang 0 voi pos 5 (khong phai goc)
    - Pos 9: CITY (opt 9) -- goc, khong dung lam Resort
    - Pos 16: RESORT (opt 102) -- hang 1 (9-17)
    - Pos 17, 25: goc
    - Pos khac: CITY
    - Pos dat vua la pos 5 (hang 0: 1-9) -> cung canh voi pos 8 (RESORT)
    """
    space_positions = {}
    for p in range(1, 33):
        if p == 1:
            space_positions[str(p)] = {"spaceId": SpaceId.START, "opt": 0}
        elif p == 2:
            space_positions[str(p)] = {"spaceId": SpaceId.TRAVEL, "opt": 0}
        elif p == 8:
            space_positions[str(p)] = {"spaceId": SpaceId.RESORT, "opt": 101}
        elif p == 16:
            space_positions[str(p)] = {"spaceId": SpaceId.RESORT, "opt": 102}
        else:
            opt_val = p if p <= 18 else (p % 9) + 1
            space_positions[str(p)] = {"spaceId": SpaceId.CITY, "opt": opt_val}

    # Minimal land_config (1 map, 1 tile)
    land_config = {
        "1": {
            str(i): {
                "color": (i - 1) // 2 + 1,
                "building": {
                    "1": {"build": 1000, "toll": 100},
                    "2": {"build": 2000, "toll": 300},
                    "3": {"build": 3000, "toll": 600},
                    "4": {"build": 4000, "toll": 1000},
                    "5": {"build": 5000, "toll": 2000},
                }
            }
            for i in range(1, 19)
        }
    }
    return Board(space_positions, land_config)


def _make_player(player_id: str = "p1", position: int = 5, rank: str = "A", star: int = 3) -> Player:
    p = Player(player_id, 1_000_000)
    p.position = position
    p.rank = rank
    p.star = star
    return p


def _make_skill_cfg(skill_id: str, trigger: str, secondary_rate: float | None = None) -> SkillEntry:
    return SkillEntry(
        id=skill_id,
        name=skill_id,
        trigger=trigger,
        rank_config={
            "A": RankConfig(min_star=1, base_rate=100, chance=0),
            "S": RankConfig(min_star=1, base_rate=100, chance=0),
        },
        secondary_rate=secondary_rate,
    )


def _make_engine(skills=None) -> SkillEngine:
    skills_cfg = SkillsConfig(skills=skills or [])
    return SkillEngine(skills_cfg, PendantsConfig(pendants=[]), PetsConfig(pets=[]))


# ---------------------------------------------------------------------------
# Kiem tra handler duoc dang ky trong SKILL_HANDLERS
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Kiem tra cac handler duoc dang ky dung."""

    def test_teddy_registered(self):
        assert "SK_TEDDY" in SKILL_HANDLERS
        assert callable(SKILL_HANDLERS["SK_TEDDY"])

    def test_o_ky_dieu_registered(self):
        assert "SK_O_KY_DIEU" in SKILL_HANDLERS
        assert callable(SKILL_HANDLERS["SK_O_KY_DIEU"])

    def test_mong_ngua_registered(self):
        assert "SK_MONG_NGUA" in SKILL_HANDLERS
        assert callable(SKILL_HANDLERS["SK_MONG_NGUA"])


# ---------------------------------------------------------------------------
# SK_TEDDY tests
# ---------------------------------------------------------------------------


class TestHandleTeddy:
    """SK_TEDDY: nang cap len L5 + 60% di Travel."""

    def _make_ctx(self, board, player, players, chosen_level=2):
        tile = board.get_tile(player.position)
        tile.building_level = chosen_level
        return {
            "tile": tile,
            "board": board,
            "players": players,
            "chosen_level": chosen_level,
        }

    def test_teddy_effect1_upgrades_to_l5(self):
        """E1: tile duoc nang cap len L5 bat ke chosen_level la bao nhieu."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        ctx = self._make_ctx(board, player, [player], chosen_level=2)

        cfg = _make_skill_cfg("SK_TEDDY", "ON_UPGRADE")
        engine = _make_engine()

        # Buoc qua rate check (handler da duoc goi sau khi pass rate)
        with patch("random.randint", return_value=99):  # E2 60% khong active
            result = handle_teddy(player, ctx, cfg, engine)

        assert ctx["tile"].building_level == 5
        assert result is not None
        assert result["type"] == "upgrade_to_l5"

    def test_teddy_effect1_from_level3(self):
        """E1: tu L3, nang len L5."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        ctx = self._make_ctx(board, player, [player], chosen_level=3)

        cfg = _make_skill_cfg("SK_TEDDY", "ON_UPGRADE")
        engine = _make_engine()

        with patch("random.randint", return_value=99):
            handle_teddy(player, ctx, cfg, engine)

        assert ctx["tile"].building_level == 5

    def test_teddy_effect2_moves_to_travel(self):
        """E2: 60% active -> player di chuyen den Travel tile."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        ctx = self._make_ctx(board, player, [player], chosen_level=2)

        cfg = _make_skill_cfg("SK_TEDDY", "ON_UPGRADE")
        engine = _make_engine()

        # E2: random < 60 -> active
        with patch("random.randint", return_value=0):  # <60 -> E2 active
            result = handle_teddy(player, ctx, cfg, engine)

        assert result["move_to_travel"] is True
        assert result["travel_pos"] is not None
        # Kiem tra player thuc su di chuyen den Travel
        travel_tile = board.get_tile(result["travel_pos"])
        assert travel_tile.space_id == SpaceId.TRAVEL
        assert player.position == result["travel_pos"]

    def test_teddy_effect2_no_move_when_rate_fails(self):
        """E2: 60% khong active -> player khong di chuyen."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        original_pos = player.position
        ctx = self._make_ctx(board, player, [player], chosen_level=2)

        cfg = _make_skill_cfg("SK_TEDDY", "ON_UPGRADE")
        engine = _make_engine()

        # E2: random >= 60 -> khong active
        with patch("random.randint", return_value=60):  # >=60 -> E2 khong active
            result = handle_teddy(player, ctx, cfg, engine)

        assert result["move_to_travel"] is False
        assert player.position == original_pos

    def test_teddy_cascade_d50_fires_on_upgrade(self):
        """D-50: Khi Teddy tao L5, fire ON_UPGRADE cascade voi new_level=5."""
        board = _make_minimal_board()
        player = _make_player(position=5, rank="A", star=3)

        # Them SK_MONG_NGUA vao player skills
        player.skills = ["SK_MONG_NGUA"]

        # Tao engine voi SK_MONG_NGUA duoc dang ky
        mong_ngua_cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine(skills=[mong_ngua_cfg])
        cascade_called = []

        def mock_mong_ngua(p, c, cfg2, eng):
            cascade_called.append(c.get("new_level"))
            return None

        engine.register_skill("SK_MONG_NGUA", mock_mong_ngua)
        # Cho SK_MONG_NGUA always activate trong cascade
        engine._skill_handlers["SK_MONG_NGUA"] = mock_mong_ngua
        # Override rate check bang always_active
        mong_ngua_cfg_always = SkillEntry(
            id="SK_MONG_NGUA",
            name="SK_MONG_NGUA",
            trigger="ON_UPGRADE",
            rank_config={"A": RankConfig(min_star=1, base_rate=100, chance=0)},
            always_active=True,
        )
        engine.skill_configs["SK_MONG_NGUA"] = mong_ngua_cfg_always

        ctx = {
            "tile": board.get_tile(player.position),
            "board": board,
            "players": [player],
            "chosen_level": 2,
        }

        teddy_cfg = _make_skill_cfg("SK_TEDDY", "ON_UPGRADE")

        with patch("random.randint", return_value=99):  # E2 khong active
            handle_teddy(player, ctx, teddy_cfg, engine)

        # D-50: cascade phai duoc goi voi new_level=5
        assert 5 in cascade_called, f"Cascade chua duoc goi, cascade_called={cascade_called}"


# ---------------------------------------------------------------------------
# SK_O_KY_DIEU tests
# ---------------------------------------------------------------------------


class TestHandleOKyDieu:
    """SK_O_KY_DIEU: chi trigger khi new_level=4, tra ve sweep_walk 32 buoc."""

    def test_triggers_only_at_level4(self):
        """Chi trigger khi new_level == 4."""
        board = _make_minimal_board()
        player = _make_player()
        cfg = _make_skill_cfg("SK_O_KY_DIEU", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {"tile": board.get_tile(player.position), "board": board,
               "players": [player], "new_level": 4}
        result = handle_o_ky_dieu(player, ctx, cfg, engine)
        assert result is not None
        assert result["type"] == "sweep_walk"
        assert result["steps"] == 32

    def test_no_trigger_at_level3(self):
        """Khong trigger khi new_level == 3."""
        board = _make_minimal_board()
        player = _make_player()
        cfg = _make_skill_cfg("SK_O_KY_DIEU", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {"tile": board.get_tile(player.position), "board": board,
               "players": [player], "new_level": 3}
        result = handle_o_ky_dieu(player, ctx, cfg, engine)
        assert result is None

    def test_no_trigger_at_level5(self):
        """Khong trigger khi new_level == 5."""
        board = _make_minimal_board()
        player = _make_player()
        cfg = _make_skill_cfg("SK_O_KY_DIEU", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {"tile": board.get_tile(player.position), "board": board,
               "players": [player], "new_level": 5}
        result = handle_o_ky_dieu(player, ctx, cfg, engine)
        assert result is None

    def test_no_trigger_at_level2(self):
        """Khong trigger khi new_level == 2."""
        board = _make_minimal_board()
        player = _make_player()
        cfg = _make_skill_cfg("SK_O_KY_DIEU", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {"tile": board.get_tile(player.position), "board": board,
               "players": [player], "new_level": 2}
        result = handle_o_ky_dieu(player, ctx, cfg, engine)
        assert result is None

    def test_sweep_walk_returns_exactly_32_steps(self):
        """Tra ve dung 32 buoc (T-02.5-08: bounded loop)."""
        board = _make_minimal_board()
        player = _make_player()
        cfg = _make_skill_cfg("SK_O_KY_DIEU", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {"tile": board.get_tile(player.position), "board": board,
               "players": [player], "new_level": 4}
        result = handle_o_ky_dieu(player, ctx, cfg, engine)
        assert result["steps"] == 32


# ---------------------------------------------------------------------------
# SK_MONG_NGUA tests
# ---------------------------------------------------------------------------


class TestHandleMongNgua:
    """SK_MONG_NGUA: lay Resort cung canh khi xay L5 (D-24, D-28)."""

    def _make_ctx_l5(self, board, player, players, tile_pos=5):
        tile = board.get_tile(tile_pos)
        tile.building_level = 5
        return {
            "tile": tile,
            "board": board,
            "players": players,
            "new_level": 5,
        }

    def test_no_trigger_when_not_level5(self):
        """Khong trigger khi new_level != 5."""
        board = _make_minimal_board()
        player = _make_player()
        cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {
            "tile": board.get_tile(5), "board": board,
            "players": [player], "new_level": 4
        }
        result = handle_mong_ngua(player, ctx, cfg, engine)
        assert result is None

    def test_claims_unowned_resort_on_same_side(self):
        """Lay Resort chua co chu cung canh ban co.

        Ban co: hang 0 la o 1-9 (goc la 1 va 9).
        O 5 (CITY) va o 8 (RESORT) cung hang 0, ca hai deu khong phai goc.
        """
        board = _make_minimal_board()
        player = _make_player(position=5)
        resort_tile = board.get_tile(8)
        assert resort_tile.space_id == SpaceId.RESORT
        resort_tile.owner_id = None  # Chua co chu

        cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine()

        ctx = self._make_ctx_l5(board, player, [player], tile_pos=5)
        result = handle_mong_ngua(player, ctx, cfg, engine)

        assert result is not None
        assert result["type"] == "claim_resort"
        assert result["resort_pos"] == 8
        assert resort_tile.owner_id == "p1"
        assert 8 in player.owned_properties

    def test_steals_resort_from_opponent(self):
        """Cuop Resort cua doi thu — chi doi owner_id per D-28."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        opponent = _make_player(player_id="p2", position=7)
        resort_tile = board.get_tile(8)
        resort_tile.owner_id = "p2"
        opponent.add_property(8)

        cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine()

        ctx = self._make_ctx_l5(board, player, [player, opponent], tile_pos=5)
        result = handle_mong_ngua(player, ctx, cfg, engine)

        assert result is not None
        assert result["type"] == "claim_resort"
        assert result["stolen_from"] == "p2"
        # Doi thu mat Resort
        assert 8 not in opponent.owned_properties
        # Player cuop duoc Resort
        assert resort_tile.owner_id == "p1"
        assert 8 in player.owned_properties

    def test_no_effect_when_player_already_owns_resort(self):
        """Khong co tac dung neu player da so huu Resort."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        resort_tile = board.get_tile(8)
        resort_tile.owner_id = "p1"
        player.add_property(8)

        cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine()

        ctx = self._make_ctx_l5(board, player, [player], tile_pos=5)
        result = handle_mong_ngua(player, ctx, cfg, engine)

        assert result is None
        assert resort_tile.owner_id == "p1"  # Khong thay doi

    def test_fail_silently_when_no_resort_on_side(self):
        """Fail silently khi khong co Resort tren canh do.

        Dung o CITY (pos 18) thuoc hang 1 (9-17).
        Hang nay khong co Resort (pos 9 la goc, pos 16 la RESORT nhung
        trong test nay ta doi no thanh CITY de test fail silently).
        """
        board = _make_minimal_board()
        # Doi Resort tren canh hang 1 thanh CITY
        board.get_tile(16).space_id = SpaceId.CITY

        player = _make_player(position=18)  # Hang 1: 9-17... pos 18 thuoc hang 2 (17-25)
        # Dung o 11 (hang 1: 9..17), khong co Resort tren canh
        player.position = 11

        cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine()

        ctx = {
            "tile": board.get_tile(11), "board": board,
            "players": [player], "new_level": 5
        }
        result = handle_mong_ngua(player, ctx, cfg, engine)

        assert result is None  # fail silently

    def test_resort_building_level_unchanged_when_stolen(self):
        """D-28: Khi cuop Resort, building_level giu nguyen (Resort chi 1 cap)."""
        board = _make_minimal_board()
        player = _make_player(position=5)
        opponent = _make_player(player_id="p2", position=7)
        resort_tile = board.get_tile(8)
        resort_tile.owner_id = "p2"
        resort_tile.building_level = 0  # Resort khong co building_level
        opponent.add_property(8)

        cfg = _make_skill_cfg("SK_MONG_NGUA", "ON_UPGRADE")
        engine = _make_engine()

        ctx = self._make_ctx_l5(board, player, [player, opponent], tile_pos=5)
        handle_mong_ngua(player, ctx, cfg, engine)

        # building_level khong duoc thay doi
        assert resort_tile.building_level == 0
