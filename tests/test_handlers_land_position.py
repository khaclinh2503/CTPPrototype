"""Tests for handlers_land_position.py — SK_SUNG_VANG, SK_LOC_XOAY, SK_TOC_CHIEN."""

import pytest
from unittest.mock import patch, MagicMock

from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.skills.handlers_land_position import (
    handle_sung_vang,
    handle_loc_xoay,
    handle_toc_chien,
    _most_expensive_property,
)
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SPACE_POSITIONS = {str(i): {"spaceId": 7 if i == 1 else 3, "opt": i if i != 1 else 0}
                   for i in range(1, 33)}
# Set a few CITY tiles explicitly for land_config usage
SPACE_POSITIONS["2"] = {"spaceId": 3, "opt": 1}
SPACE_POSITIONS["3"] = {"spaceId": 3, "opt": 2}
SPACE_POSITIONS["4"] = {"spaceId": 3, "opt": 3}

LAND_CONFIG = {
    "1": {
        str(i): {
            "building": {
                "1": {"build": 100},
                "2": {"build": 200},
            }
        }
        for i in range(1, 19)
    }
}


@pytest.fixture
def board():
    return Board(SPACE_POSITIONS, LAND_CONFIG)


@pytest.fixture
def player():
    p = Player(player_id="p1", cash=1_000_000, rank="A", star=1)
    p.skills = ["SK_SUNG_VANG"]
    return p


@pytest.fixture
def opponent():
    return Player(player_id="p2", cash=100_000)


@pytest.fixture
def mock_cfg_sung_vang():
    """Mock SkillEntry config for SK_SUNG_VANG rank A, star 1 -> rate=28."""
    cfg = MagicMock()
    cfg.always_active = False
    return cfg


@pytest.fixture
def mock_cfg_loc_xoay():
    """Mock SkillEntry config for SK_LOC_XOAY rank A, star 1 -> rate=38."""
    cfg = MagicMock()
    cfg.always_active = False
    return cfg


@pytest.fixture
def mock_cfg_toc_chien():
    """Mock SkillEntry config for SK_TOC_CHIEN rank A, star 1 -> rate=40."""
    cfg = MagicMock()
    cfg.always_active = False
    return cfg


@pytest.fixture
def mock_engine(player):
    """Mock SkillEngine that returns a fixed rate for calc_rate."""
    engine = MagicMock()
    engine.calc_rate.return_value = 50  # 50% rate for tests
    return engine


# ---------------------------------------------------------------------------
# SK_SUNG_VANG tests
# ---------------------------------------------------------------------------

class TestSungVang:

    def test_steals_exactly_15_percent_of_opponent_cash(self, board, player, opponent, mock_cfg_sung_vang, mock_engine):
        """Effect 1 always fires: steals exactly 15% of opponent's cash."""
        initial_opponent_cash = opponent.cash   # 100_000
        initial_player_cash = player.cash       # 1_000_000
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        # Mock rate check to fail so E2 doesn't fire
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=99):
            result = handle_sung_vang(player, ctx, mock_cfg_sung_vang, mock_engine)

        expected_stolen = initial_opponent_cash * 0.15
        assert result is not None
        assert result["stolen"] == pytest.approx(expected_stolen)
        assert opponent.cash == pytest.approx(initial_opponent_cash - expected_stolen)
        assert player.cash == pytest.approx(initial_player_cash + expected_stolen)

    def test_effect2_teleports_opponent_to_most_expensive_property(self, board, player, opponent, mock_cfg_sung_vang, mock_engine):
        """Effect 2 teleports opponent to player's most expensive property."""
        # Give player two properties; pos 3 opt=2 -> build lvl2 costs 200*BASE_UNIT+100*BASE_UNIT
        player.owned_properties = [2, 3]
        board.get_tile(2).building_level = 1   # 100 * 1000 = 100_000
        board.get_tile(3).building_level = 2   # (100+200) * 1000 = 300_000
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        # Mock random to always pass rate check (randint < rate)
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=0):
            result = handle_sung_vang(player, ctx, mock_cfg_sung_vang, mock_engine)

        assert result is not None
        assert result.get("effect2") is True
        assert result.get("teleport_to") == 3  # pos 3 is most expensive
        assert opponent.position == 3

    def test_blocks_opponent_skills_and_cards_during_interaction(self, board, player, opponent, mock_cfg_sung_vang, mock_engine):
        """Opponent skills and cards are blocked during interaction."""
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=99):
            result = handle_sung_vang(player, ctx, mock_cfg_sung_vang, mock_engine)

        assert result is not None
        assert result.get("opponent_blocked") is True
        assert opponent.skills_disabled_this_turn is True
        assert opponent.cards_disabled_this_turn is True

    def test_does_not_fire_when_not_player_turn(self, board, player, opponent, mock_cfg_sung_vang, mock_engine):
        """D-51: SK_SUNG_VANG must not fire when is_player_turn=False."""
        initial_cash = opponent.cash
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": False,
        }
        result = handle_sung_vang(player, ctx, mock_cfg_sung_vang, mock_engine)
        assert result is None
        assert opponent.cash == initial_cash  # cash unchanged

    def test_effect2_skipped_when_no_properties(self, board, player, opponent, mock_cfg_sung_vang, mock_engine):
        """Effect 2 is skipped when player has no properties."""
        player.owned_properties = []
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=0):
            result = handle_sung_vang(player, ctx, mock_cfg_sung_vang, mock_engine)

        assert result is not None
        assert result.get("effect1") is True
        assert result.get("effect2") is None  # skipped


