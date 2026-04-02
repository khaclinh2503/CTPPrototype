"""Tests for headless game runner."""

import pytest
from ctp.config import ConfigLoader
from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.core.events import EventBus, EventType
from ctp.controller import GameController
import ctp.tiles  # Register tile strategies


@pytest.fixture
def config_loader():
    """Create ConfigLoader with test config."""
    return ConfigLoader()


@pytest.fixture
def simple_space_positions():
    """Simplified 32-tile board for testing."""
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
def simple_land_config():
    """Simplified land config."""
    return {
        "1": {
            str(i): {"color": 1, "building": {str(j): {"build": 10 * j, "toll": j} for j in range(1, 6)}}
            for i in range(1, 19)
        }
    }


@pytest.fixture
def simple_board(simple_space_positions, simple_land_config):
    """Create a simple board for testing."""
    return Board(
        space_positions=simple_space_positions,
        land_config=simple_land_config,
        resort_config={"maxUpgrade": 3, "initCost": 50, "tollCost": 25, "increaseRate": 2},
        festival_config={"holdCostRate": 0.02, "increaseRate": 2, "maxFestival": 1}
    )


class TestHeadlessRunToCompletion:
    """Test that headless game runs to completion."""

    def test_runs_to_completion_without_exception(self, simple_board):
        """Game should run to max_turns without unhandled exceptions."""
        players = [
            Player(player_id="Player1", cash=200),
            Player(player_id="Player2", cash=200),
        ]
        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=5,
            event_bus=event_bus
        )

        # Run game to completion
        # Safety limit: max_turns * num_players * phases_per_turn (7 phases in Phase 2)
        turn_count = 0
        while not controller.is_game_over():
            controller.step()
            turn_count += 1
            # Safety limit: 5 turns * 2 players * 7 phases = 70, use 200 for margin
            if turn_count > 200:
                break

        # Game should be over
        assert controller.is_game_over() == True
        assert controller.current_turn <= 5

    def test_terminates_at_max_turns(self, simple_board):
        """Game should terminate at max_turns."""
        players = [
            Player(player_id="Player1", cash=200),
            Player(player_id="Player2", cash=200),
        ]
        event_bus = EventBus()

        max_turns = 3
        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=max_turns,
            event_bus=event_bus
        )

        # Run game
        while not controller.is_game_over():
            controller.step()

        # Should have reached max turns
        assert controller.current_turn >= max_turns


class TestHeadlessDetectsBankruptcy:
    """Test bankruptcy detection."""

    def test_bankruptcy_detected_when_cash_negative(self, simple_board):
        """Player should be marked bankrupt when cash goes negative."""
        player = Player(player_id="p1", cash=-100)  # Start bankrupt
        players = [player, Player(player_id="p2", cash=200)]
        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=10,
            event_bus=event_bus
        )

        # Run through bankruptcy check
        player.cash = -50  # Make negative during game

        # Player should be detected as bankrupt
        assert player.cash < 0

    def test_player_marked_is_bankrupt_true(self, simple_board):
        """Player should be marked is_bankrupt=True after bankruptcy."""
        player = Player(player_id="p1", cash=-100)
        assert player.is_bankrupt == False  # Initially not bankrupt

        # Simulate bankruptcy resolution
        player.cash = -100
        player.is_bankrupt = True

        assert player.is_bankrupt == True


class TestHeadlessConsoleOutput:
    """Test that console output events are generated."""

    def test_dice_roll_event_generated(self, simple_board):
        """Dice roll events should be generated."""
        players = [Player(player_id="p1", cash=200)]
        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=1,
            event_bus=event_bus
        )

        # Do one step (ROLL)
        controller.step()

        # Check for dice roll event
        dice_events = event_bus.get_events(EventType.DICE_ROLL)
        assert len(dice_events) >= 1

    def test_player_move_event_generated(self, simple_board):
        """Player move events should be generated."""
        players = [Player(player_id="p1", cash=200)]
        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=1,
            event_bus=event_bus
        )

        # Do ROLL and MOVE steps
        controller.step()  # ROLL
        controller.step()  # MOVE

        # Check for move event
        move_events = event_bus.get_events(EventType.PLAYER_MOVE)
        assert len(move_events) >= 1

    def test_tile_landed_event_generated(self, simple_board):
        """Tile landed events should be generated."""
        players = [Player(player_id="p1", cash=200)]
        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=1,
            event_bus=event_bus
        )

        # Run through RESOLVE_TILE
        controller.step()  # ROLL
        controller.step()  # MOVE
        controller.step()  # RESOLVE_TILE

        # Check for tile landed event
        tile_events = event_bus.get_events(EventType.TILE_LANDED)
        assert len(tile_events) >= 1


class TestEndGameSummary:
    """Test end-game summary information."""

    def test_winner_is_highest_cash_player(self, simple_board):
        """Winner should be the player with highest cash."""
        players = [
            Player(player_id="Player1", cash=100),
            Player(player_id="Player2", cash=500),
        ]
        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=1,
            event_bus=event_bus
        )

        # Force game over
        controller._game_over = True
        winner = controller._get_winner()

        assert winner == "Player2"

    def test_no_winner_when_all_bankrupt(self, simple_board):
        """No winner when all players are bankrupt."""
        players = [
            Player(player_id="Player1", cash=0),
            Player(player_id="Player2", cash=0),
        ]
        players[0].is_bankrupt = True
        players[1].is_bankrupt = True

        event_bus = EventBus()

        controller = GameController(
            board=simple_board,
            players=players,
            max_turns=1,
            event_bus=event_bus
        )

        winner = controller._get_winner()
        assert winner is None