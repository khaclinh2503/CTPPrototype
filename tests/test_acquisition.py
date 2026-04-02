"""Tests cho Acquisition flow và Upgrade logic."""

import pytest
from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.constants import BASE_UNIT, STARTING_CASH


@pytest.fixture
def land_config():
    """LandSpace config với building levels cho opt=1."""
    return {
        "1": {
            "1": {
                "color": 1,
                "building": {
                    "1": {"build": 10, "toll": 1},
                    "2": {"build": 5, "toll": 3},
                    "3": {"build": 15, "toll": 10},
                    "4": {"build": 25, "toll": 28},
                    "5": {"build": 25, "toll": 125},
                },
            },
            "2": {
                "color": 1,
                "building": {
                    "1": {"build": 10, "toll": 1},
                    "2": {"build": 5, "toll": 3},
                    "3": {"build": 15, "toll": 10},
                    "4": {"build": 25, "toll": 28},
                    "5": {"build": 25, "toll": 125},
                },
            },
        }
    }


@pytest.fixture
def space_positions():
    """Board layout với một số CITY tiles."""
    return {str(i): {"spaceId": 7 if i == 1 else 3, "opt": i - 1 if i != 1 else 0}
            for i in range(1, 33)}


@pytest.fixture
def board(space_positions, land_config):
    """Create test board."""
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=None,
        festival_config=None,
    )


@pytest.fixture
def event_bus():
    return EventBus()


class TestAcquisition:
    """Tests cho resolve_acquisition()."""

    def test_acquisition_player_buys_opponents_land(self, board, event_bus):
        """A dứng ô đất B (CITY, level 1, build=10) -> A trả toll, B nhận toll, A mua.

        acquire_price = build_level1(10) * BASE_UNIT(1000) * acquireRate(1.0) = 10_000
        """
        from ctp.controller.acquisition import resolve_acquisition

        player_a = Player(player_id="A", cash=STARTING_CASH)
        player_b = Player(player_id="B", cash=STARTING_CASH)

        tile = board.get_tile(2)  # opt=1, CITY tile
        tile.owner_id = "B"
        tile.building_level = 1
        player_b.add_property(2)

        initial_a_cash = player_a.cash
        initial_b_cash = player_b.cash

        events = resolve_acquisition(
            player=player_a,
            tile=tile,
            board=board,
            players=[player_a, player_b],
            event_bus=event_bus,
            acquire_rate=1.0,
        )

        # acquire_price = 10 * 1000 * 1.0 = 10_000
        acquire_price = 10 * BASE_UNIT * 1.0
        assert player_a.cash == initial_a_cash - acquire_price
        assert player_b.cash == initial_b_cash + acquire_price
        assert tile.owner_id == "A"
        assert 2 in player_a.owned_properties
        assert 2 not in player_b.owned_properties

        assert len(events) == 1
        assert events[0].event_type == EventType.PROPERTY_ACQUIRED
        assert events[0].data["position"] == 2
        assert events[0].data["from_player"] == "B"
        assert events[0].data["price"] == acquire_price

    def test_acquisition_unowned_tile_no_acquisition(self, board, event_bus):
        """Đất chưa có chủ -> không acquisition (đã mua trong RESOLVE_TILE)."""
        from ctp.controller.acquisition import resolve_acquisition

        player_a = Player(player_id="A", cash=STARTING_CASH)

        tile = board.get_tile(2)
        tile.owner_id = None
        tile.building_level = 0

        events = resolve_acquisition(
            player=player_a,
            tile=tile,
            board=board,
            players=[player_a],
            event_bus=event_bus,
        )

        assert events == []

    def test_acquisition_own_tile_no_acquisition(self, board, event_bus):
        """Đất của chính mình -> không acquisition."""
        from ctp.controller.acquisition import resolve_acquisition

        player_a = Player(player_id="A", cash=STARTING_CASH)
        player_a.add_property(2)

        tile = board.get_tile(2)
        tile.owner_id = "A"
        tile.building_level = 1

        events = resolve_acquisition(
            player=player_a,
            tile=tile,
            board=board,
            players=[player_a],
            event_bus=event_bus,
        )

        assert events == []

    def test_acquisition_max_level_no_acquisition(self, board, event_bus):
        """Đất max level (5) -> không acquisition."""
        from ctp.controller.acquisition import resolve_acquisition

        player_a = Player(player_id="A", cash=STARTING_CASH)
        player_b = Player(player_id="B", cash=STARTING_CASH)

        tile = board.get_tile(2)
        tile.owner_id = "B"
        tile.building_level = 5  # max level
        player_b.add_property(2)

        events = resolve_acquisition(
            player=player_a,
            tile=tile,
            board=board,
            players=[player_a, player_b],
            event_bus=event_bus,
        )

        assert events == []
        assert tile.owner_id == "B"  # không thay đổi owner

    def test_acquisition_insufficient_funds_no_buy(self, board, event_bus):
        """A không đủ tiền mua -> chỉ trả toll, không acquisition."""
        from ctp.controller.acquisition import resolve_acquisition

        player_a = Player(player_id="A", cash=100)  # rất ít tiền
        player_b = Player(player_id="B", cash=STARTING_CASH)

        tile = board.get_tile(2)
        tile.owner_id = "B"
        tile.building_level = 1
        player_b.add_property(2)

        events = resolve_acquisition(
            player=player_a,
            tile=tile,
            board=board,
            players=[player_a, player_b],
            event_bus=event_bus,
        )

        assert events == []
        assert tile.owner_id == "B"  # không thay đổi
        assert 2 in player_b.owned_properties  # B vẫn giữ

    def test_acquisition_event_published_to_bus(self, board, event_bus):
        """Event PROPERTY_ACQUIRED được publish lên event_bus."""
        from ctp.controller.acquisition import resolve_acquisition

        player_a = Player(player_id="A", cash=STARTING_CASH)
        player_b = Player(player_id="B", cash=STARTING_CASH)

        tile = board.get_tile(2)
        tile.owner_id = "B"
        tile.building_level = 1
        player_b.add_property(2)

        resolve_acquisition(
            player=player_a,
            tile=tile,
            board=board,
            players=[player_a, player_b],
            event_bus=event_bus,
        )

        acquired_events = event_bus.get_events(EventType.PROPERTY_ACQUIRED)
        assert len(acquired_events) == 1


