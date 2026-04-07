"""Integration tests for toll modification skills and Moonwalk backward movement.

Gap closure tests for Phase 02.5 verification gaps:
- Gap 1: SK_MOONWALK backward movement consumed in _do_move
- Gap 2: Toll skills (BuaSet waive, NgoiSao multiply, toll_boost) apply before toll payment

Tests verify end-to-end: handler → FSM pre-toll hooks → apply_toll_modifiers → rent payment.
"""

import pytest
from unittest.mock import patch

from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.core.events import EventBus, EventType
from ctp.controller.fsm import GameController, TurnPhase
from ctp.skills.engine import SkillEngine
from ctp.skills.registry import SKILL_HANDLERS, PENDANT_HANDLERS
from ctp.skills.register_all import register_all_handlers
from ctp.config.schemas import (
    RankConfig, SkillEntry, SkillsConfig,
    PendantEntry, PendantsConfig, PendantRankRates,
    PetEntry, PetsConfig,
)


# ---------------------------------------------------------------------------
# Fixtures (same board layout as test_fsm_skills.py)
# ---------------------------------------------------------------------------

SPACE_POSITIONS = {
    "1": {"spaceId": 7, "opt": 0},    # START
    "2": {"spaceId": 3, "opt": 1},    # CITY
    "3": {"spaceId": 3, "opt": 2},    # CITY
    "4": {"spaceId": 3, "opt": 3},    # CITY
    "5": {"spaceId": 3, "opt": 4},    # CITY
    "6": {"spaceId": 3, "opt": 5},    # CITY
    "7": {"spaceId": 3, "opt": 6},    # CITY
    "8": {"spaceId": 3, "opt": 7},    # CITY
    "9": {"spaceId": 5, "opt": 0},    # PRISON
    "10": {"spaceId": 3, "opt": 8},   # CITY
    "11": {"spaceId": 3, "opt": 9},   # CITY
    "12": {"spaceId": 3, "opt": 10},  # CITY
    "13": {"spaceId": 3, "opt": 11},  # CITY
    "14": {"spaceId": 3, "opt": 12},  # CITY
    "15": {"spaceId": 3, "opt": 13},  # CITY
    "16": {"spaceId": 3, "opt": 14},  # CITY
    "17": {"spaceId": 8, "opt": 0},   # TAX
    "18": {"spaceId": 3, "opt": 15},  # CITY
    "19": {"spaceId": 3, "opt": 16},  # CITY
    "20": {"spaceId": 3, "opt": 17},  # CITY
    "21": {"spaceId": 3, "opt": 18},  # CITY
    "22": {"spaceId": 3, "opt": 19},  # CITY
    "23": {"spaceId": 3, "opt": 20},  # CITY
    "24": {"spaceId": 3, "opt": 21},  # CITY
    "25": {"spaceId": 9, "opt": 0},   # TRAVEL
    "26": {"spaceId": 3, "opt": 22},  # CITY
    "27": {"spaceId": 3, "opt": 23},  # CITY
    "28": {"spaceId": 3, "opt": 24},  # CITY
    "29": {"spaceId": 3, "opt": 25},  # CITY
    "30": {"spaceId": 3, "opt": 26},  # CITY
    "31": {"spaceId": 3, "opt": 27},  # CITY
    "32": {"spaceId": 3, "opt": 28},  # CITY
}

