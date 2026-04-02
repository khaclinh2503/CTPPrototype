"""Tests for ctp/core game model: SpaceId, Tile, Board, Player, GameEvent, EventBus."""

import pytest
from enum import IntEnum

# Import the modules we'll test (will fail initially)
from ctp.core.board import SpaceId, Tile, Board
from ctp.core.models import Player
from ctp.core.events import EventType, GameEvent, EventBus


class TestSpaceIdEnum:
    """Test SpaceId enum has correct values (updated for Phase 2)."""

    def test_space_id_festival(self):
        assert SpaceId.FESTIVAL == 1

    def test_space_id_chance(self):
        assert SpaceId.CHANCE == 2

    def test_space_id_city(self):
        assert SpaceId.CITY == 3

    def test_space_id_game(self):
        assert SpaceId.GAME == 4

    def test_space_id_prison(self):
        assert SpaceId.PRISON == 5

    def test_space_id_resort(self):
        assert SpaceId.RESORT == 6

    def test_space_id_start(self):
        assert SpaceId.START == 7

    def test_space_id_tax(self):
        assert SpaceId.TAX == 8

    def test_space_id_travel(self):
        assert SpaceId.TRAVEL == 9

    def test_space_id_god(self):
        assert SpaceId.GOD == 10

    def test_space_id_water_slide(self):
        assert SpaceId.WATER_SLIDE == 40


class TestTileDataclass:
    """Test Tile dataclass."""

    def test_tile_creation(self):
        tile = Tile(position=1, space_id=SpaceId.START, opt=0)
        assert tile.position == 1
        assert tile.space_id == SpaceId.START
        assert tile.opt == 0

    def test_tile_with_owner(self):
        tile = Tile(position=2, space_id=SpaceId.CITY, opt=1, owner_id="p1")
        assert tile.owner_id == "p1"

    def test_tile_with_building_level(self):
        tile = Tile(position=2, space_id=SpaceId.CITY, opt=1, building_level=3)
        assert tile.building_level == 3


class TestBoardClass:
    """Test Board class creates 32 tiles from SpacePosition0."""

    @pytest.fixture
    def space_positions(self):
        """SpacePosition0 from Board.json (simplified)."""
        return {
            "1": {"spaceId": 7, "opt": 0},    # START
            "2": {"spaceId": 3, "opt": 1},    # CITY
            "3": {"spaceId": 4, "opt": 0},    # GAME
            "4": {"spaceId": 3, "opt": 2},    # CITY
            "5": {"spaceId": 6, "opt": 101},  # RESORT
            "6": {"spaceId": 3, "opt": 3},    # CITY
            "7": {"spaceId": 3, "opt": 4},    # CITY
            "8": {"spaceId": 3, "opt": 5},    # CITY
            "9": {"spaceId": 5, "opt": 0},    # PRISON
            "10": {"spaceId": 6, "opt": 102}, # RESORT
            "11": {"spaceId": 3, "opt": 6},   # CITY
            "12": {"spaceId": 3, "opt": 7},   # CITY
            "13": {"spaceId": 2, "opt": 0},   # CHANCE
            "14": {"spaceId": 3, "opt": 8},   # CITY
            "15": {"spaceId": 6, "opt": 101}, # RESORT
            "16": {"spaceId": 3, "opt": 9},   # CITY
            "17": {"spaceId": 1, "opt": 0},   # FESTIVAL
            "18": {"spaceId": 3, "opt": 10},  # CITY
            "19": {"spaceId": 6, "opt": 101}, # RESORT
            "20": {"spaceId": 3, "opt": 11},  # CITY
            "21": {"spaceId": 2, "opt": 0},   # CHANCE
            "22": {"spaceId": 3, "opt": 12},  # CITY
            "23": {"spaceId": 3, "opt": 13},  # CITY
            "24": {"spaceId": 3, "opt": 14},  # CITY
            "25": {"spaceId": 9, "opt": 0},   # TRAVEL
            "26": {"spaceId": 6, "opt": 102}, # RESORT
            "27": {"spaceId": 3, "opt": 15},  # CITY
            "28": {"spaceId": 3, "opt": 16},  # CITY
            "29": {"spaceId": 2, "opt": 0},   # CHANCE
            "30": {"spaceId": 3, "opt": 17},  # CITY
            "31": {"spaceId": 8, "opt": 0},   # TAX
            "32": {"spaceId": 3, "opt": 18},  # CITY
        }

    @pytest.fixture
    def land_config(self):
        """LandSpace from Board.json (minimal)."""
        return {
            "1": {
                "1": {"color": 1, "building": {"1": {"build": 10, "toll": 1}}},
                "2": {"color": 1, "building": {"1": {"build": 10, "toll": 1}}},
            }
        }

    def test_board_32_tiles(self, space_positions, land_config):
        board = Board(space_positions, land_config)
        assert len(board.board) == 32

    def test_first_tile_position_1(self, space_positions, land_config):
        board = Board(space_positions, land_config)
        assert board.board[0].position == 1

    def test_last_tile_position_32(self, space_positions, land_config):
        board = Board(space_positions, land_config)
        assert board.board[31].position == 32

    def test_position_1_is_start(self, space_positions, land_config):
        board = Board(space_positions, land_config)
        assert board.board[0].space_id == SpaceId.START

    def test_position_3_is_game(self, space_positions, land_config):
        """Position 3 has spaceId=4 which is now GAME (mini-game)."""
        board = Board(space_positions, land_config)
        assert board.board[2].space_id == SpaceId.GAME

    def test_position_9_is_prison(self, space_positions, land_config):
        """Position 9 has spaceId=5 which is now PRISON."""
        board = Board(space_positions, land_config)
        assert board.board[8].space_id == SpaceId.PRISON

    def test_position_17_is_festival(self, space_positions, land_config):
        """Position 17 has spaceId=1 which is now FESTIVAL."""
        board = Board(space_positions, land_config)
        assert board.board[16].space_id == SpaceId.FESTIVAL

    def test_position_25_is_travel(self, space_positions, land_config):
        """Position 25 has spaceId=9 which is now TRAVEL."""
        board = Board(space_positions, land_config)
        assert board.board[24].space_id == SpaceId.TRAVEL

    def test_position_31_is_tax(self, space_positions, land_config):
        """Position 31 has spaceId=8 which is now TAX."""
        board = Board(space_positions, land_config)
        assert board.board[30].space_id == SpaceId.TAX

    def test_position_2_is_city(self, space_positions, land_config):
        """Position 2 has spaceId=3 which is now CITY."""
        board = Board(space_positions, land_config)
        assert board.board[1].space_id == SpaceId.CITY

    def test_city_tiles_have_opt_values(self, space_positions, land_config):
        board = Board(space_positions, land_config)
        city_tiles = [t for t in board.board if t.space_id == SpaceId.CITY]
        opt_values = [t.opt for t in city_tiles]
        assert sorted(opt_values) == list(range(1, 19))