class TestUpgrade:
    """Tests cho resolve_upgrades()."""

    def test_upgrade_two_level1_properties(self, board, event_bus):
        """Player có 2 ô level 1, đủ tiền -> upgrade cả 2 lên level 2."""
        from ctp.controller.upgrade import resolve_upgrades

        # level 2 build cost = 5 * BASE_UNIT = 5000 each
        initial_cash = STARTING_CASH
        player = Player(player_id="P", cash=initial_cash)
        player.add_property(2)  # opt=1
        player.add_property(3)  # opt=2

        tile2 = board.get_tile(2)
        tile2.owner_id = "P"
        tile2.building_level = 1

        tile3 = board.get_tile(3)
        tile3.owner_id = "P"
        tile3.building_level = 1

        events = resolve_upgrades(player=player, board=board, event_bus=event_bus)

        assert tile2.building_level == 2
        assert tile3.building_level == 2

        # Cost: 2 * 5 * BASE_UNIT = 10_000
        upgrade_cost_each = 5 * BASE_UNIT
        assert player.cash == initial_cash - 2 * upgrade_cost_each

        assert len(events) == 2
        for e in events:
            assert e.event_type == EventType.PROPERTY_UPGRADED
            assert e.data["new_level"] == 2

    def test_upgrade_max_level_no_upgrade(self, board, event_bus):
        """Ô đã max level (5) -> không upgrade."""
        from ctp.controller.upgrade import resolve_upgrades

        player = Player(player_id="P", cash=STARTING_CASH)
        player.add_property(2)

        tile = board.get_tile(2)
        tile.owner_id = "P"
        tile.building_level = 5  # max

        initial_cash = player.cash
        events = resolve_upgrades(player=player, board=board, event_bus=event_bus)

        assert tile.building_level == 5
        assert player.cash == initial_cash
        assert events == []

    def test_upgrade_insufficient_funds_no_upgrade(self, board, event_bus):
        """Không đủ tiền -> không upgrade (giữ ô không đổi)."""
        from ctp.controller.upgrade import resolve_upgrades

        player = Player(player_id="P", cash=1)  # gần như không có tiền
        player.add_property(2)

        tile = board.get_tile(2)
        tile.owner_id = "P"
        tile.building_level = 1

        events = resolve_upgrades(player=player, board=board, event_bus=event_bus)

        assert tile.building_level == 1  # không thay đổi
        assert player.cash == 1
        assert events == []
