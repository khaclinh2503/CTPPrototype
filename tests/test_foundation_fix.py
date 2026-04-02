"""Tests for Phase 2 foundation fixes.

Covers: SpaceId enum fix, BASE_UNIT/STARTING_CASH constants,
calc_invested_build_cost helper, new tile stubs (Game/God/WaterSlide),
TileRegistry updates.
"""

import pytest
from ctp.core.board import SpaceId, Tile, Board
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def land_config():
    """Two land configs: opt 1 and 2, build=10 each at level 1."""
    return {
        "1": {
            "1": {"color": 1, "building": {
                "1": {"build": 10, "toll": 1},
                "2": {"build": 5, "toll": 3},
                "3": {"build": 15, "toll": 10},
                "4": {"build": 25, "toll": 28},
                "5": {"build": 25, "toll": 125}
            }},
            "2": {"color": 1, "building": {
                "1": {"build": 10, "toll": 1},
                "2": {"build": 5, "toll": 3},
                "3": {"build": 15, "toll": 10},
                "4": {"build": 25, "toll": 28},
                "5": {"build": 25, "toll": 125}
            }},
        }
    }


@pytest.fixture
def resort_config():
    return {
        "maxUpgrade": 3,
        "initCost": 50,
        "tollCost": 25,
        "increaseRate": 2
    }