class TestPlayerDataclass:
    """Test Player dataclass."""

    def test_player_creation(self):
        player = Player(player_id="p1", cash=200)
        assert player.player_id == "p1"
        assert player.cash == 200
        assert player.position == 1
        assert player.is_bankrupt == False
        assert player.owned_properties == []
        assert player.prison_turns_remaining == 0

    def test_player_pay_success(self):
        player = Player(player_id="p1", cash=100)
        result = player.pay(50)
        assert result == True
        assert player.cash == 50

    def test_player_pay_insufficient(self):
        player = Player(player_id="p1", cash=30)
        result = player.pay(50)
        assert result == False
        assert player.cash == 30

    def test_player_receive(self):
        player = Player(player_id="p1", cash=100)
        player.receive(100)
        assert player.cash == 200

    def test_player_can_afford(self):
        player = Player(player_id="p1", cash=100)
        assert player.can_afford(50) == True
        assert player.can_afford(150) == False


class TestGameEventAndEventBus:
    """Test GameEvent dataclass and EventBus."""

    def test_event_creation(self):
        event = GameEvent(EventType.DICE_ROLL, player_id="p1", data={"roll": 7})
        assert event.event_type == EventType.DICE_ROLL
        assert event.player_id == "p1"
        assert event.data == {"roll": 7}

    def test_eventbus_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.DICE_ROLL, handler)
        event = GameEvent(EventType.DICE_ROLL, player_id="p1", data={"roll": 5})
        bus.publish(event)

        assert len(received) == 1
        assert received[0].player_id == "p1"

    def test_eventbus_history(self):
        bus = EventBus()
        bus.publish(GameEvent(EventType.DICE_ROLL, player_id="p1"))
        bus.publish(GameEvent(EventType.PLAYER_MOVE, player_id="p1"))

        events = bus.get_events()
        assert len(events) == 2

    def test_eventbus_get_events_filtered(self):
        bus = EventBus()
        bus.publish(GameEvent(EventType.DICE_ROLL, player_id="p1"))
        bus.publish(GameEvent(EventType.DICE_ROLL, player_id="p2"))
        bus.publish(GameEvent(EventType.PLAYER_MOVE, player_id="p1"))

        dice_events = bus.get_events(EventType.DICE_ROLL)
        assert len(dice_events) == 2

        move_events = bus.get_events(EventType.PLAYER_MOVE)
        assert len(move_events) == 1

    def test_eventbus_clear(self):
        bus = EventBus()
        bus.publish(GameEvent(EventType.DICE_ROLL))
        bus.clear()
        assert len(bus.get_events()) == 0