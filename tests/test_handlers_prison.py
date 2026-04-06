"""Tests for handlers_prison.py — SK_JOKER, SK_HQXX, SK_LAU_DAI_TINH_AI.

Covers:
- Joker TH1: exit prison + move to unowned CITY + extra_roll (is_player_turn=True)
- Joker TH2: exit prison immediately, joker_pending=True (is_player_turn=False)
- Joker: no unowned CITY -> skip move, still exit + extra_roll (TH1)
- Joker: guard against double-exit (T-02.5-07)
- HQXX: extra_roll + push opponents on same side to prison
- HQXX: no opponents on same side -> only extra_roll + reset doubles
- HQXX: consecutive_doubles reset to 0
- LDTA: pulls random opponent to player's L5
- LDTA: skip opponent already at position (D-48)
- LDTA: does not fire at non-L5 tile
- LDTA: does not fire at opponent's L5
- resolve_joker_pending: moves to city + returns extra_roll
"""

import pytest
from unittest.mock import MagicMock, patch

from ctp.core.models import Player
from ctp.core.board import Board, Tile, SpaceId
from ctp.skills.handlers_prison import (
    handle_joker,
    handle_hqxx,
    handle_lau_dai_tinh_ai,
    resolve_joker_pending,
    SKILL_HANDLERS,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_player(player_id="P1", position=5, prison_turns=3) -> Player:
    p = Player(player_id=player_id, cash=1_000_000, position=position)
    p.prison_turns_remaining = prison_turns
    p.consecutive_doubles = 0
    p.joker_pending = False
    return p


def _make_board_with_cities(city_positions: list[int], owned_map: dict = None) -> MagicMock:
    """Build a mock board with CITY tiles at given positions.

    Args:
        city_positions: Positions to place unowned CITY tiles.
        owned_map: {position: owner_id} for owned tiles.
    """
    owned_map = owned_map or {}
    tiles = []
    for pos in range(1, 33):
        if pos in city_positions:
            t = Tile(position=pos, space_id=SpaceId.CITY, opt=pos)
            t.owner_id = owned_map.get(pos)  # None = unowned
            t.building_level = 0
            tiles.append(t)
        else:
            t = Tile(position=pos, space_id=SpaceId.START, opt=0)
            t.owner_id = None
            t.building_level = 0
            tiles.append(t)

    board = MagicMock()
    board.board = tiles
    board.get_row_non_corner_positions = MagicMock(return_value=[])
    return board


def _make_l5_tile(position: int, owner_id: str, level: int = 5) -> Tile:
    t = Tile(position=position, space_id=SpaceId.CITY, opt=1)
    t.owner_id = owner_id
    t.building_level = level
    return t


# ---------------------------------------------------------------------------
# SK_JOKER tests
# ---------------------------------------------------------------------------

class TestJokerTH1:
    """TH1: is_player_turn=True — all effects fire immediately."""

    def test_joker_th1_exit_prison(self):
        player = _make_player(position=5, prison_turns=3)
        board = _make_board_with_cities([10, 15, 20])
        ctx = {"board": board, "is_player_turn": True, "players": [player]}

        handle_joker(player, ctx, MagicMock(), MagicMock())

        assert player.prison_turns_remaining == 0

    def test_joker_th1_moves_to_unowned_city(self):
        player = _make_player(position=5, prison_turns=3)
        board = _make_board_with_cities([10, 15, 20])
        ctx = {"board": board, "is_player_turn": True, "players": [player]}

        handle_joker(player, ctx, MagicMock(), MagicMock())

        # Should have moved to a CITY tile (nearest forward from 5 = 10)
        assert player.position == 10

    def test_joker_th1_returns_extra_roll(self):
        player = _make_player(position=5, prison_turns=3)
        board = _make_board_with_cities([10])
        ctx = {"board": board, "is_player_turn": True, "players": [player]}

        result = handle_joker(player, ctx, MagicMock(), MagicMock())

        assert result == {"type": "extra_roll"}

    def test_joker_th1_no_unowned_city_skip_move_but_still_exit_and_extra_roll(self):
        """If no unowned CITY exists, skip move but exit+extra_roll still apply."""
        player = _make_player(position=5, prison_turns=2)
        # All CITY tiles are owned
        board = _make_board_with_cities([10, 20], owned_map={10: "P2", 20: "P3"})
        ctx = {"board": board, "is_player_turn": True, "players": [player]}

        result = handle_joker(player, ctx, MagicMock(), MagicMock())

        assert player.prison_turns_remaining == 0   # exited
        assert player.position == 5                  # did not move
        assert result == {"type": "extra_roll"}


class TestJokerTH2:
    """TH2: is_player_turn=False — only exit immediately, defer rest."""

    def test_joker_th2_exit_prison_immediately(self):
        player = _make_player(position=17, prison_turns=3)
        board = _make_board_with_cities([20])
        ctx = {"board": board, "is_player_turn": False, "players": [player]}

        handle_joker(player, ctx, MagicMock(), MagicMock())

        assert player.prison_turns_remaining == 0

    def test_joker_th2_sets_joker_pending(self):
        player = _make_player(position=17, prison_turns=3)
        board = _make_board_with_cities([20])
        ctx = {"board": board, "is_player_turn": False, "players": [player]}

        handle_joker(player, ctx, MagicMock(), MagicMock())

        assert player.joker_pending is True

    def test_joker_th2_does_not_move(self):
        player = _make_player(position=17, prison_turns=3)
        board = _make_board_with_cities([20])
        ctx = {"board": board, "is_player_turn": False, "players": [player]}

        handle_joker(player, ctx, MagicMock(), MagicMock())

        assert player.position == 17  # no move in TH2

    def test_joker_th2_returns_joker_pending_result(self):
        player = _make_player(position=17, prison_turns=3)
        board = _make_board_with_cities([20])
        ctx = {"board": board, "is_player_turn": False, "players": [player]}

        result = handle_joker(player, ctx, MagicMock(), MagicMock())

        assert result == {"type": "joker_pending"}


class TestJokerDoubleExitGuard:
    """T-02.5-07: No double-exit if not in prison."""

    def test_joker_not_in_prison_returns_none(self):
        player = _make_player(position=5, prison_turns=0)  # not in prison
        board = _make_board_with_cities([10])
        ctx = {"board": board, "is_player_turn": True, "players": [player]}

        result = handle_joker(player, ctx, MagicMock(), MagicMock())

        assert result is None


class TestResolveJokerPending:
    """resolve_joker_pending: clears flag, moves to city, returns extra_roll."""

    def test_resolve_joker_pending_clears_flag(self):
        player = _make_player(position=5, prison_turns=0)
        player.joker_pending = True
        board = _make_board_with_cities([10])
        ctx = {"board": board}

        resolve_joker_pending(player, ctx)

        assert player.joker_pending is False

    def test_resolve_joker_pending_moves_to_city(self):
        player = _make_player(position=5, prison_turns=0)
        player.joker_pending = True
        board = _make_board_with_cities([12])
        ctx = {"board": board}

        resolve_joker_pending(player, ctx)

        assert player.position == 12

    def test_resolve_joker_pending_returns_extra_roll(self):
        player = _make_player(position=5, prison_turns=0)
        player.joker_pending = True
        board = _make_board_with_cities([12])
        ctx = {"board": board}

        result = resolve_joker_pending(player, ctx)

        assert result == {"type": "extra_roll"}


# ---------------------------------------------------------------------------
# SK_HQXX tests
# ---------------------------------------------------------------------------

class TestHQXX:
    """SK_HQXX: extra_roll + same-side opponents to prison + reset doubles."""

    def _make_hqxx_board(self, same_side: list[int]) -> MagicMock:
        board = MagicMock()
        board.get_row_non_corner_positions = MagicMock(return_value=same_side)
        return board

    def test_hqxx_returns_extra_roll(self):
        player = _make_player(position=5)
        player.prison_turns_remaining = 0
        board = self._make_hqxx_board([])
        ctx = {"board": board, "players": [player]}

        result = handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert result == {"type": "extra_roll"}

    def test_hqxx_resets_consecutive_doubles(self):
        player = _make_player(position=5)
        player.consecutive_doubles = 2
        board = self._make_hqxx_board([])
        ctx = {"board": board, "players": [player]}

        handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert player.consecutive_doubles == 0

    def test_hqxx_pushes_opponent_on_same_side_to_prison(self):
        player = _make_player("P1", position=5)
        opponent = _make_player("P2", position=7)
        opponent.prison_turns_remaining = 0
        board = self._make_hqxx_board([7, 3, 6])
        ctx = {"board": board, "players": [player, opponent]}

        handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert opponent.prison_turns_remaining == 3

    def test_hqxx_no_opponents_on_same_side_only_extra_roll_and_doubles_reset(self):
        player = _make_player("P1", position=5)
        player.consecutive_doubles = 1
        opponent = _make_player("P2", position=20)  # different side
        opponent.prison_turns_remaining = 0
        # same-side does not include position 20
        board = self._make_hqxx_board([3, 6, 7, 8])
        ctx = {"board": board, "players": [player, opponent]}

        result = handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert opponent.prison_turns_remaining == 0  # not pushed
        assert player.consecutive_doubles == 0
        assert result == {"type": "extra_roll"}

    def test_hqxx_does_not_push_bankrupt_opponent(self):
        player = _make_player("P1", position=5)
        opponent = _make_player("P2", position=7)
        opponent.is_bankrupt = True
        opponent.prison_turns_remaining = 0
        board = self._make_hqxx_board([7])
        ctx = {"board": board, "players": [player, opponent]}

        handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert opponent.prison_turns_remaining == 0  # bankrupt not pushed

    def test_hqxx_does_not_push_self(self):
        player = _make_player("P1", position=5)
        player.prison_turns_remaining = 0
        board = self._make_hqxx_board([5, 6, 7])  # player's own position included
        ctx = {"board": board, "players": [player]}

        handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert player.prison_turns_remaining == 0  # player not self-pushed

    def test_hqxx_pushes_multiple_opponents_on_same_side(self):
        player = _make_player("P1", position=5)
        opp1 = _make_player("P2", position=6)
        opp2 = _make_player("P3", position=8)
        opp1.prison_turns_remaining = 0
        opp2.prison_turns_remaining = 0
        board = self._make_hqxx_board([6, 7, 8])
        ctx = {"board": board, "players": [player, opp1, opp2]}

        handle_hqxx(player, ctx, MagicMock(), MagicMock())

        assert opp1.prison_turns_remaining == 3
        assert opp2.prison_turns_remaining == 3


# ---------------------------------------------------------------------------
# SK_LAU_DAI_TINH_AI tests
# ---------------------------------------------------------------------------

class TestLauDaiTinhAi:
    """SK_LAU_DAI_TINH_AI: pull random opponent to player's L5."""

    def test_ldta_pulls_opponent_to_l5(self):
        player = _make_player("P1", position=15)
        opponent = _make_player("P2", position=3)
        tile = _make_l5_tile(position=15, owner_id="P1", level=5)
        ctx = {"tile": tile, "players": [player, opponent]}

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert opponent.position == 15
        assert result["type"] == "lau_dai_tinh_ai_pull"
        assert result["target_id"] == "P2"

    def test_ldta_skip_opponent_already_at_position(self):
        """D-48: skip if opponent is already at player's position."""
        player = _make_player("P1", position=15)
        opponent = _make_player("P2", position=15)  # already there
        tile = _make_l5_tile(position=15, owner_id="P1", level=5)
        ctx = {"tile": tile, "players": [player, opponent]}

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert opponent.position == 15  # unchanged
        assert result["type"] == "lau_dai_tinh_ai_skipped"

    def test_ldta_does_not_fire_at_non_l5(self):
        """Should not fire at L4 or below."""
        player = _make_player("P1", position=15)
        opponent = _make_player("P2", position=3)
        tile = _make_l5_tile(position=15, owner_id="P1", level=4)
        ctx = {"tile": tile, "players": [player, opponent]}

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert result is None
        assert opponent.position == 3  # not moved

    def test_ldta_does_not_fire_at_opponents_l5(self):
        """Should not fire if tile belongs to opponent, not player."""
        player = _make_player("P1", position=15)
        opponent = _make_player("P2", position=3)
        tile = _make_l5_tile(position=15, owner_id="P2", level=5)  # P2 owns it
        ctx = {"tile": tile, "players": [player, opponent]}

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert result is None
        assert opponent.position == 3  # not moved

    def test_ldta_no_opponents_returns_none(self):
        player = _make_player("P1", position=15)
        tile = _make_l5_tile(position=15, owner_id="P1", level=5)
        ctx = {"tile": tile, "players": [player]}  # only player, no opponents

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert result is None

    def test_ldta_does_not_fire_when_tile_is_none(self):
        player = _make_player("P1", position=15)
        ctx = {"tile": None, "players": [player]}

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert result is None

    def test_ldta_does_not_pull_bankrupt_opponent(self):
        """Bankrupt opponents cannot be pulled."""
        player = _make_player("P1", position=15)
        bankrupt_opp = _make_player("P2", position=3)
        bankrupt_opp.is_bankrupt = True
        tile = _make_l5_tile(position=15, owner_id="P1", level=5)
        ctx = {"tile": tile, "players": [player, bankrupt_opp]}

        result = handle_lau_dai_tinh_ai(player, ctx, MagicMock(), MagicMock())

        assert result is None
        assert bankrupt_opp.position == 3  # not moved


# ---------------------------------------------------------------------------
# Registry test
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_all_handlers_registered_in_skill_handlers(self):
        assert "SK_JOKER" in SKILL_HANDLERS
        assert "SK_HQXX" in SKILL_HANDLERS
        assert "SK_LAU_DAI_TINH_AI" in SKILL_HANDLERS
