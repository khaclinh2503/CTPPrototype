"""Tests for pet handlers — PET_THIEN_THAN, PET_XI_CHO, PET_PHU_THU, PET_TROI_CHAN.

Covers:
- tiles_needed_to_win: 3 color pairs condition
- tiles_needed_to_win: 1 full side condition
- tiles_needed_to_win: all Resorts condition
- ThienThan: waives toll, stamina depletes (handled by engine)
- XiCho: builds L1 when opponent 1 tile from win
- XiCho: does not fire when opponent needs > 1 tile
- XiCho: acquisition_blocked_turns set to 1 on chosen tile
- PhuThu: steals 50% at tier 1, 200% at tier 5
- PhuThu: opponent cash decreases by exact amount
- TroiChan: sets bound_turns on opponent
- TroiChan: bound_turns stacks
"""

import pytest
from unittest.mock import MagicMock

from ctp.core.board import Board, Tile, SpaceId
from ctp.core.models import Player

# Import triggers registration as side effect
import ctp.skills.pet_handlers  # noqa: F401 — populates PET_HANDLERS

from ctp.skills.pet_handlers import (
    tiles_needed_to_win,
    handle_thien_than,
    handle_xi_cho,
    handle_phu_thu,
    handle_troi_chan,
    _PHU_THU_STEAL_RATIOS,
)
from ctp.skills.registry import PET_HANDLERS


# ---------------------------------------------------------------------------
# Board / Player helpers
# ---------------------------------------------------------------------------

def _make_player(player_id: str = "p1", cash: float = 1_000_000,
                 pet_tier: int = 1) -> Player:
    p = Player(player_id, cash)
    p.pet_tier = pet_tier
    return p


