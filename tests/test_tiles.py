"""Tests for tile strategies.

Updated for Phase 2: SpaceId enum renamed, space_positions reflect new semantics.
"""

import pytest
from ctp.core.board import SpaceId, Tile, Board
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.tiles.registry import TileRegistry
from ctp.tiles.land import LandStrategy
from ctp.tiles.resort import ResortStrategy
from ctp.tiles.prison import PrisonStrategy
from ctp.tiles.travel import TravelStrategy
from ctp.tiles.tax import TaxStrategy
from ctp.tiles.start import StartStrategy
from ctp.tiles.festival import FestivalStrategy
from ctp.tiles.fortune import FortuneStrategy
from ctp.tiles.game import GameStrategy
from ctp.tiles.god import GodStrategy
from ctp.tiles.water_slide import WaterSlideStrategy


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def space_positions():
    """Standard 32-tile board layout matching Board.json SpacePosition0.

    SpaceId mapping (new Phase 2 enum):
      spaceId=7 → START      (position 1)
      spaceId=3 → CITY       (positions 2,4,6,7,8,11,12,14,16,18,20,22,23,24,27,28,30,32)
      spaceId=4 → GAME       (position 3)
      spaceId=6 → RESORT     (positions 5,10,15,19,26)
      spaceId=5 → PRISON     (position 9)
      spaceId=2 → CHANCE     (positions 13,21,29)
      spaceId=1 → FESTIVAL   (position 17)
      spaceId=9 → TRAVEL     (position 25)
      spaceId=8 → TAX        (position 31)
    """
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


class TestTileRegistry:
    """Test TileRegistry.resolve() returns correct strategy."""

    def test_resolve_city(self):
        strategy = TileRegistry.resolve(SpaceId.CITY)
        assert isinstance(strategy, LandStrategy)

    def test_resolve_resort(self):
        strategy = TileRegistry.resolve(SpaceId.RESORT)
        assert isinstance(strategy, ResortStrategy)

    def test_resolve_prison(self):
        strategy = TileRegistry.resolve(SpaceId.PRISON)
        assert isinstance(strategy, PrisonStrategy)

    def test_resolve_travel(self):
        strategy = TileRegistry.resolve(SpaceId.TRAVEL)
        assert isinstance(strategy, TravelStrategy)

    def test_resolve_tax(self):
        strategy = TileRegistry.resolve(SpaceId.TAX)
        assert isinstance(strategy, TaxStrategy)

    def test_resolve_start(self):
        strategy = TileRegistry.resolve(SpaceId.START)
        assert isinstance(strategy, StartStrategy)

    def test_resolve_festival(self):
        strategy = TileRegistry.resolve(SpaceId.FESTIVAL)
        assert isinstance(strategy, FestivalStrategy)

    def test_resolve_chance(self):
        strategy = TileRegistry.resolve(SpaceId.CHANCE)
        assert isinstance(strategy, FortuneStrategy)

    def test_resolve_game(self):
        strategy = TileRegistry.resolve(SpaceId.GAME)
        assert isinstance(strategy, GameStrategy)

    def test_resolve_god(self):
        strategy = TileRegistry.resolve(SpaceId.GOD)
        assert isinstance(strategy, GodStrategy)

    def test_resolve_water_slide(self):
        strategy = TileRegistry.resolve(SpaceId.WATER_SLIDE)
        assert isinstance(strategy, WaterSlideStrategy)

    def test_resolve_unknown_raises(self):
        with pytest.raises(ValueError):
            TileRegistry.resolve(999)  # Invalid SpaceId


