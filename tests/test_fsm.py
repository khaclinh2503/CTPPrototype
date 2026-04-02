"""Tests for GameController FSM."""

import pytest
from ctp.core.board import SpaceId, Tile, Board
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.controller.fsm import GameController, TurnPhase
from ctp.controller.bankruptcy import resolve_bankruptcy
from ctp.tiles import TileRegistry


@pytest.fixture
def space_positions():
    """Standard 32-tile board layout."""
    return {
        "1": {"spaceId": 7, "opt": 0},   # START
        "2": {"spaceId": 3, "opt": 1},   # LAND
        "3": {"spaceId": 4, "opt": 0},   # PRISON
        "4": {"spaceId": 3, "opt": 2},   # LAND
        "5": {"spaceId": 6, "opt": 101}, # FORTUNE_EVENT
        "6": {"spaceId": 3, "opt": 3},   # LAND
        "7": {"spaceId": 3, "opt": 4},   # LAND
        "8": {"spaceId": 3, "opt": 5},   # LAND
        "9": {"spaceId": 5, "opt": 0},   # FESTIVAL
        "10": {"spaceId": 6, "opt": 102}, # FORTUNE_EVENT
        "11": {"spaceId": 3, "opt": 6},  # LAND
        "12": {"spaceId": 3, "opt": 7},  # LAND
        "13": {"spaceId": 2, "opt": 0},  # FORTUNE_CARD
        "14": {"spaceId": 3, "opt": 8},  # LAND
        "15": {"spaceId": 6, "opt": 101}, # FORTUNE_EVENT
        "16": {"spaceId": 3, "opt": 9},  # LAND
        "17": {"spaceId": 1, "opt": 0},  # TAX
        "18": {"spaceId": 3, "opt": 10}, # LAND
        "19": {"spaceId": 6, "opt": 101}, # FORTUNE_EVENT
        "20": {"spaceId": 3, "opt": 11}, # LAND
        "21": {"spaceId": 2, "opt": 0},  # FORTUNE_CARD
        "22": {"spaceId": 3, "opt": 12}, # LAND
        "23": {"spaceId": 3, "opt": 13}, # LAND
        "24": {"spaceId": 3, "opt": 14}, # LAND
        "25": {"spaceId": 9, "opt": 0},  # RESORT
        "26": {"spaceId": 6, "opt": 102}, # FORTUNE_EVENT
        "27": {"spaceId": 3, "opt": 15}, # LAND
        "28": {"spaceId": 3, "opt": 16}, # LAND
        "29": {"spaceId": 2, "opt": 0},  # FORTUNE_CARD
        "30": {"spaceId": 3, "opt": 17}, # LAND
        "31": {"spaceId": 8, "opt": 0},  # TRAVEL
        "32": {"spaceId": 3, "opt": 18}, # LAND
    }


@pytest.fixture
def land_config():
    """LandSpace configuration."""
    return {
        "1": {
            "1": {"color": 1, "building": {"1": {"build": 10, "toll": 1}, "2": {"build": 5, "toll": 3}, "3": {"build": 15, "toll": 10}, "4": {"build": 25, "toll": 28}, "5": {"build": 25, "toll": 125}}},
            "2": {"color": 1, "building": {"1": {"build": 10, "toll": 1}, "2": {"build": 5, "toll": 3}, "3": {"build": 15, "toll": 10}, "4": {"build": 25, "toll": 28}, "5": {"build": 25, "toll": 125}}},
        }
    }


@pytest.fixture
def resort_config():
    """ResortSpace configuration."""
    return {
        "maxUpgrade": 3,
        "initCost": 50,
        "tollCost": 25,
        "increaseRate": 2
    }


@pytest.fixture
def festival_config():
    """FestivalSpace configuration."""
    return {
        "holdCostRate": 0.02,
        "increaseRate": 2,
        "maxFestival": 1
    }


@pytest.fixture
def board(space_positions, land_config, resort_config, festival_config):
    """Create a test board."""
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config
    )


@pytest.fixture
def players():
    """Create test players."""
    return [
        Player(player_id="Player1", cash=200),
        Player(player_id="Player2", cash=200),
    ]


@pytest.fixture
def event_bus():
    """Create an EventBus."""
    return EventBus()


@pytest.fixture
def controller(board, players, event_bus):
    """Create a GameController."""
    return GameController(
        board=board,
        players=players,
        max_turns=25,
        event_bus=event_bus
    )


class TestGameControllerInitialization:
    """Test GameController initialization."""

    def test_initializes_with_players(self, controller, players):
        assert len(controller.players) == 2

    def test_initial_phase_is_roll(self, controller):
        assert controller.phase == TurnPhase.ROLL

    def test_current_player_is_first(self, controller):
        assert controller.current_player.player_id == "Player1"

    def test_current_turn_is_1(self, controller):
        assert controller.current_turn == 1


class TestDiceRoll:
    """Test dice rolling."""

    def test_roll_dice_returns_2d6(self, controller):
        dice = controller.roll_dice()
        assert len(dice) == 2
        assert 1 <= dice[0] <= 6
        assert 1 <= dice[1] <= 6

    def test_roll_dice_total_in_range(self, controller):
        dice = controller.roll_dice()
        total = sum(dice)
        assert 2 <= total <= 12


