"""Tests for tile strategies."""

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


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


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


class TestTileRegistry:
    """Test TileRegistry.resolve() returns correct strategy."""

    def test_resolve_land(self):
        strategy = TileRegistry.resolve(SpaceId.LAND)
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

    def test_resolve_fortune_card(self):
        strategy = TileRegistry.resolve(SpaceId.FORTUNE_CARD)
        assert isinstance(strategy, FortuneStrategy)

    def test_resolve_fortune_event(self):
        strategy = TileRegistry.resolve(SpaceId.FORTUNE_EVENT)
        assert isinstance(strategy, FortuneStrategy)

    def test_resolve_unknown_raises(self):
        with pytest.raises(ValueError):
            TileRegistry.resolve(999)  # Invalid SpaceId


class TestLandStrategy:
    """Test LandStrategy.on_land and on_pass."""

    def test_land_unowned_auto_buy(self, board, event_bus):
        """Landing on unowned land triggers auto-buy."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(2)  # Position 2 is LAND with opt=1

        strategy = TileRegistry.resolve(SpaceId.LAND)
        events = strategy.on_land(player, tile, board, event_bus)

        # Should have purchased property
        assert tile.owner_id == "p1"
        assert tile.building_level == 1
        assert 2 in player.owned_properties

        # Check event was published
        purchase_events = event_bus.get_events(EventType.PROPERTY_PURCHASED)
        assert len(purchase_events) == 1

    def test_land_owned_pays_rent(self, board, event_bus):
        """Landing on owned land pays rent."""
        # Setup: p1 owns the land
        tile = board.get_tile(2)
        p1 = Player(player_id="p1", cash=200)
        p1.add_property(2)
        tile.owner_id = "p1"
        tile.building_level = 1

        # p2 lands on it
        p2 = Player(player_id="p2", cash=200)
        strategy = TileRegistry.resolve(SpaceId.LAND)
        events = strategy.on_land(p2, tile, board, event_bus)

        # p2 should have paid rent
        assert p2.cash < 200
        rent_events = event_bus.get_events(EventType.RENT_PAID)
        assert len(rent_events) == 1

    def test_land_pass_no_effect(self, board, event_bus):
        """Passing land has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(2)

        strategy = TileRegistry.resolve(SpaceId.LAND)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []
        assert player.cash == 200