class TestLandStrategy:
    """Test LandStrategy.on_land and on_pass (renamed CITY)."""

    def test_city_unowned_auto_buy(self, board, event_bus):
        """Landing on unowned city triggers auto-buy via GameController."""
        from ctp.controller.fsm import GameController
        from ctp.core.constants import BASE_UNIT
        # Give exactly level-1 price so player can only afford level 1 (build=10)
        player = Player(player_id="p1", cash=10 * BASE_UNIT)
        tile = board.get_tile(2)  # Position 2 is CITY with opt=1

        controller = GameController(board=board, players=[player], max_turns=1, event_bus=event_bus)
        events = controller._try_buy_property(player, tile)

        # Should have purchased property
        assert tile.owner_id == "p1"
        assert tile.building_level == 1
        assert 2 in player.owned_properties

        # Check event was published
        purchase_events = event_bus.get_events(EventType.PROPERTY_PURCHASED)
        assert len(purchase_events) == 1

    def test_city_owned_pays_rent(self, board, event_bus):
        """Landing on owned city pays rent."""
        # Setup: p1 owns the city
        tile = board.get_tile(2)
        p1 = Player(player_id="p1", cash=1_000_000)
        p1.add_property(2)
        tile.owner_id = "p1"
        tile.building_level = 1

        # p2 lands on it
        p2 = Player(player_id="p2", cash=1_000_000)
        strategy = TileRegistry.resolve(SpaceId.CITY)
        events = strategy.on_land(p2, tile, board, event_bus, players=[p1, p2])

        # p2 should have paid rent
        assert p2.cash < 1_000_000
        rent_events = event_bus.get_events(EventType.RENT_PAID)
        assert len(rent_events) == 1

    def test_city_pass_no_effect(self, board, event_bus):
        """Passing city has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(2)

        strategy = TileRegistry.resolve(SpaceId.CITY)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []
        assert player.cash == 1_000_000


class TestResortStrategy:
    """Test ResortStrategy.on_land and on_pass."""

    def test_resort_unowned_auto_buy(self, board, event_bus):
        """Landing on unowned resort triggers auto-buy."""
        from ctp.core.constants import BASE_UNIT
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(10)  # Position 10 is RESORT (spaceId=6)

        strategy = TileRegistry.resolve(SpaceId.RESORT)
        events = strategy.on_land(player, tile, board, event_bus)

        assert tile.owner_id == "p1"
        assert tile.building_level == 1

    def test_resort_pass_no_effect(self, board, event_bus):
        """Passing resort has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(10)

        strategy = TileRegistry.resolve(SpaceId.RESORT)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestPrisonStrategy:
    """Test PrisonStrategy.on_land and on_pass."""

    def test_prison_sets_prison_turns(self, board, event_bus):
        """Landing on prison sets prison_turns_remaining."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(9)  # Position 9 is PRISON (spaceId=5)

        strategy = TileRegistry.resolve(SpaceId.PRISON)
        events = strategy.on_land(player, tile, board, event_bus)

        assert player.prison_turns_remaining > 0

        prison_events = event_bus.get_events(EventType.PRISON_ENTERED)
        assert len(prison_events) == 1

    def test_prison_pass_no_effect(self, board, event_bus):
        """Passing prison has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(9)

        strategy = TileRegistry.resolve(SpaceId.PRISON)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestTravelStrategy:
    """Test TravelStrategy.on_land and on_pass."""

    def test_travel_sets_pending_flag(self, board, event_bus):
        """Landing on travel sets pending_travel — teleport happens next turn via FSM."""
        player = Player(player_id="p1", cash=1_000_000)
        player.position = 25
        tile = board.get_tile(25)

        strategy = TileRegistry.resolve(SpaceId.TRAVEL)
        events = strategy.on_land(player, tile, board, event_bus)

        assert player.pending_travel is True
        assert player.position == 25   # chưa di chuyển
        assert player.cash == 1_000_000  # chưa trả phí

    def test_travel_pass_no_effect(self, board, event_bus):
        """Passing travel has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(25)

        strategy = TileRegistry.resolve(SpaceId.TRAVEL)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestTaxStrategy:
    """Test TaxStrategy.on_land and on_pass."""

    def test_tax_deducts_cash(self, board, event_bus):
        """Landing on tax deducts cash (player with property)."""
        from ctp.core.constants import BASE_UNIT
        # Give player a property so tax > 0
        tile2 = board.get_tile(2)
        tile2.owner_id = "p1"
        tile2.building_level = 1

        player = Player(player_id="p1", cash=1_000_000)
        player.add_property(2)
        tile = board.get_tile(31)  # Position 31 is TAX (spaceId=8)

        strategy = TileRegistry.resolve(SpaceId.TAX)
        events = strategy.on_land(player, tile, board, event_bus, players=[player])

        # With property, tax > 0
        assert player.cash < 1_000_000

        tax_events = event_bus.get_events(EventType.TAX_PAID)
        assert len(tax_events) == 1

    def test_tax_pass_no_effect(self, board, event_bus):
        """Passing tax has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(31)

        strategy = TileRegistry.resolve(SpaceId.TAX)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestStartStrategy:
    """Test StartStrategy.on_land and on_pass."""

    def test_start_land_no_effect(self, board, event_bus):
        """Landing on start has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(1)  # Position 1 is START

        strategy = TileRegistry.resolve(SpaceId.START)
        events = strategy.on_land(player, tile, board, event_bus)

        assert events == []

    def test_start_pass_gives_bonus(self, board, event_bus):
        """Passing start gives passing bonus."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(1)

        strategy = TileRegistry.resolve(SpaceId.START)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert player.cash > 1_000_000

        bonus_events = event_bus.get_events(EventType.BONUS_RECEIVED)
        assert len(bonus_events) == 1


class TestFestivalStrategy:
    """Test FestivalStrategy.on_land and on_pass."""

    def test_festival_increments_and_pays(self, board, event_bus):
        """Landing on festival updates level and pays reward."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(17)  # Position 17 is FESTIVAL (spaceId=1)
        board.festival_level = 0

        strategy = TileRegistry.resolve(SpaceId.FESTIVAL)
        events = strategy.on_land(player, tile, board, event_bus)

        assert board.festival_level >= 0

        festival_events = event_bus.get_events(EventType.FESTIVAL_UPDATED)
        assert len(festival_events) == 1

    def test_festival_pass_no_effect(self, board, event_bus):
        """Passing festival has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(17)

        strategy = TileRegistry.resolve(SpaceId.FESTIVAL)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestFortuneStrategy:
    """Test FortuneStrategy.on_land and on_pass."""

    def test_chance_creates_card_event(self, board, event_bus):
        """Landing on chance creates CARD_DRAWN event with card_id."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(13)  # Position 13 is CHANCE (spaceId=2)

        strategy = TileRegistry.resolve(SpaceId.CHANCE)
        events = strategy.on_land(player, tile, board, event_bus)

        card_events = event_bus.get_events(EventType.CARD_DRAWN)
        assert len(card_events) == 1
        # Phase 02.1: FortuneStrategy now draws real cards
        assert "card_id" in card_events[0].data
        assert card_events[0].data["card_id"].startswith("IT_CA_")

    def test_chance_pass_no_effect(self, board, event_bus):
        """Passing chance has no effect."""
        player = Player(player_id="p1", cash=1_000_000)
        tile = board.get_tile(13)

        strategy = TileRegistry.resolve(SpaceId.CHANCE)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []
