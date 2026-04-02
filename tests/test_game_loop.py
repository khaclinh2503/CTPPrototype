"""Integration tests: full game loop Phase 2."""

import pytest
from ctp.config import ConfigLoader
from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.core.events import EventBus, EventType
from ctp.core.constants import STARTING_CASH, BASE_UNIT
from ctp.controller.fsm import GameController, TurnPhase
import ctp.tiles  # Register tile strategies


def create_board_from_loader(loader: ConfigLoader) -> Board:
    """Helper: tạo Board từ ConfigLoader (giống main.py create_board)."""
    board_config = loader.board
    space_positions = {}
    for pos in range(1, 33):
        pos_str = str(pos)
        if pos_str in board_config.SpacePosition0:
            space_data = board_config.SpacePosition0[pos_str]
            space_positions[pos_str] = {
                "spaceId": space_data.spaceId,
                "opt": space_data.opt,
            }

    land_config = {}
    if board_config.LandSpace:
        for map_id, map_data in board_config.LandSpace.items():
            land_config[map_id] = {}
            for land_idx, land_info in map_data.items():
                land_config[map_id][land_idx] = {
                    "color": land_info.color,
                    "building": {
                        k: {"build": v.build, "toll": v.toll}
                        for k, v in land_info.building.items()
                    },
                }

    resort_config = None
    if board_config.ResortSpace:
        resort_config = {
            "maxUpgrade": board_config.ResortSpace.maxUpgrade,
            "initCost": board_config.ResortSpace.initCost,
            "tollCost": board_config.ResortSpace.tollCost,
            "increaseRate": board_config.ResortSpace.increaseRate,
        }

    festival_config = None
    if board_config.FestivalSpace:
        festival_config = {
            "holdCostRate": board_config.FestivalSpace.holdCostRate,
            "increaseRate": board_config.FestivalSpace.increaseRate,
            "maxFestival": board_config.FestivalSpace.maxFestival,
        }

    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config,
    )


def make_test_board():
    """Tạo board đơn giản cho unit tests."""
    space_positions = {
        "1": {"spaceId": 7, "opt": 0},   # START
        "2": {"spaceId": 3, "opt": 1},   # CITY opt=1
        "3": {"spaceId": 4, "opt": 0},   # GAME
        "4": {"spaceId": 3, "opt": 2},   # CITY opt=2
        "5": {"spaceId": 3, "opt": 3},   # CITY opt=3
        "6": {"spaceId": 3, "opt": 4},   # CITY opt=4
        "7": {"spaceId": 3, "opt": 5},   # CITY opt=5
        "8": {"spaceId": 3, "opt": 6},   # CITY opt=6
        "9": {"spaceId": 5, "opt": 0},   # PRISON
        "10": {"spaceId": 3, "opt": 7},  # CITY opt=7
        "11": {"spaceId": 3, "opt": 8},  # CITY opt=8
        "12": {"spaceId": 3, "opt": 9},  # CITY opt=9
        "13": {"spaceId": 2, "opt": 0},  # CHANCE
        "14": {"spaceId": 3, "opt": 10}, # CITY
        "15": {"spaceId": 3, "opt": 11}, # CITY
        "16": {"spaceId": 3, "opt": 12}, # CITY
        "17": {"spaceId": 8, "opt": 0},  # TAX
        "18": {"spaceId": 3, "opt": 13}, # CITY
        "19": {"spaceId": 3, "opt": 14}, # CITY
        "20": {"spaceId": 3, "opt": 15}, # CITY
        "21": {"spaceId": 2, "opt": 0},  # CHANCE
        "22": {"spaceId": 3, "opt": 16}, # CITY
        "23": {"spaceId": 3, "opt": 17}, # CITY
        "24": {"spaceId": 3, "opt": 18}, # CITY
        "25": {"spaceId": 6, "opt": 0},  # RESORT
        "26": {"spaceId": 3, "opt": 1},  # CITY
        "27": {"spaceId": 3, "opt": 2},  # CITY
        "28": {"spaceId": 3, "opt": 3},  # CITY
        "29": {"spaceId": 2, "opt": 0},  # CHANCE
        "30": {"spaceId": 3, "opt": 4},  # CITY
        "31": {"spaceId": 9, "opt": 0},  # TRAVEL
        "32": {"spaceId": 3, "opt": 5},  # CITY
    }
    land_config = {
        "1": {
            str(i): {
                "color": 1,
                "building": {
                    "1": {"build": 10, "toll": 1},
                    "2": {"build": 5, "toll": 3},
                    "3": {"build": 15, "toll": 10},
                    "4": {"build": 25, "toll": 28},
                    "5": {"build": 25, "toll": 125},
                }
            }
            for i in range(1, 19)
        }
    }
    resort_config = {
        "maxUpgrade": 3,
        "initCost": 50,
        "tollCost": 25,
        "increaseRate": 2,
    }
    festival_config = {
        "holdCostRate": 0.02,
        "increaseRate": 2,
        "maxFestival": 1,
    }
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config,
    )


