"""Tests for handlers_land_toll.py — SK_BUA_SET, SK_NGOI_SAO, SK_CUONG_CHE.

Test coverage:
- BuaSet: waives toll, returns move instruction
- BuaSet: does not fire when is_player_turn=False (D-51)
- BuaSet: destination=None when no unowned CITY
- NgoiSao: toll x2 on activation (no angel card)
- NgoiSao: 70% angel card destruction (mock random)
- NgoiSao: angel card success 30% — toll waived entirely
- NgoiSao: fires in any turn (D-52 — no turn restriction)
- CuongChe: teleports opponent to most expensive L5
- CuongChe: does not fire in player's own turn (D-49)
- CuongChe: fails silently when no L5 properties
- CuongChe: skips opponent already at target (D-48)
"""

import pytest
from unittest.mock import patch, MagicMock

from ctp.core.models import Player
from ctp.core.board import Board, Tile, SpaceId
from ctp.skills.handlers_land_toll import (
    handle_bua_set,
    handle_ngoi_sao,
    handle_cuong_che,
    ANGEL_CARD_ITEM_ID,
)
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(player_id="P1", position=5, owned=None, rank="A", star=1) -> Player:
    p = Player(player_id=player_id, cash=500_000, position=position, rank=rank, star=star)
    if owned:
        p.owned_properties = list(owned)
    return p


def _make_board_with_tiles(tiles: list) -> MagicMock:
    """Create a mock Board with get_tile delegating to a position→Tile dict."""
    tile_map = {t.position: t for t in tiles}
    board = MagicMock()
    board.get_tile = lambda pos: tile_map[pos]
    return board


def _make_city_tile(position: int, owner_id=None, building_level: int = 1) -> Tile:
    t = Tile(position=position, space_id=SpaceId.CITY, opt=position)
    t.owner_id = owner_id
    t.building_level = building_level
    return t


def _make_non_city_tile(position: int) -> Tile:
    """Start tile — not CITY."""
    t = Tile(position=position, space_id=SpaceId.START, opt=0)
    return t


# ---------------------------------------------------------------------------
# SK_BUA_SET tests
# ---------------------------------------------------------------------------

class TestBuaSet:
    def _ctx(self, board, is_player_turn=True):
        return {"board": board, "is_player_turn": is_player_turn}

    def test_waives_toll_and_returns_move_instruction(self):
        """BuaSet returns toll_waive with move_to_nearest_unowned=True."""
        # Position 5 is owned CITY (opponent's), position 6 is unowned CITY
        tiles = [
            _make_city_tile(5, owner_id="P2"),   # current pos
            _make_city_tile(6, owner_id=None),   # nearest unowned
        ]
        # Fill rest with non-city tiles so find_nearest works
        for pos in range(1, 33):
            if pos not in (5, 6):
                tiles.append(_make_non_city_tile(pos))

        board = _make_board_with_tiles(tiles)
        player = _make_player(position=5)
        ctx = self._ctx(board, is_player_turn=True)

        result = handle_bua_set(player, ctx, cfg=None, engine=None)

        assert result is not None
        assert result["type"] == "toll_waive"
        assert result["move_to_nearest_unowned"] is True
        assert result["destination"] == 6

    def test_does_not_fire_when_not_player_turn(self):
        """BuaSet returns None when is_player_turn=False (D-51)."""
        board = MagicMock()
        player = _make_player(position=3)
        ctx = self._ctx(board, is_player_turn=False)

        result = handle_bua_set(player, ctx, cfg=None, engine=None)

        assert result is None

    def test_destination_none_when_no_unowned_city(self):
        """BuaSet destination=None when all CITY tiles are owned."""
        # All CITY tiles owned
        tiles = []
        for pos in range(1, 33):
            if pos in (3, 7, 12, 18, 22, 27):
                t = _make_city_tile(pos, owner_id="P2")
            else:
                t = _make_non_city_tile(pos)
            tiles.append(t)

        board = _make_board_with_tiles(tiles)
        player = _make_player(position=5)
        ctx = self._ctx(board, is_player_turn=True)

        result = handle_bua_set(player, ctx, cfg=None, engine=None)

        assert result is not None
        assert result["type"] == "toll_waive"
        assert result["destination"] is None


# ---------------------------------------------------------------------------
# SK_NGOI_SAO tests
# ---------------------------------------------------------------------------

class TestNgoiSao:
    def _ctx(self, opponent, board=None):
        return {"opponent": opponent, "tile": MagicMock(), "board": board or MagicMock()}

    def test_toll_multiply_x2_no_angel(self):
        """NgoiSao doubles toll when opponent has no angel card."""
        player = _make_player("P1")
        opponent = _make_player("P2")
        opponent.held_card = None

        result = handle_ngoi_sao(player, self._ctx(opponent), cfg=None, engine=None)

        assert result is not None
        assert result["type"] == "toll_multiply"
        assert result["factor"] == 2
        assert result["angel_destroyed"] is False
        assert result.get("angel_blocked") is False

    def test_angel_card_destroyed_70_percent(self):
        """NgoiSao destroys angel card 70% — toll x2 still applies."""
        player = _make_player("P1")
        opponent = _make_player("P2")
        opponent.held_card = ANGEL_CARD_ITEM_ID

        with patch("ctp.skills.handlers_land_toll.random.randint", return_value=50):
            # 50 <= 70 → angel destroyed
            result = handle_ngoi_sao(player, self._ctx(opponent), cfg=None, engine=None)

        assert result is not None
        assert result["type"] == "toll_multiply"
        assert result["factor"] == 2
        assert result["angel_destroyed"] is True
        assert opponent.held_card is None  # card consumed

    def test_angel_card_success_30_percent(self):
        """NgoiSao 30% chance — angel card works, toll waived entirely."""
        player = _make_player("P1")
        opponent = _make_player("P2")
        opponent.held_card = ANGEL_CARD_ITEM_ID

        with patch("ctp.skills.handlers_land_toll.random.randint", return_value=90):
            # 90 > 70 → angel succeeds
            result = handle_ngoi_sao(player, self._ctx(opponent), cfg=None, engine=None)

        assert result is not None
        assert result.get("toll_waived") is True
        assert result.get("angel_blocked") is True
        assert opponent.held_card is None  # card was used

    def test_fires_in_any_turn(self):
        """NgoiSao has no turn restriction — fires when ctx has no is_player_turn."""
        player = _make_player("P1")
        opponent = _make_player("P2")
        opponent.held_card = None

        # No is_player_turn key in ctx — should still fire
        ctx = {"opponent": opponent, "tile": MagicMock()}
        result = handle_ngoi_sao(player, ctx, cfg=None, engine=None)

        assert result is not None
        assert result["type"] == "toll_multiply"