class TestFSMStateTransitions:
    """Test FSM state transitions through a turn."""

    def test_step_roll_to_move(self, controller):
        """ROLL -> MOVE"""
        controller.step()
        assert controller.phase == TurnPhase.MOVE

    def test_step_move_to_resolve_tile(self, controller):
        """MOVE -> RESOLVE_TILE"""
        # First roll
        controller.step()
        # Then move
        controller.step()
        assert controller.phase == TurnPhase.RESOLVE_TILE

    def test_step_resolve_to_acquire(self, controller):
        """RESOLVE_TILE -> ACQUIRE (Phase 2: acquisition phase added)"""
        # Roll
        controller.step()
        # Move
        controller.step()
        # Resolve tile
        controller.step()
        assert controller.phase == TurnPhase.ACQUIRE

    def test_step_acquire_to_upgrade(self, controller):
        """ACQUIRE -> UPGRADE"""
        # Roll
        controller.step()
        # Move
        controller.step()
        # Resolve tile
        controller.step()
        # Acquire
        controller.step()
        assert controller.phase == TurnPhase.UPGRADE

    def test_step_upgrade_to_check_bankruptcy(self, controller):
        """UPGRADE -> CHECK_BANKRUPTCY"""
        # Roll
        controller.step()
        # Move
        controller.step()
        # Resolve tile
        controller.step()
        # Acquire
        controller.step()
        # Upgrade
        controller.step()
        assert controller.phase == TurnPhase.CHECK_BANKRUPTCY

    def test_step_check_to_end_turn(self, controller):
        """CHECK_BANKRUPTCY -> END_TURN (force non-doubles so no re-roll)"""
        controller._current_dice = (1, 2)  # ensure not doubles before check
        controller._rolled_doubles = False
        # Move
        controller.phase = TurnPhase.MOVE
        controller.step()
        # Resolve
        controller.step()
        # Acquire
        controller.step()
        # Upgrade
        controller.step()
        # Check bankruptcy
        controller.step()
        assert controller.phase == TurnPhase.END_TURN

    def test_full_turn_cycle(self, controller):
        """Complete turn cycles back to ROLL (7 steps with ACQUIRE + UPGRADE phases)."""
        # Complete one full turn for Player1: ROLL+MOVE+RESOLVE+ACQUIRE+UPGRADE+CHECK+END = 7
        for _ in range(7):
            controller.step()

        # Should be back to ROLL for next player
        assert controller.phase == TurnPhase.ROLL
        assert controller.current_player.player_id == "Player2"


class TestPositionWrapping:
    """Test position wrapping around the 32-tile board."""

    def test_position_wraps_at_32(self, controller):
        """Player at position 30 rolls 7 -> lands on position 5."""
        controller.current_player.position = 30
        # Set the dice directly and skip the ROLL phase to test MOVE
        controller._current_dice = (3, 4)  # 30 + 7 = 37 -> wraps to 5
        controller.phase = TurnPhase.MOVE  # Skip roll phase

        # Do move
        controller.step()  # MOVE

        assert controller.current_player.position == 5


class TestPassingStart:
    """Test passing Start gives bonus."""

    def test_passing_start_triggers_bonus(self, controller, event_bus):
        """Player passing Start gets passing bonus."""
        controller.current_player.position = 30
        controller.current_player.cash = 200
        controller._current_dice = (3, 4)  # 7 total -> wraps past start
        controller.phase = TurnPhase.MOVE  # Skip roll phase

        # Move (triggers passing bonus)
        controller.step()

        # Check bonus was received
        bonus_events = event_bus.get_events(EventType.BONUS_RECEIVED)
        assert len(bonus_events) > 0


class TestTerminalConditions:
    """Test game over conditions."""

    def test_game_over_when_single_player_left(self, controller):
        """Game ends when only 1 non-bankrupt player remains."""
        # Bankrupt Player2
        controller.players[1].is_bankrupt = True

        # Player1 completes a turn
        for _ in range(5):
            controller.step()

        assert controller.is_game_over() == True

    def test_game_over_at_max_turns(self, controller):
        """Game ends when current_turn >= max_turns."""
        controller.max_turns = 1
        controller.current_turn = 1

        assert controller.is_game_over() == True

    def test_get_winner_returns_highest_cash(self, controller):
        """Winner is player with highest cash."""
        controller.players[0].cash = 100
        controller.players[1].cash = 200

        winner = controller._get_winner()
        assert winner == "Player2"


class TestPrisonHandling:
    """Test prison handling in FSM."""

    def test_prison_player_skips_roll(self, controller, event_bus):
        """Player in prison (turns>1) with no money skips roll phase."""
        controller.current_player.prison_turns_remaining = 2
        controller.current_player.cash = 0  # cannot afford escape fee

        # Step should go from ROLL directly to END_TURN
        controller.step()

        assert controller.phase == TurnPhase.END_TURN
        assert controller.current_player.prison_turns_remaining == 1


class TestBankruptcyResolution:
    """Test bankruptcy resolution."""

    def test_resolve_bankruptcy_sells_properties(self, board, event_bus):
        """Bankruptcy resolution sells properties."""
        player = Player(player_id="p1", cash=-50)
        player.add_property(2)  # Add a property

        # Setup board with owned tile
        tile = board.get_tile(2)
        tile.owner_id = "p1"

        events = resolve_bankruptcy(player, board, event_bus)

        # Should have property sold event
        sold_events = event_bus.get_events(EventType.PROPERTY_SOLD)
        assert len(sold_events) > 0

    def test_resolve_bankruptcy_marks_player(self, board, event_bus):
        """Bankruptcy resolution marks player as bankrupt when unable to pay."""
        player = Player(player_id="p1", cash=-1000)  # Can't afford to pay

        events = resolve_bankruptcy(player, board, event_bus)

        # Player should be marked bankrupt
        assert player.is_bankrupt == True

        # Should have bankruptcy event
        bankrupt_events = event_bus.get_events(EventType.PLAYER_BANKRUPT)
        assert len(bankrupt_events) > 0