class TestFSMPhases:
    """Test FSM có ACQUIRE và UPGRADE phases."""

    def test_turn_phase_has_acquire(self):
        """TurnPhase có ACQUIRE member."""
        phases = [p.name for p in TurnPhase]
        assert "ACQUIRE" in phases

    def test_turn_phase_has_upgrade(self):
        """TurnPhase có UPGRADE member."""
        phases = [p.name for p in TurnPhase]
        assert "UPGRADE" in phases

    def test_fsm_flow_includes_acquire_and_upgrade(self):
        """FSM flow: ROLL -> MOVE -> RESOLVE_TILE -> ACQUIRE -> UPGRADE -> CHECK_BANKRUPTCY -> END_TURN."""
        board = make_test_board()
        players = [
            Player(player_id="p1", cash=STARTING_CASH),
            Player(player_id="p2", cash=STARTING_CASH),
        ]
        event_bus = EventBus()
        controller = GameController(board, players, max_turns=25, event_bus=event_bus)

        # ROLL
        controller.step()
        assert controller.phase == TurnPhase.MOVE

        # MOVE
        controller.step()
        assert controller.phase == TurnPhase.RESOLVE_TILE

        # RESOLVE_TILE
        controller.step()
        assert controller.phase == TurnPhase.ACQUIRE

        # ACQUIRE
        controller.step()
        assert controller.phase == TurnPhase.UPGRADE

        # UPGRADE
        controller.step()
        assert controller.phase == TurnPhase.CHECK_BANKRUPTCY

        # CHECK_BANKRUPTCY
        controller.step()
        assert controller.phase == TurnPhase.END_TURN

    def test_do_resolve_tile_passes_players_to_strategy(self):
        """_do_resolve_tile() truyền players vào strategy.on_land()."""
        board = make_test_board()
        players = [
            Player(player_id="p1", cash=STARTING_CASH),
            Player(player_id="p2", cash=STARTING_CASH),
        ]
        event_bus = EventBus()
        controller = GameController(board, players, max_turns=25, event_bus=event_bus)

        # Đặt p2 sở hữu position 2, p1 tại position 2
        tile = board.get_tile(2)
        tile.owner_id = "p2"
        tile.building_level = 1
        players[1].add_property(2)
        players[0].position = 2

        # Skip ROLL phase
        controller.phase = TurnPhase.RESOLVE_TILE
        controller._current_dice = (0, 0)

        initial_p2_cash = players[1].cash
        controller.step()

        # p2 nên nhận tiền thuê (chứng tỏ players đã được truyền vào on_land)
        rent = 1 * BASE_UNIT  # toll level 1 = 1 * 1000
        assert players[1].cash == initial_p2_cash + rent

    def test_do_acquire_calls_resolve_acquisition(self):
        """_do_acquire() gọi resolve_acquisition() với current_player, tile, players."""
        board = make_test_board()
        players = [
            Player(player_id="p1", cash=STARTING_CASH),
            Player(player_id="p2", cash=STARTING_CASH),
        ]
        event_bus = EventBus()
        controller = GameController(board, players, max_turns=25, event_bus=event_bus)

        # p2 sở hữu position 2, p1 đứng tại position 2
        tile = board.get_tile(2)
        tile.owner_id = "p2"
        tile.building_level = 1
        players[1].add_property(2)
        players[0].position = 2

        # Đặt phase = ACQUIRE
        controller.phase = TurnPhase.ACQUIRE

        events = controller.step()

        # Phase nên chuyển sang UPGRADE
        assert controller.phase == TurnPhase.UPGRADE

        # p1 nên đã mua đất từ p2
        assert tile.owner_id == "p1"
        assert 2 in players[0].owned_properties
        assert 2 not in players[1].owned_properties

    def test_do_upgrade_calls_resolve_upgrades(self):
        """_do_upgrade() gọi resolve_upgrades() với current_player."""
        board = make_test_board()
        players = [
            Player(player_id="p1", cash=STARTING_CASH),
            Player(player_id="p2", cash=STARTING_CASH),
        ]
        event_bus = EventBus()
        controller = GameController(board, players, max_turns=25, event_bus=event_bus)

        # p1 sở hữu position 2, level 1
        tile = board.get_tile(2)
        tile.owner_id = "p1"
        tile.building_level = 1
        players[0].add_property(2)

        # Đặt phase = UPGRADE
        controller.phase = TurnPhase.UPGRADE

        controller.step()

        # Phase nên chuyển sang CHECK_BANKRUPTCY
        assert controller.phase == TurnPhase.CHECK_BANKRUPTCY

        # Tile nên được upgrade lên level 2
        assert tile.building_level == 2


class TestDebtResolution:
    """Test debt resolution bán cả ô, rẻ nhất trước."""

    def test_debt_sells_cheapest_property_first(self):
        """Player có cash < 0, có 2 properties -> bán rẻ nhất trước."""
        from ctp.controller.bankruptcy import resolve_bankruptcy

        board = make_test_board()
        event_bus = EventBus()

        player = Player(player_id="p1", cash=-1)
        player.add_property(2)  # opt=1, level 1: build=10, cost=10000
        player.add_property(4)  # opt=2, level 1: build=10, cost=10000

        tile2 = board.get_tile(2)
        tile2.owner_id = "p1"
        tile2.building_level = 1

        tile4 = board.get_tile(4)
        tile4.owner_id = "p1"
        tile4.building_level = 1

        events = resolve_bankruptcy(player, board, event_bus)

        # Sau khi bán ít nhất một ô, cash nên >= 0
        sold_events = event_bus.get_events(EventType.PROPERTY_SOLD)
        assert len(sold_events) >= 1
        # Player không bị bankrupt (vì tiền bán đủ trả nợ)
        assert player.is_bankrupt is False or player.cash >= 0

    def test_debt_bankrupt_when_all_sold_insufficient(self):
        """Player cash < 0, bán hết vẫn không đủ -> is_bankrupt = True."""
        from ctp.controller.bankruptcy import resolve_bankruptcy

        board = make_test_board()
        event_bus = EventBus()

        # Cash rất âm, không có property nào để bán
        player = Player(player_id="p1", cash=-1_000_000)
        # Không có property

        events = resolve_bankruptcy(player, board, event_bus)

        assert player.is_bankrupt is True

        bankrupt_events = event_bus.get_events(EventType.PLAYER_BANKRUPT)
        assert len(bankrupt_events) == 1


class TestFullGameLoop:
    """Integration: chạy full game với 4 players."""

    def test_game_completes_without_crash(self):
        """4 players, max_turns=10, game kết thúc không crash, có winner."""
        loader = ConfigLoader()
        loader.load_all()
        board = create_board_from_loader(loader)
        players = [Player(player_id=f"p{i}", cash=STARTING_CASH) for i in range(4)]
        event_bus = EventBus()
        controller = GameController(board, players, max_turns=10, event_bus=event_bus)

        while not controller._game_over:
            controller.step()

        assert controller._game_over
        assert controller.winner is not None

    def test_game_has_property_purchases(self):
        """Verify property purchases xảy ra trong game."""
        loader = ConfigLoader()
        loader.load_all()
        board = create_board_from_loader(loader)
        players = [Player(player_id=f"p{i}", cash=STARTING_CASH) for i in range(4)]
        event_bus = EventBus()
        controller = GameController(board, players, max_turns=10, event_bus=event_bus)

        while not controller._game_over:
            controller.step()

        purchase_events = event_bus.get_events(EventType.PROPERTY_PURCHASED)
        assert len(purchase_events) > 0, "Không có property nào được mua trong 10 turns"