# ---------------------------------------------------------------------------
# SK_LOC_XOAY tests
# ---------------------------------------------------------------------------

class TestLocXoay:

    def test_disables_opponent_skills_and_cards(self, board, player, opponent, mock_cfg_loc_xoay, mock_engine):
        """LocXoay disables opponent skills and cards when both checks pass."""
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        # Both rate checks pass (randint=0 < 38 and 0 < 60)
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=0):
            result = handle_loc_xoay(player, ctx, mock_cfg_loc_xoay, mock_engine)

        assert result is not None
        assert result.get("skills_disabled") is True
        assert result.get("cards_disabled") is True
        assert opponent.skills_disabled_this_turn is True
        assert opponent.cards_disabled_this_turn is True

    def test_secondary_60_percent_check_blocks_when_fails(self, board, player, opponent, mock_cfg_loc_xoay, mock_engine):
        """LocXoay returns None when secondary 60% check fails."""
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        # First call (primary): 0 < 38 = pass. Second call (secondary): 70 >= 60 = fail
        call_seq = iter([0, 70])
        with patch("ctp.skills.handlers_land_position.random.randint", side_effect=call_seq):
            result = handle_loc_xoay(player, ctx, mock_cfg_loc_xoay, mock_engine)

        assert result is None
        assert opponent.skills_disabled_this_turn is False

    def test_teleports_opponent_to_most_expensive_property(self, board, player, opponent, mock_cfg_loc_xoay, mock_engine):
        """LocXoay teleports opponent to player's most expensive property."""
        player.owned_properties = [2, 4]
        board.get_tile(2).building_level = 1   # 100_000
        board.get_tile(4).building_level = 2   # 300_000
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=0):
            result = handle_loc_xoay(player, ctx, mock_cfg_loc_xoay, mock_engine)

        assert result is not None
        assert result.get("teleport_to") == 4
        assert opponent.position == 4

    def test_does_not_fire_when_not_player_turn(self, board, player, opponent, mock_cfg_loc_xoay, mock_engine):
        """D-51: SK_LOC_XOAY must not fire when is_player_turn=False."""
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": False,
        }
        result = handle_loc_xoay(player, ctx, mock_cfg_loc_xoay, mock_engine)
        assert result is None

    def test_disable_fires_even_when_no_properties(self, board, player, opponent, mock_cfg_loc_xoay, mock_engine):
        """Disable still fires even when player has no properties to teleport to."""
        player.owned_properties = []
        ctx = {
            "opponent": opponent,
            "board": board,
            "players": [player, opponent],
            "is_player_turn": True,
        }
        with patch("ctp.skills.handlers_land_position.random.randint", return_value=0):
            result = handle_loc_xoay(player, ctx, mock_cfg_loc_xoay, mock_engine)

        assert result is not None
        assert result.get("skills_disabled") is True
        assert result.get("teleport_to") is None


# ---------------------------------------------------------------------------
# SK_TOC_CHIEN tests
# ---------------------------------------------------------------------------

class TestTocChien:

    def test_returns_extra_roll_result_after_travel(self, board, player, mock_cfg_toc_chien, mock_engine):
        """TocChien returns extra_roll result after Travel tile."""
        ctx = {"board": board, "players": [player]}
        result = handle_toc_chien(player, ctx, mock_cfg_toc_chien, mock_engine)
        assert result is not None
        assert result.get("type") == "extra_roll"


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestRegistry:

    def test_all_handlers_registered_in_skill_handlers(self):
        """All 3 handlers are registered in SKILL_HANDLERS dict."""
        assert "SK_SUNG_VANG" in SKILL_HANDLERS
        assert "SK_LOC_XOAY" in SKILL_HANDLERS
        assert "SK_TOC_CHIEN" in SKILL_HANDLERS