@pytest.fixture
def space_positions():
    """32-tile board layout matching Board.json SpacePosition0.

    SpaceId mapping (new enum):
      spaceId=7 → START
      spaceId=3 → CITY
      spaceId=4 → GAME  (was PRISON in old enum)
      spaceId=6 → RESORT (was FORTUNE_EVENT in old enum)
      spaceId=5 → PRISON (was FESTIVAL in old enum)
      spaceId=2 → CHANCE (was FORTUNE_CARD in old enum)
      spaceId=1 → FESTIVAL (was TAX in old enum)
      spaceId=9 → TRAVEL (was RESORT in old enum)
      spaceId=8 → TAX (was TRAVEL in old enum)
    """
    return {
        "1": {"spaceId": 7, "opt": 0},    # START
        "2": {"spaceId": 3, "opt": 1},    # CITY
        "3": {"spaceId": 4, "opt": 0},    # GAME
        "4": {"spaceId": 3, "opt": 2},    # CITY
        "5": {"spaceId": 6, "opt": 101},  # RESORT (opt 101 = chance-type?)
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
def board(space_positions, land_config, resort_config):
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: SpaceId Enum Fix
# ─────────────────────────────────────────────────────────────────────────────

class TestSpaceIdEnum:
    """SpaceId enum values match new Board.json semantics."""

    def test_festival_is_1(self):
        assert SpaceId(1) == SpaceId.FESTIVAL
        assert SpaceId.FESTIVAL == 1

    def test_chance_is_2(self):
        assert SpaceId(2) == SpaceId.CHANCE
        assert SpaceId.CHANCE == 2

    def test_city_is_3(self):
        assert SpaceId(3) == SpaceId.CITY
        assert SpaceId.CITY == 3

    def test_game_is_4(self):
        assert SpaceId(4) == SpaceId.GAME
        assert SpaceId.GAME == 4

    def test_prison_is_5(self):
        assert SpaceId(5) == SpaceId.PRISON
        assert SpaceId.PRISON == 5

    def test_resort_is_6(self):
        assert SpaceId(6) == SpaceId.RESORT
        assert SpaceId.RESORT == 6

    def test_start_is_7(self):
        assert SpaceId(7) == SpaceId.START
        assert SpaceId.START == 7

    def test_tax_is_8(self):
        assert SpaceId(8) == SpaceId.TAX
        assert SpaceId.TAX == 8

    def test_travel_is_9(self):
        assert SpaceId(9) == SpaceId.TRAVEL
        assert SpaceId.TRAVEL == 9

    def test_god_is_10(self):
        assert SpaceId(10) == SpaceId.GOD
        assert SpaceId.GOD == 10

    def test_water_slide_is_40(self):
        assert SpaceId(40) == SpaceId.WATER_SLIDE
        assert SpaceId.WATER_SLIDE == 40

    def test_enum_has_11_members(self):
        assert len(SpaceId) == 11

    def test_old_names_gone(self):
        """Old names TAX=1, LAND=3, FORTUNE_CARD=2 must not exist."""
        assert not hasattr(SpaceId, 'LAND')
        assert not hasattr(SpaceId, 'FORTUNE_CARD')
        assert not hasattr(SpaceId, 'FORTUNE_EVENT')


class TestBoardLoadWithNewSpaceId:
    """Board must parse all 32 tiles without ValueError."""

    def test_board_loads_32_tiles(self, space_positions, land_config, resort_config):
        board = Board(space_positions, land_config, resort_config)
        assert len(board.board) == 32

    def test_no_value_error_on_load(self, space_positions, land_config, resort_config):
        """Should not raise ValueError for any tile."""
        board = Board(space_positions, land_config, resort_config)
        for tile in board.board:
            assert isinstance(tile.space_id, SpaceId)

    def test_position_1_is_start(self, board):
        tile = board.get_tile(1)
        assert tile.space_id == SpaceId.START

    def test_position_2_is_city(self, board):
        tile = board.get_tile(2)
        assert tile.space_id == SpaceId.CITY

    def test_position_3_is_game(self, board):
        tile = board.get_tile(3)
        assert tile.space_id == SpaceId.GAME


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    """BASE_UNIT and STARTING_CASH are correct values."""

    def test_base_unit_is_1000(self):
        from ctp.core.constants import BASE_UNIT
        assert BASE_UNIT == 1000

    def test_starting_cash_is_1_000_000(self):
        from ctp.core.constants import STARTING_CASH
        assert STARTING_CASH == 1_000_000

    def test_base_unit_relation(self):
        from ctp.core.constants import BASE_UNIT, STARTING_CASH
        assert STARTING_CASH // BASE_UNIT == 1000


class TestCalcInvestedBuildCost:
    """calc_invested_build_cost returns correct scaled values."""

    def test_city_level_1_single(self, board):
        """CITY tile at level 1: build_1 * BASE_UNIT = 10 * 1000 = 10_000."""
        from ctp.core.constants import calc_invested_build_cost, BASE_UNIT
        tile = board.get_tile(2)  # CITY opt=1
        tile.building_level = 1
        result = calc_invested_build_cost(board, 2)
        assert result == 10 * BASE_UNIT

    def test_city_level_2_cumulative(self, board):
        """CITY tile at level 2: (build_1 + build_2) * BASE_UNIT = (10+5)*1000 = 15_000."""
        from ctp.core.constants import calc_invested_build_cost, BASE_UNIT
        tile = board.get_tile(2)
        tile.building_level = 2
        result = calc_invested_build_cost(board, 2)
        assert result == (10 + 5) * BASE_UNIT

    def test_resort_tile(self, board):
        """RESORT tile: initCost * BASE_UNIT = 50 * 1000 = 50_000."""
        from ctp.core.constants import calc_invested_build_cost, BASE_UNIT
        # Position 25 is TRAVEL in new board, need to find a RESORT
        # Position 5 has spaceId=6 (RESORT), but let's use position 10
        tile = board.get_tile(10)  # spaceId=6 (RESORT)
        tile.building_level = 1
        result = calc_invested_build_cost(board, 10)
        assert result == 50 * BASE_UNIT

    def test_non_property_returns_0(self, board):
        """Non-property tiles return 0."""
        from ctp.core.constants import calc_invested_build_cost
        tile = board.get_tile(1)  # START tile
        result = calc_invested_build_cost(board, 1)
        assert result == 0

    def test_city_level_0_returns_0(self, board):
        """CITY tile with building_level=0 (unowned) returns 0."""
        from ctp.core.constants import calc_invested_build_cost
        tile = board.get_tile(2)
        tile.building_level = 0
        result = calc_invested_build_cost(board, 2)
        assert result == 0


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: New Tile Stubs via Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestNewTileStubs:
    """GameStrategy, GodStrategy, WaterSlideStrategy are registered and safe."""

    def test_registry_resolves_game(self):
        from ctp.tiles import TileRegistry
        from ctp.tiles.game import GameStrategy
        strategy = TileRegistry.resolve(SpaceId.GAME)
        assert isinstance(strategy, GameStrategy)

    def test_registry_resolves_god(self):
        from ctp.tiles import TileRegistry
        from ctp.tiles.god import GodStrategy
        strategy = TileRegistry.resolve(SpaceId.GOD)
        assert isinstance(strategy, GodStrategy)

    def test_registry_resolves_water_slide(self):
        from ctp.tiles import TileRegistry
        from ctp.tiles.water_slide import WaterSlideStrategy
        strategy = TileRegistry.resolve(SpaceId.WATER_SLIDE)
        assert isinstance(strategy, WaterSlideStrategy)

    def test_game_on_land_returns_list(self, board, event_bus):
        from ctp.tiles.game import GameStrategy
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(3)  # GAME tile
        strategy = GameStrategy()
        result = strategy.on_land(player, tile, board, event_bus)
        assert isinstance(result, list)

    def test_god_on_land_turn1_buys_city(self, board, event_bus):
        from ctp.tiles.god import GodStrategy
        from ctp.core.events import EventType
        player = Player(player_id="p1", cash=1_000_000)
        # turns_taken=0 (default) = first turn: God tile buys a CITY
        tile = Tile(position=5, space_id=SpaceId.GOD, opt=0)
        strategy = GodStrategy()
        result = strategy.on_land(player, tile, board, event_bus)
        assert len(result) == 1
        assert result[0].event_type == EventType.GOD_BUILD
        assert result[0].data["action"] == "buy"

    def test_god_on_land_turn2_no_owned_returns_empty(self, board, event_bus):
        from ctp.tiles.god import GodStrategy
        player = Player(player_id="p1", cash=1_000_000)
        player.turns_taken = 1  # not first turn
        tile = Tile(position=5, space_id=SpaceId.GOD, opt=0)
        strategy = GodStrategy()
        # No owned properties and map already has elevated tile -> upgrade path, but no owned land
        board.elevated_tile = 3  # block elevation
        result = strategy.on_land(player, tile, board, event_bus)
        assert result == []
        # cleanup
        board.elevated_tile = None

    def test_water_slide_on_land_returns_empty_list(self, board, event_bus):
        from ctp.tiles.water_slide import WaterSlideStrategy
        player = Player(player_id="p1", cash=1_000_000)
        tile = Tile(position=5, space_id=SpaceId.WATER_SLIDE, opt=0)
        strategy = WaterSlideStrategy()
        result = strategy.on_land(player, tile, board, event_bus)
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Rent Transfer
# ─────────────────────────────────────────────────────────────────────────────

class TestRentTransfer:
    """Rent goes from payer to owner."""

    def test_rent_transfers_to_owner(self, board, event_bus):
        """When A pays rent, owner B receives the exact rent amount."""
        from ctp.tiles.land import LandStrategy
        from ctp.core.constants import BASE_UNIT

        tile = board.get_tile(2)  # CITY opt=1, level 1 toll=1
        owner = Player(player_id="p1", cash=1_000_000)
        payer = Player(player_id="p2", cash=1_000_000)

        owner.add_property(2)
        tile.owner_id = "p1"
        tile.building_level = 1

        initial_owner_cash = owner.cash
        expected_rent = 1 * BASE_UNIT  # toll=1 * 1000

        strategy = LandStrategy()
        strategy.on_land(payer, tile, board, event_bus, players=[owner, payer])

        assert owner.cash == initial_owner_cash + expected_rent
        assert payer.cash == 1_000_000 - expected_rent

    def test_rent_not_paid_to_self(self, board, event_bus):
        """Owner landing on own land pays no rent."""
        from ctp.tiles.land import LandStrategy

        tile = board.get_tile(2)
        owner = Player(player_id="p1", cash=1_000_000)
        owner.add_property(2)
        tile.owner_id = "p1"
        tile.building_level = 1

        initial_cash = owner.cash
        strategy = LandStrategy()
        strategy.on_land(owner, tile, board, event_bus, players=[owner])

        assert owner.cash == initial_cash  # No change

    def test_rent_scaled_by_base_unit(self, board, event_bus):
        """Rent = toll_value * BASE_UNIT."""
        from ctp.tiles.land import LandStrategy
        from ctp.core.constants import BASE_UNIT

        tile = board.get_tile(2)  # toll=1 at level 1
        owner = Player(player_id="p1", cash=1_000_000)
        payer = Player(player_id="p2", cash=1_000_000)
        owner.add_property(2)
        tile.owner_id = "p1"
        tile.building_level = 1

        strategy = LandStrategy()
        events = strategy.on_land(payer, tile, board, event_bus, players=[owner, payer])

        rent_events = [e for e in events if e.event_type == EventType.RENT_PAID]
        assert len(rent_events) == 1
        assert rent_events[0].data["amount"] == 1 * BASE_UNIT


class TestLandPriceScaling:
    """Land purchase price = build_level_1 * BASE_UNIT."""

    def test_buy_price_uses_base_unit(self, board, event_bus):
        """Purchase price = level_1 build * BASE_UNIT = 10 * 1000 = 10_000."""
        from ctp.controller.fsm import GameController
        from ctp.core.constants import BASE_UNIT

        tile = board.get_tile(2)  # opt=1, level_1 build=10
        # Give exactly 10*BASE_UNIT so player can only afford level 1
        player = Player(player_id="p1", cash=10 * BASE_UNIT)
        controller = GameController(board=board, players=[player], max_turns=1, event_bus=event_bus)

        controller._try_buy_property(player, tile)

        assert tile.owner_id == "p1"
        assert player.cash == 0  # spent exactly level_1_build * BASE_UNIT = 10_000


class TestResortPriceScaling:
    """Resort prices use BASE_UNIT."""

    def test_resort_buy_price_uses_base_unit(self, board, event_bus):
        """Resort purchase = initCost * BASE_UNIT = 50 * 1000 = 50_000."""
        from ctp.tiles.resort import ResortStrategy
        from ctp.core.constants import BASE_UNIT

        tile = board.get_tile(10)  # RESORT tile (spaceId=6)
        player = Player(player_id="p1", cash=1_000_000)

        strategy = ResortStrategy()
        strategy.on_land(player, tile, board, event_bus)

        assert tile.owner_id == "p1"
        assert player.cash == 1_000_000 - 50 * BASE_UNIT

    def test_resort_toll_uses_base_unit(self, board, event_bus):
        """Resort toll = int(tollCost * increaseRate^level) * BASE_UNIT."""
        from ctp.tiles.resort import ResortStrategy
        from ctp.core.constants import BASE_UNIT

        tile = board.get_tile(10)
        owner = Player(player_id="p1", cash=1_000_000)
        payer = Player(player_id="p2", cash=1_000_000)
        owner.add_property(10)
        tile.owner_id = "p1"
        tile.building_level = 1

        # toll = int(25 * 2^1) * 1000 = 50 * 1000 = 50_000
        expected_toll = int(25 * (2 ** 1)) * BASE_UNIT

        strategy = ResortStrategy()
        strategy.on_land(payer, tile, board, event_bus, players=[owner, payer])

        assert payer.cash == 1_000_000 - expected_toll


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Tax Fix
# ─────────────────────────────────────────────────────────────────────────────

class TestTaxFix:
    """TaxSpace calculates tax as 10% of total invested build cost."""

    def test_tax_with_two_properties(self, board, event_bus):
        """Player with 2 properties both at level 1 (build=10 each):
        tax = 0.1 * (10 + 10) * 1000 = 2000."""
        from ctp.tiles.tax import TaxStrategy
        from ctp.core.constants import BASE_UNIT

        # Setup: player owns positions 2 and 4, both CITY opt=1 and opt=2
        tile2 = board.get_tile(2)  # CITY opt=1, level 1
        tile4 = board.get_tile(4)  # CITY opt=2, level 1
        tile2.owner_id = "p1"
        tile2.building_level = 1
        tile4.owner_id = "p1"
        tile4.building_level = 1

        player = Player(player_id="p1", cash=1_000_000)
        player.add_property(2)
        player.add_property(4)

        # Find TAX tile (position 31, spaceId=8)
        tax_tile = board.get_tile(31)
        strategy = TaxStrategy()
        strategy.on_land(player, tax_tile, board, event_bus, players=[player])

        expected_tax = int(0.1 * (10 + 10) * BASE_UNIT)
        assert player.cash == 1_000_000 - expected_tax

    def test_tax_no_properties_is_zero(self, board, event_bus):
        """Player with no properties pays 0 tax."""
        from ctp.tiles.tax import TaxStrategy

        player = Player(player_id="p1", cash=1_000_000)
        tax_tile = board.get_tile(31)

        strategy = TaxStrategy()
        strategy.on_land(player, tax_tile, board, event_bus, players=[player])

        assert player.cash == 1_000_000  # No tax deducted


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Start Bonus Fix
# ─────────────────────────────────────────────────────────────────────────────

class TestStartBonus:
    """StartSpace passing bonus is fixed at 15% * STARTING_CASH."""

    def test_passing_bonus_is_fixed_150k(self, board, event_bus):
        """Bonus = 0.15 * 1_000_000 = 150_000, regardless of player cash."""
        from ctp.tiles.start import StartStrategy
        from ctp.core.constants import STARTING_CASH

        player = Player(player_id="p1", cash=500_000)  # Not STARTING_CASH
        start_tile = board.get_tile(1)

        strategy = StartStrategy()
        strategy.on_pass(player, start_tile, board, event_bus)

        expected_bonus = int(0.15 * STARTING_CASH)  # = 150_000
        assert player.cash == 500_000 + expected_bonus

    def test_bonus_same_regardless_of_current_cash(self, board, event_bus):
        """Two players with different cash get same bonus."""
        from ctp.tiles.start import StartStrategy

        player_rich = Player(player_id="p1", cash=2_000_000)
        player_poor = Player(player_id="p2", cash=100_000)
        start_tile = board.get_tile(1)
        strategy = StartStrategy()

        bus1 = EventBus()
        bus2 = EventBus()
        strategy.on_pass(player_rich, start_tile, board, bus1)
        strategy.on_pass(player_poor, start_tile, board, bus2)

        bonus_rich = player_rich.cash - 2_000_000
        bonus_poor = player_poor.cash - 100_000
        assert bonus_rich == bonus_poor


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Bankruptcy Fix
# ─────────────────────────────────────────────────────────────────────────────

class TestBankruptcyFix:
    """Bankruptcy uses calc_invested_build_cost, sells cheapest first."""

    def test_sell_value_is_half_invested_cost(self, board, event_bus):
        """Sell value = 0.5 * invested_build_cost (not all 5 levels)."""
        from ctp.controller.bankruptcy import resolve_bankruptcy
        from ctp.core.constants import BASE_UNIT

        # Player has 1 property at level 1 (build=10, invested = 10*1000=10000)
        tile = board.get_tile(2)  # CITY opt=1
        tile.owner_id = "p1"
        tile.building_level = 1

        player = Player(player_id="p1", cash=-1)  # In debt
        player.add_property(2)

        resolve_bankruptcy(player, board, event_bus)

        # sell_value = 0.5 * 10 * 1000 = 5000
        expected_sell = int(0.5 * 10 * BASE_UNIT)
        # cash started at -1, should be -1 + 5000 = 4999
        assert player.cash == -1 + expected_sell

    def test_sells_cheapest_property_first(self, board, event_bus):
        """Player with two properties sells the cheaper one first."""
        from ctp.controller.bankruptcy import resolve_bankruptcy
        from ctp.core.constants import BASE_UNIT

        # Set up two properties: pos 2 (level 1, build=10) and pos 4 (level 2, build=10+5=15)
        tile2 = board.get_tile(2)
        tile2.owner_id = "p1"
        tile2.building_level = 1  # invested = 10 * 1000

        tile4 = board.get_tile(4)
        tile4.owner_id = "p1"
        tile4.building_level = 2  # invested = (10+5) * 1000 = 15000

        player = Player(player_id="p1", cash=-1)
        player.add_property(2)
        player.add_property(4)

        resolve_bankruptcy(player, board, event_bus)

        # Cheapest is position 2 (10k invested → 5k sell value)
        # After selling pos 2: cash = -1 + 5000 = 4999 (positive, stop selling)
        assert 2 not in player.owned_properties
        assert 4 in player.owned_properties

    def test_bankruptcy_only_invested_levels(self, board, event_bus):
        """Sell value based only on levels 1..building_level, not all 5."""
        from ctp.controller.bankruptcy import resolve_bankruptcy
        from ctp.core.constants import BASE_UNIT

        tile = board.get_tile(2)  # CITY: level 1 build=10, level 2 build=5
        tile.owner_id = "p1"
        tile.building_level = 2  # Invested levels 1 and 2

        player = Player(player_id="p1", cash=-1)
        player.add_property(2)

        resolve_bankruptcy(player, board, event_bus)

        # sell_value = 0.5 * (10+5) * 1000 = 7500
        expected_sell = int(0.5 * (10 + 5) * BASE_UNIT)
        assert player.cash == -1 + expected_sell