LAND_CONFIG = {
    "1": {
        str(i): {
            "color": ((i - 1) // 4) + 1,
            "building": {
                "1": {"build": 10, "toll": 1},
                "2": {"build": 5, "toll": 3},
                "3": {"build": 15, "toll": 10},
                "4": {"build": 25, "toll": 28},
                "5": {"build": 25, "toll": 125},
            }
        }
        for i in range(1, 29)
    }
}

PRISON_CONFIG = {
    "escapeCostRate": 0.05,
    "limitTurns": 3,
}


def _make_board():
    return Board(
        space_positions=SPACE_POSITIONS,
        land_config=LAND_CONFIG,
        prison_config=PRISON_CONFIG,
    )


def _make_skill_cfg(skill_id, trigger, base_rate=100):
    rc = RankConfig(min_star=1, base_rate=base_rate, chance=0)
    return SkillEntry(
        id=skill_id,
        name=skill_id,
        trigger=trigger,
        rank_config={"S": rc},
        always_active=True,
    )


def _make_pendant_cfg(pendant_id, triggers, rate=100):
    rates = PendantRankRates(B=rate, A=rate, S=rate, R=rate, SR=rate)
    return PendantEntry(
        id=pendant_id,
        name=pendant_id,
        triggers=triggers,
        rank_rates=rates,
        always_active=True,
    )


def _make_players(n=2, cash=1_000_000):
    names = ["A", "B", "C", "D"]
    return [Player(player_id=names[i], cash=cash) for i in range(n)]


def _make_engine(skills=None, pendants=None, pets=None):
    skills_cfg = SkillsConfig(skills=skills or [])
    pendants_cfg = PendantsConfig(pendants=pendants or [])
    pets_cfg = PetsConfig(pets=pets or [])
    engine = SkillEngine(skills_cfg, pendants_cfg, pets_cfg)
    register_all_handlers(engine)
    return engine


def _make_controller(board=None, players=None, skill_engine=None, max_turns=20):
    if board is None:
        board = _make_board()
    if players is None:
        players = _make_players(2)
    bus = EventBus()
    return GameController(
        board=board,
        players=players,
        max_turns=max_turns,
        event_bus=bus,
        starting_cash=1_000_000,
        skill_engine=skill_engine,
    )


def _setup_opponent_tile(board, position, owner_id, level=1):
    """Set up a tile as owned by owner_id with given building level."""
    tile = board.get_tile(position)
    tile.owner_id = owner_id
    tile.building_level = level
    return tile


# ---------------------------------------------------------------------------
# Test: SK_MOONWALK backward movement
# ---------------------------------------------------------------------------

class TestMoonwalkBackward:
    """SK_MOONWALK backward: _pending_direction consumed in _do_move."""

    def test_backward_decreases_position(self):
        """Moonwalk backward: player at pos 10, dice=3 → pos 7."""
        board = _make_board()
        players = _make_players(2)
        engine = _make_engine(
            skills=[_make_skill_cfg("SK_MOONWALK", "ON_ROLL")]
        )
        players[0].skills = ["SK_MOONWALK"]
        players[0].rank = "S"
        players[0].star = 1
        controller = _make_controller(board=board, players=players, skill_engine=engine)

        # Place player at position 10
        players[0].position = 10
        controller._current_dice = (2, 1)
        controller._rolled_doubles = False
        controller.phase = TurnPhase.MOVE

        # Set pending direction to backward (normally set by _resolve_roll_modifiers)
        controller._pending_direction = "backward"

        events = controller._do_move()

        assert players[0].position == 7, f"Expected pos 7, got {players[0].position}"

    def test_backward_wraps_around(self):
        """Moonwalk backward wraps: pos 2, dice=4 → pos 30."""
        board = _make_board()
        players = _make_players(2)
        engine = _make_engine()
        controller = _make_controller(board=board, players=players, skill_engine=engine)

        players[0].position = 2
        controller._current_dice = (2, 2)
        controller._rolled_doubles = True
        controller.phase = TurnPhase.MOVE
        controller._pending_direction = "backward"

        events = controller._do_move()

        assert players[0].position == 30, f"Expected pos 30, got {players[0].position}"

    def test_backward_no_start_bonus(self):
        """Backward movement never triggers Start passing bonus."""
        board = _make_board()
        players = _make_players(2)
        engine = _make_engine()
        controller = _make_controller(board=board, players=players, skill_engine=engine)

        cash_before = players[0].cash
        players[0].position = 3
        controller._current_dice = (3, 3)
        controller._rolled_doubles = True
        controller.phase = TurnPhase.MOVE
        controller._pending_direction = "backward"

        events = controller._do_move()

        # Should wrap from 3 backward 6 = pos 29, no Start bonus
        assert players[0].position == 29
        assert players[0].cash == cash_before, "Backward should not give Start bonus"

    def test_direction_resets_after_move(self):
        """_pending_direction resets to 'forward' after consumed."""
        board = _make_board()
        players = _make_players(2)
        engine = _make_engine()
        controller = _make_controller(board=board, players=players, skill_engine=engine)

        players[0].position = 10
        controller._current_dice = (1, 1)
        controller._rolled_doubles = True
        controller.phase = TurnPhase.MOVE
        controller._pending_direction = "backward"

        controller._do_move()

        assert controller._pending_direction == "forward"

    def test_forward_still_works(self):
        """Default forward movement unchanged."""
        board = _make_board()
        players = _make_players(2)
        engine = _make_engine()
        controller = _make_controller(board=board, players=players, skill_engine=engine)

        players[0].position = 5
        controller._current_dice = (2, 1)
        controller._rolled_doubles = False
        controller.phase = TurnPhase.MOVE
        # _pending_direction defaults to "forward"

        controller._do_move()

        assert players[0].position == 8


# ---------------------------------------------------------------------------
# Test: SK_BUA_SET toll waive
# ---------------------------------------------------------------------------

class TestBuaSetTollWaive:
    """SK_BUA_SET: toll_waive skips rent payment entirely."""

    def test_bua_set_waives_toll(self):
        """When BuaSet fires, player pays 0 rent."""
        board = _make_board()
        players = _make_players(2)

        # Player B owns tile at pos 5 with level 1
        players[1].add_property(5)
        _setup_opponent_tile(board, 5, "B", level=1)

        engine = _make_engine(
            skills=[_make_skill_cfg("SK_BUA_SET", "ON_LAND_OPPONENT")]
        )
        players[0].skills = ["SK_BUA_SET"]
        players[0].rank = "S"
        players[0].star = 1

        controller = _make_controller(board=board, players=players, skill_engine=engine)

        # Place player A on opponent tile
        cash_before = players[0].cash
        players[0].position = 5
        controller.phase = TurnPhase.RESOLVE_TILE

        events = controller._do_resolve_tile()

        # No rent should be paid
        rent_events = [e for e in events if e.event_type == EventType.RENT_PAID]
        assert len(rent_events) == 0, "BuaSet should waive toll — no RENT_PAID event"
        assert players[0].cash == cash_before, "Player cash should not decrease"


# ---------------------------------------------------------------------------
# Test: SK_NGOI_SAO toll multiply
# ---------------------------------------------------------------------------

class TestNgoiSaoTollMultiply:
    """SK_NGOI_SAO: toll_multiply doubles the rent."""

    def test_ngoi_sao_doubles_toll(self):
        """When NgoiSao fires for owner, visitor pays 2x rent."""
        board = _make_board()
        players = _make_players(2)

        # Player B owns tile at pos 5 with level 1
        players[1].add_property(5)
        _setup_opponent_tile(board, 5, "B", level=1)
        # Give B the NgoiSao skill
        players[1].skills = ["SK_NGOI_SAO"]
        players[1].rank = "S"
        players[1].star = 1

        engine = _make_engine(
            skills=[_make_skill_cfg("SK_NGOI_SAO", "ON_OPPONENT_LAND_YOURS")]
        )
        controller = _make_controller(board=board, players=players, skill_engine=engine)

        # Calculate expected rent: toll at level 1 = 1 * BASE_UNIT = 1000
        # With NgoiSao x2 = 2000
        from ctp.core.constants import BASE_UNIT
        base_rent = 1 * BASE_UNIT  # level 1 toll
        expected_rent = base_rent * 2  # NgoiSao doubles

        cash_before_a = players[0].cash
        cash_before_b = players[1].cash
        players[0].position = 5
        controller.phase = TurnPhase.RESOLVE_TILE

        events = controller._do_resolve_tile()

        rent_events = [e for e in events if e.event_type == EventType.RENT_PAID]
        assert len(rent_events) == 1, "Should have exactly 1 RENT_PAID event"
        assert rent_events[0].data["amount"] == expected_rent, \
            f"Expected rent {expected_rent}, got {rent_events[0].data['amount']}"
        assert players[0].cash == cash_before_a - expected_rent
        assert players[1].cash == cash_before_b + expected_rent


# ---------------------------------------------------------------------------
# Test: apply_toll_modifiers with skill params
# ---------------------------------------------------------------------------

class TestApplyTollModifiersSkillParams:
    """Unit tests for apply_toll_modifiers with skill params."""

    def test_skill_toll_waived_returns_zero(self):
        """skill_toll_waived=True → (0.0, True)."""
        from ctp.tiles._toll_modifiers import apply_toll_modifiers
        player = Player(player_id="A", cash=100_000)
        owner = Player(player_id="B", cash=100_000)
        board = _make_board()
        tile = board.get_tile(5)
        bus = EventBus()

        rent, skip = apply_toll_modifiers(
            player, owner, tile, 10_000, bus,
            skill_toll_waived=True,
        )
        assert rent == 0.0
        assert skip is True

    def test_skill_toll_multiply(self):
        """skill_toll_multiply=2 doubles rent before other modifiers."""
        from ctp.tiles._toll_modifiers import apply_toll_modifiers
        player = Player(player_id="A", cash=100_000)
        owner = Player(player_id="B", cash=100_000)
        board = _make_board()
        tile = board.get_tile(5)
        bus = EventBus()

        rent, skip = apply_toll_modifiers(
            player, owner, tile, 10_000, bus,
            skill_toll_multiply=2.0,
        )
        assert rent == 20_000
        assert skip is False

    def test_skill_toll_boost_pct(self):
        """skill_toll_boost_pct=50 increases rent by 50%."""
        from ctp.tiles._toll_modifiers import apply_toll_modifiers
        player = Player(player_id="A", cash=100_000)
        owner = Player(player_id="B", cash=100_000)
        board = _make_board()
        tile = board.get_tile(5)
        bus = EventBus()

        rent, skip = apply_toll_modifiers(
            player, owner, tile, 10_000, bus,
            skill_toll_boost_pct=50,
        )
        assert rent == 15_000
        assert skip is False

    def test_multiply_and_boost_stack(self):
        """toll_multiply and toll_boost stack: rent * multiply * (1 + boost/100)."""
        from ctp.tiles._toll_modifiers import apply_toll_modifiers
        player = Player(player_id="A", cash=100_000)
        owner = Player(player_id="B", cash=100_000)
        board = _make_board()
        tile = board.get_tile(5)
        bus = EventBus()

        rent, skip = apply_toll_modifiers(
            player, owner, tile, 10_000, bus,
            skill_toll_multiply=2.0,
            skill_toll_boost_pct=50,
        )
        # 10000 * 2 = 20000, then * 1.5 = 30000
        assert rent == 30_000
        assert skip is False

    def test_waive_takes_priority_over_multiply(self):
        """toll_waived=True ignores multiply and boost."""
        from ctp.tiles._toll_modifiers import apply_toll_modifiers
        player = Player(player_id="A", cash=100_000)
        owner = Player(player_id="B", cash=100_000)
        board = _make_board()
        tile = board.get_tile(5)
        bus = EventBus()

        rent, skip = apply_toll_modifiers(
            player, owner, tile, 10_000, bus,
            skill_toll_waived=True,
            skill_toll_multiply=2.0,
            skill_toll_boost_pct=50,
        )
        assert rent == 0.0
        assert skip is True

    def test_default_params_no_change(self):
        """Default params (waived=False, multiply=1.0, boost=0) don't affect rent."""
        from ctp.tiles._toll_modifiers import apply_toll_modifiers
        player = Player(player_id="A", cash=100_000)
        owner = Player(player_id="B", cash=100_000)
        board = _make_board()
        tile = board.get_tile(5)
        bus = EventBus()

        rent, skip = apply_toll_modifiers(
            player, owner, tile, 10_000, bus,
        )
        assert rent == 10_000
        assert skip is False