# ---------------------------------------------------------------------------
# SK_CUONG_CHE tests
# ---------------------------------------------------------------------------

class TestCuongChe:
    def _ctx(self, opponent, board, is_opponent_turn=True):
        return {
            "opponent": opponent,
            "board": board,
            "is_opponent_turn": is_opponent_turn,
        }

    def _board_with_l5(self, l5_positions: list[int], player_id: str):
        """Build a mock board where given positions are L5 CITY tiles owned by player."""
        tiles = {}
        for pos in range(1, 33):
            if pos in l5_positions:
                t = _make_city_tile(pos, owner_id=player_id, building_level=5)
            else:
                t = _make_non_city_tile(pos)
            tiles[pos] = t

        board = MagicMock()
        board.get_tile = lambda pos: tiles[pos]
        return board

    def test_teleports_opponent_to_most_expensive_l5(self):
        """CuongChe teleports opponent to most expensive L5 tile."""
        from ctp.core.constants import calc_invested_build_cost

        player = _make_player("P1", owned=[10, 15])
        opponent = _make_player("P2", position=10)

        tiles = {}
        for pos in range(1, 33):
            if pos == 10:
                t = _make_city_tile(10, owner_id="P1", building_level=5)
                t.opt = 1
            elif pos == 15:
                t = _make_city_tile(15, owner_id="P1", building_level=5)
                t.opt = 2
            else:
                t = _make_non_city_tile(pos)
            tiles[pos] = t

        board = MagicMock()
        board.get_tile = lambda pos: tiles[pos]

        # Mock calc_invested_build_cost: pos 15 is more expensive
        def mock_calc(b, pos):
            return {10: 100_000, 15: 200_000}.get(pos, 0)

        ctx = self._ctx(opponent, board, is_opponent_turn=True)

        with patch("ctp.skills.handlers_land_toll.calc_invested_build_cost", side_effect=mock_calc):
            result = handle_cuong_che(player, ctx, cfg=None, engine=None)

        assert result is not None
        assert result["type"] == "teleport"
        assert result["destination"] == 15

    def test_does_not_fire_in_players_own_turn(self):
        """CuongChe returns None when is_opponent_turn=False (D-49)."""
        player = _make_player("P1", owned=[10])
        opponent = _make_player("P2", position=5)
        board = self._board_with_l5([10], "P1")
        ctx = self._ctx(opponent, board, is_opponent_turn=False)

        result = handle_cuong_che(player, ctx, cfg=None, engine=None)

        assert result is None

    def test_fails_silently_no_l5_properties(self):
        """CuongChe returns None when player has no L5 properties."""
        player = _make_player("P1", owned=[10])
        opponent = _make_player("P2", position=5)

        tiles = {}
        for pos in range(1, 33):
            if pos == 10:
                t = _make_city_tile(10, owner_id="P1", building_level=3)  # L3, not L5
            else:
                t = _make_non_city_tile(pos)
            tiles[pos] = t

        board = MagicMock()
        board.get_tile = lambda pos: tiles[pos]
        ctx = self._ctx(opponent, board, is_opponent_turn=True)

        result = handle_cuong_che(player, ctx, cfg=None, engine=None)

        assert result is None

    def test_skips_if_opponent_already_at_target(self):
        """CuongChe returns None if opponent already at target L5 (D-48)."""
        player = _make_player("P1", owned=[10])
        opponent = _make_player("P2", position=10)  # already at target

        tiles = {}
        for pos in range(1, 33):
            if pos == 10:
                t = _make_city_tile(10, owner_id="P1", building_level=5)
                t.opt = 1
            else:
                t = _make_non_city_tile(pos)
            tiles[pos] = t

        board = MagicMock()
        board.get_tile = lambda pos: tiles[pos]

        def mock_calc(b, pos):
            return 100_000

        ctx = self._ctx(opponent, board, is_opponent_turn=True)

        with patch("ctp.skills.handlers_land_toll.calc_invested_build_cost", side_effect=mock_calc):
            result = handle_cuong_che(player, ctx, cfg=None, engine=None)

        assert result is None


# ---------------------------------------------------------------------------
# Registry check
# ---------------------------------------------------------------------------

def test_all_handlers_registered():
    """All 3 handlers are registered in SKILL_HANDLERS."""
    assert "SK_BUA_SET" in SKILL_HANDLERS
    assert "SK_NGOI_SAO" in SKILL_HANDLERS
    assert "SK_CUONG_CHE" in SKILL_HANDLERS