def _make_minimal_board() -> Board:
    """Create a minimal 32-tile board with all CITY tiles at positions 2-19 (18 CITY).

    Layout (matches Board.json Map1 spirit):
      pos 1      = START
      pos 2-19   = CITY (18 tiles, 9 color-pairs: opt 1-18, colors 1-9 with pairs)
      pos 20-23  = RESORT (4 tiles)
      pos 9,17   = PRISON / CHANCE (non-property corners, using CITY placeholder)
      pos 24-32  = filler (CHANCE)

    For simplicity, color grouping: opt 1,2 → color 1; opt 3,4 → color 2; … opt 17,18 → color 9
    """
    tiles = []
    # pos 1 = START
    tiles.append(Tile(position=1, space_id=SpaceId.START, opt=0))
    # pos 2-19 = CITY (18 tiles)
    for i in range(18):
        pos = i + 2
        tiles.append(Tile(position=pos, space_id=SpaceId.CITY, opt=i + 1))
    # pos 20-23 = RESORT
    for i in range(4):
        pos = i + 20
        tiles.append(Tile(position=pos, space_id=SpaceId.RESORT, opt=100 + i))
    # pos 24-32 = CHANCE (filler)
    for pos in range(24, 33):
        tiles.append(Tile(position=pos, space_id=SpaceId.CHANCE, opt=0))

    # Build a mock board with .board list
    board = MagicMock(spec=Board)
    board.board = tiles

    def get_tile(position):
        return tiles[position - 1]

    board.get_tile = get_tile
    # land_config: pairs opt 1&2 → color 1, opt 3&4 → color 2, etc.
    land_cfg = {"1": {}}
    for i in range(18):
        opt = i + 1
        color = (i // 2) + 1  # 2 opts per color group
        land_cfg["1"][str(opt)] = {"color": color}
    board.land_config = land_cfg
    return board


# ---------------------------------------------------------------------------
# tiles_needed_to_win tests
# ---------------------------------------------------------------------------

class TestTilesNeededToWin:
    """Tests for the tiles_needed_to_win helper."""

    def test_three_color_pairs_complete_returns_zero(self):
        """Player owns both tiles of 3 color pairs → already won → 0."""
        board = _make_minimal_board()
        player = _make_player("p1")
        # Give p1 both tiles for colors 1, 2, 3 (opts 1-6, positions 2-7)
        for pos in range(2, 8):  # positions 2,3,4,5,6,7 → opts 1-6 → colors 1-3
            board.get_tile(pos).owner_id = "p1"
        result = tiles_needed_to_win(player, board)
        assert result == 0

    def test_three_color_pairs_needs_one_more(self):
        """Player has 2 complete pairs + 1 tile of 3rd pair → needs 1 more tile."""
        board = _make_minimal_board()
        player = _make_player("p1")
        # Complete pairs for colors 1,2 (opts 1-4, positions 2-5)
        for pos in range(2, 6):
            board.get_tile(pos).owner_id = "p1"
        # Partial pair for color 3: own opt 5 (pos 6) but not opt 6 (pos 7)
        board.get_tile(6).owner_id = "p1"
        result = tiles_needed_to_win(player, board)
        assert result == 1

    def test_all_resorts_owned_returns_zero(self):
        """Player owns all resort tiles → already won (condition 3) → 0."""
        board = _make_minimal_board()
        player = _make_player("p1")
        # Positions 20-23 are RESORT
        for pos in range(20, 24):
            board.get_tile(pos).owner_id = "p1"
        result = tiles_needed_to_win(player, board)
        assert result == 0

    def test_all_resorts_needs_two(self):
        """Player owns 2 of 4 resorts → needs 2 more."""
        board = _make_minimal_board()
        player = _make_player("p1")
        board.get_tile(20).owner_id = "p1"
        board.get_tile(21).owner_id = "p1"
        # 22, 23 not owned
        result = tiles_needed_to_win(player, board)
        assert result <= 2  # condition 3 gives 2

    def test_full_side_condition(self):
        """Player owns all CITY+RESORT on a side → 0 needed for that side."""
        board = _make_minimal_board()
        player = _make_player("p1")
        # Side 0 = positions 1-9, CITY tiles are 2-8 (positions 2-8, RESORT none there)
        for pos in range(2, 9):
            tile = board.get_tile(pos)
            if tile.space_id == SpaceId.CITY:
                tile.owner_id = "p1"
        result = tiles_needed_to_win(player, board)
        assert result == 0

    def test_no_tiles_owned_returns_large_number(self):
        """Player owns nothing → result is well above 0."""
        board = _make_minimal_board()
        player = _make_player("p1")
        result = tiles_needed_to_win(player, board)
        assert result > 0


# ---------------------------------------------------------------------------
# PET_THIEN_THAN tests
# ---------------------------------------------------------------------------

class TestThienThan:
    """Tests for handle_thien_than — ON_CANT_AFFORD_TOLL."""

    def test_thien_than_waives_toll(self):
        """handle_thien_than returns toll_waive_pet result."""
        player = _make_player()
        ctx = {"toll_amount": 50_000}
        result = handle_thien_than(player, ctx, cfg=MagicMock(), engine=MagicMock())
        assert result == {"type": "toll_waive_pet"}

    def test_thien_than_stamina_managed_by_engine(self):
        """Stamina decrement is done by engine.fire_pet, not the handler.

        Handler should NOT touch pet_stamina directly.
        """
        player = _make_player()
        player.pet_stamina = 1
        handle_thien_than(player, {}, cfg=MagicMock(), engine=MagicMock())
        # stamina should remain 1 — engine handles the decrement
        assert player.pet_stamina == 1

    def test_thien_than_registered_in_pet_handlers(self):
        """PET_THIEN_THAN must be registered in PET_HANDLERS dict."""
        assert "PET_THIEN_THAN" in PET_HANDLERS


# ---------------------------------------------------------------------------
# PET_XI_CHO tests
# ---------------------------------------------------------------------------

class TestXiCho:
    """Tests for handle_xi_cho — ON_OPPONENT_BUILD."""

    def _make_ctx(self, board, opponent):
        return {"board": board, "opponent": opponent}

    def test_xi_cho_builds_l1_when_opponent_near_win(self):
        """XiCho: places L1 on empty CITY tile when opponent needs 1 tile to win."""
        board = _make_minimal_board()
        player = _make_player("p1")
        opponent = _make_player("p2")

        # Make opponent 1 tile away: own all resorts except 1
        for pos in range(20, 23):  # own 3 of 4 resorts
            board.get_tile(pos).owner_id = "p2"
        # Resort at pos 23 unowned → tiles_needed_to_win(opponent) = 1

        ctx = self._make_ctx(board, opponent)
        result = handle_xi_cho(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert result is not None
        assert result["type"] == "xi_cho_claim"
        position = result["position"]
        # The claimed tile should now be owned by player
        claimed_tile = board.get_tile(position)
        assert claimed_tile.owner_id == "p1"
        assert claimed_tile.building_level == 1
        assert position in player.owned_properties

    def test_xi_cho_sets_acquisition_blocked_turns(self):
        """XiCho: acquisition_blocked_turns=1 on the claimed tile."""
        board = _make_minimal_board()
        player = _make_player("p1")
        opponent = _make_player("p2")

        # Opponent near win: 3/4 resorts
        for pos in range(20, 23):
            board.get_tile(pos).owner_id = "p2"

        ctx = self._make_ctx(board, opponent)
        result = handle_xi_cho(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert result is not None
        claimed_tile = board.get_tile(result["position"])
        assert claimed_tile.acquisition_blocked_turns == 1

    def test_xi_cho_does_not_fire_when_opponent_needs_more_than_one(self):
        """XiCho: returns None when opponent needs > 1 tile to win."""
        board = _make_minimal_board()
        player = _make_player("p1")
        opponent = _make_player("p2")

        # Opponent needs 2 resorts → tiles_needed_to_win = 2
        board.get_tile(20).owner_id = "p2"
        board.get_tile(21).owner_id = "p2"
        # 22 and 23 unowned

        ctx = self._make_ctx(board, opponent)
        result = handle_xi_cho(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert result is None

    def test_xi_cho_returns_none_when_no_empty_city(self):
        """XiCho: returns None when all CITY tiles are owned (no empty tile available)."""
        board = _make_minimal_board()
        player = _make_player("p1")
        opponent = _make_player("p2")

        # Own all but 1 resort
        for pos in range(20, 23):
            board.get_tile(pos).owner_id = "p2"

        # Give all CITY tiles to other players
        for tile in board.board:
            if tile.space_id == SpaceId.CITY:
                tile.owner_id = "other"

        ctx = self._make_ctx(board, opponent)
        result = handle_xi_cho(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert result is None

    def test_xi_cho_registered_in_pet_handlers(self):
        """PET_XI_CHO must be registered in PET_HANDLERS dict."""
        assert "PET_XI_CHO" in PET_HANDLERS


# ---------------------------------------------------------------------------
# PET_PHU_THU tests
# ---------------------------------------------------------------------------

class TestPhuThu:
    """Tests for handle_phu_thu — ON_OPPONENT_ACQUIRE_YOURS."""

    def _make_ctx(self, opponent, acquisition_cost):
        return {"opponent": opponent, "acquisition_cost": acquisition_cost}

    def test_phu_thu_steals_50_percent_at_tier_1(self):
        """Tier 1: steal 50% of acquisition_cost."""
        player = _make_player("p1", cash=1_000_000, pet_tier=1)
        opponent = _make_player("p2", cash=500_000)
        cost = 200_000.0

        ctx = self._make_ctx(opponent, cost)
        result = handle_phu_thu(player, ctx, cfg=MagicMock(), engine=MagicMock())

        expected_steal = cost * 0.5  # 100_000
        assert result == {"type": "phu_thu_steal", "amount": expected_steal}
        assert opponent.cash == 500_000 - expected_steal
        assert player.cash == 1_000_000 + expected_steal

    def test_phu_thu_steals_200_percent_at_tier_5(self):
        """Tier 5: steal 200% of acquisition_cost — opponent loses double."""
        player = _make_player("p1", cash=1_000_000, pet_tier=5)
        opponent = _make_player("p2", cash=600_000)
        cost = 100_000.0

        ctx = self._make_ctx(opponent, cost)
        result = handle_phu_thu(player, ctx, cfg=MagicMock(), engine=MagicMock())

        expected_steal = cost * 2.0  # 200_000
        assert result == {"type": "phu_thu_steal", "amount": expected_steal}
        assert opponent.cash == 600_000 - expected_steal
        assert player.cash == 1_000_000 + expected_steal

    def test_phu_thu_steals_100_percent_at_tier_3(self):
        """Tier 3: steal 100% of acquisition_cost."""
        player = _make_player("p1", cash=0, pet_tier=3)
        opponent = _make_player("p2", cash=300_000)
        cost = 150_000.0

        ctx = self._make_ctx(opponent, cost)
        handle_phu_thu(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert opponent.cash == 300_000 - 150_000
        assert player.cash == 150_000

    def test_phu_thu_steal_ratios_by_tier(self):
        """Verify steal ratios for all 5 tiers match spec."""
        expected = [0.5, 0.75, 1.0, 1.5, 2.0]
        assert _PHU_THU_STEAL_RATIOS == expected

    def test_phu_thu_registered_in_pet_handlers(self):
        """PET_PHU_THU must be registered in PET_HANDLERS dict."""
        assert "PET_PHU_THU" in PET_HANDLERS


# ---------------------------------------------------------------------------
# PET_TROI_CHAN tests
# ---------------------------------------------------------------------------

class TestTroiChan:
    """Tests for handle_troi_chan — ON_OPPONENT_PASS_YOURS."""

    def _make_ctx(self, opponent):
        return {"opponent": opponent}

    def test_troi_chan_sets_bound_turns(self):
        """TroiChan: sets opponent.bound_turns += 1."""
        player = _make_player("p1")
        opponent = _make_player("p2")
        assert opponent.bound_turns == 0

        ctx = self._make_ctx(opponent)
        result = handle_troi_chan(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert result == {"type": "bind_opponent", "target": "p2"}
        assert opponent.bound_turns == 1

    def test_troi_chan_bound_turns_stacks(self):
        """TroiChan: calling twice stacks bound_turns to 2."""
        player = _make_player("p1")
        opponent = _make_player("p2")

        ctx = self._make_ctx(opponent)
        handle_troi_chan(player, ctx, cfg=MagicMock(), engine=MagicMock())
        handle_troi_chan(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert opponent.bound_turns == 2

    def test_troi_chan_already_bound_stacks(self):
        """TroiChan: opponent already has bound_turns=2, adds 1 more → 3."""
        player = _make_player("p1")
        opponent = _make_player("p2")
        opponent.bound_turns = 2

        ctx = self._make_ctx(opponent)
        handle_troi_chan(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert opponent.bound_turns == 3

    def test_troi_chan_returns_correct_target_id(self):
        """TroiChan result contains target player_id."""
        player = _make_player("p1")
        opponent = _make_player("opponent_99")

        ctx = self._make_ctx(opponent)
        result = handle_troi_chan(player, ctx, cfg=MagicMock(), engine=MagicMock())

        assert result["target"] == "opponent_99"

    def test_troi_chan_registered_in_pet_handlers(self):
        """PET_TROI_CHAN must be registered in PET_HANDLERS dict."""
        assert "PET_TROI_CHAN" in PET_HANDLERS