class TestResortStrategy:
    """Test ResortStrategy.on_land and on_pass."""

    def test_resort_unowned_auto_buy(self, board, event_bus):
        """Landing on unowned resort triggers auto-buy."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(25)  # Position 25 is RESORT

        strategy = TileRegistry.resolve(SpaceId.RESORT)
        events = strategy.on_land(player, tile, board, event_bus)

        assert tile.owner_id == "p1"
        assert tile.building_level == 1

    def test_resort_pass_no_effect(self, board, event_bus):
        """Passing resort has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(25)

        strategy = TileRegistry.resolve(SpaceId.RESORT)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestPrisonStrategy:
    """Test PrisonStrategy.on_land and on_pass."""

    def test_prison_sets_prison_turns(self, board, event_bus):
        """Landing on prison sets prison_turns_remaining."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(3)  # Position 3 is PRISON

        strategy = TileRegistry.resolve(SpaceId.PRISON)
        events = strategy.on_land(player, tile, board, event_bus)

        assert player.prison_turns_remaining > 0

        prison_events = event_bus.get_events(EventType.PRISON_ENTERED)
        assert len(prison_events) == 1

    def test_prison_pass_no_effect(self, board, event_bus):
        """Passing prison has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(3)

        strategy = TileRegistry.resolve(SpaceId.PRISON)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestTravelStrategy:
    """Test TravelStrategy.on_land and on_pass."""

    def test_travel_teleports_and_charges(self, board, event_bus):
        """Landing on travel teleports player and charges cost."""
        player = Player(player_id="p1", cash=200)
        player.position = 31  # Currently on TRAVEL
        tile = board.get_tile(31)

        strategy = TileRegistry.resolve(SpaceId.TRAVEL)
        events = strategy.on_land(player, tile, board, event_bus)

        # Player should be teleported to position 1 (Start)
        assert player.position == 1
        # Player should have paid travel cost
        assert player.cash < 200

    def test_travel_pass_no_effect(self, board, event_bus):
        """Passing travel has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(31)

        strategy = TileRegistry.resolve(SpaceId.TRAVEL)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestTaxStrategy:
    """Test TaxStrategy.on_land and on_pass."""

    def test_tax_deducts_cash(self, board, event_bus):
        """Landing on tax deducts cash."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(17)  # Position 17 is TAX

        strategy = TileRegistry.resolve(SpaceId.TAX)
        events = strategy.on_land(player, tile, board, event_bus)

        assert player.cash < 200

        tax_events = event_bus.get_events(EventType.TAX_PAID)
        assert len(tax_events) == 1

    def test_tax_pass_no_effect(self, board, event_bus):
        """Passing tax has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(17)

        strategy = TileRegistry.resolve(SpaceId.TAX)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestStartStrategy:
    """Test StartStrategy.on_land and on_pass."""

    def test_start_land_no_effect(self, board, event_bus):
        """Landing on start has no effect in Phase 1."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(1)  # Position 1 is START

        strategy = TileRegistry.resolve(SpaceId.START)
        events = strategy.on_land(player, tile, board, event_bus)

        assert events == []

    def test_start_pass_gives_bonus(self, board, event_bus):
        """Passing start gives passing bonus."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(1)

        strategy = TileRegistry.resolve(SpaceId.START)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert player.cash > 200

        bonus_events = event_bus.get_events(EventType.BONUS_RECEIVED)
        assert len(bonus_events) == 1


class TestFestivalStrategy:
    """Test FestivalStrategy.on_land and on_pass."""

    def test_festival_increments_and_pays(self, board, event_bus):
        """Landing on festival updates level and pays reward."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(9)  # Position 9 is FESTIVAL
        board.festival_level = 0

        strategy = TileRegistry.resolve(SpaceId.FESTIVAL)
        events = strategy.on_land(player, tile, board, event_bus)

        assert board.festival_level >= 0

        festival_events = event_bus.get_events(EventType.FESTIVAL_UPDATED)
        assert len(festival_events) == 1

    def test_festival_pass_no_effect(self, board, event_bus):
        """Passing festival has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(9)

        strategy = TileRegistry.resolve(SpaceId.FESTIVAL)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []


class TestFortuneStrategy:
    """Test FortuneStrategy.on_land and on_pass (stub)."""

    def test_fortune_creates_card_event(self, board, event_bus):
        """Landing on fortune creates CARD_DRAWN event (stub)."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(13)  # Position 13 is FORTUNE_CARD

        strategy = TileRegistry.resolve(SpaceId.FORTUNE_CARD)
        events = strategy.on_land(player, tile, board, event_bus)

        card_events = event_bus.get_events(EventType.CARD_DRAWN)
        assert len(card_events) == 1
        # Effect should NOT be applied (stub)
        assert card_events[0].data.get("effect_applied") == False

    def test_fortune_event_creates_card_event(self, board, event_bus):
        """Landing on fortune event creates CARD_DRAWN event (stub)."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(5)  # Position 5 is FORTUNE_EVENT

        strategy = TileRegistry.resolve(SpaceId.FORTUNE_EVENT)
        events = strategy.on_land(player, tile, board, event_bus)

        card_events = event_bus.get_events(EventType.CARD_DRAWN)
        assert len(card_events) == 1

    def test_fortune_pass_no_effect(self, board, event_bus):
        """Passing fortune has no effect."""
        player = Player(player_id="p1", cash=200)
        tile = board.get_tile(13)

        strategy = TileRegistry.resolve(SpaceId.FORTUNE_CARD)
        events = strategy.on_pass(player, tile, board, event_bus)

        assert events == []