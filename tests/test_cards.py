"""Tests cho FortuneStrategy (card draw) và toll modifiers (Phase 02.1 Plan 02)."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from ctp.core.board import SpaceId, Tile, Board
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.tiles.fortune import (
    FortuneStrategy,
    _load_card_pool,
    _draw_card,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def space_positions():
    """Board layout matching Board.json SpacePosition0 (map_id=1)."""
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
    """Minimal land config for testing."""
    return {"1": {str(i): {"building": {"1": {"toll": 2}}, "price": 10} for i in range(1, 19)}}


@pytest.fixture
def board_map1(space_positions, land_config):
    return Board(space_positions, land_config, map_id=1)


@pytest.fixture
def board_map2(land_config):
    """Board for map_id=2 (includes IT_CA_22, IT_CA_23, excludes IT_CA_11)."""
    # Thêm GOD tile cho map2
    sp = {
        "1": {"spaceId": 7, "opt": 0},
        "2": {"spaceId": 3, "opt": 1},
        "3": {"spaceId": 4, "opt": 0},
        "4": {"spaceId": 3, "opt": 2},
        "5": {"spaceId": 6, "opt": 101},
        "6": {"spaceId": 3, "opt": 3},
        "7": {"spaceId": 3, "opt": 4},
        "8": {"spaceId": 3, "opt": 5},
        "9": {"spaceId": 5, "opt": 0},
        "10": {"spaceId": 10, "opt": 0},  # GOD tile for map2
        "11": {"spaceId": 3, "opt": 6},
        "12": {"spaceId": 3, "opt": 7},
        "13": {"spaceId": 2, "opt": 0},
        "14": {"spaceId": 3, "opt": 8},
        "15": {"spaceId": 6, "opt": 101},
        "16": {"spaceId": 3, "opt": 9},
        "17": {"spaceId": 1, "opt": 0},
        "18": {"spaceId": 3, "opt": 10},
        "19": {"spaceId": 6, "opt": 101},
        "20": {"spaceId": 3, "opt": 11},
        "21": {"spaceId": 2, "opt": 0},
        "22": {"spaceId": 3, "opt": 12},
        "23": {"spaceId": 3, "opt": 13},
        "24": {"spaceId": 3, "opt": 14},
        "25": {"spaceId": 9, "opt": 0},
        "26": {"spaceId": 6, "opt": 102},
        "27": {"spaceId": 3, "opt": 15},
        "28": {"spaceId": 3, "opt": 16},
        "29": {"spaceId": 2, "opt": 0},
        "30": {"spaceId": 3, "opt": 17},
        "31": {"spaceId": 8, "opt": 0},
        "32": {"spaceId": 3, "opt": 18},
    }
    return Board(sp, land_config, map_id=2)


@pytest.fixture
def player():
    return Player(player_id="p1", cash=1_000_000)


@pytest.fixture
def opponent():
    return Player(player_id="p2", cash=500_000)


# ---------------------------------------------------------------------------
# Task 1: _load_card_pool Tests
# ---------------------------------------------------------------------------

class TestLoadCardPool:
    """Test _load_card_pool() filtering theo mapNotAvail và rate."""

    def test_map1_excludes_it_ca_22_and_ca_23(self):
        """IT_CA_22 và IT_CA_23 có mapNotAvail=[1,3] → không có trong map_id=1 pool."""
        pool = _load_card_pool(map_id=1)
        assert "IT_CA_22" not in pool, "IT_CA_22 phải bị lọc ra khỏi map 1"
        assert "IT_CA_23" not in pool, "IT_CA_23 phải bị lọc ra khỏi map 1"

    def test_map2_includes_it_ca_22_and_ca_23(self):
        """IT_CA_22 và IT_CA_23 có mapNotAvail=[1,3] → có trong map_id=2 pool."""
        pool = _load_card_pool(map_id=2)
        assert "IT_CA_22" in pool, "IT_CA_22 phải có trong map 2"
        assert "IT_CA_23" in pool, "IT_CA_23 phải có trong map 2"

    def test_map2_excludes_it_ca_11(self):
        """IT_CA_11 có mapNotAvail=[2] → không có trong map_id=2 pool."""
        pool = _load_card_pool(map_id=2)
        assert "IT_CA_11" not in pool, "IT_CA_11 phải bị lọc ra khỏi map 2"

    def test_pool_excludes_rate_zero_cards(self):
        """Cards với rate=0 phải bị loại khỏi pool."""
        pool = _load_card_pool(map_id=1)
        for card_id, data in pool.items():
            assert data.get("rate", 0) > 0, f"{card_id} với rate=0 không được có trong pool"

    def test_pool_is_not_empty(self):
        """Pool map_id=1 phải có ít nhất 1 card."""
        pool = _load_card_pool(map_id=1)
        assert len(pool) > 0, "Pool không được rỗng"


# ---------------------------------------------------------------------------
# Task 1: _draw_card Tests
# ---------------------------------------------------------------------------

class TestDrawCard:
    """Test _draw_card() weighted random."""

    def test_draw_returns_card_in_pool(self):
        """_draw_card() trả về card_id có trong pool."""
        pool = {"IT_CA_1": {"rate": 5}, "IT_CA_2": {"rate": 5}}
        result = _draw_card(pool)
        assert result in pool, f"Kết quả '{result}' không có trong pool"

    def test_draw_single_card_pool_always_returns_that_card(self):
        """Khi pool chỉ có 1 card, luôn rút được card đó."""
        pool = {"IT_CA_3": {"rate": 10}}
        for _ in range(10):
            assert _draw_card(pool) == "IT_CA_3"


# ---------------------------------------------------------------------------
# Task 1: Held Card Tests
# ---------------------------------------------------------------------------

class TestHeldCardBehavior:
    """Test held card lưu vào player.held_card, không apply effect ngay."""

    def test_rut_ef3_shield_luu_vao_held_card(self, board_map1, event_bus, player):
        """IT_CA_3 (EF_3 Shield) → player.held_card == 'IT_CA_3', không di chuyển."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)  # CHANCE tile at position 13
        original_position = player.position

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_3"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        assert player.held_card == "IT_CA_3", "IT_CA_3 phải được lưu vào held_card"
        assert player.position == original_position, "Held card không được di chuyển player"

    def test_rut_held_card_ghi_de_len_held_cu(self, board_map1, event_bus, player):
        """Rút thẻ held mới → overwrite thẻ cũ (1 slot, D-05)."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)
        player.held_card = "IT_CA_1"  # Angel đang giữ

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_3"):  # Shield
            strategy.on_land(player, tile, board_map1, event_bus)

        assert player.held_card == "IT_CA_3", "Thẻ mới phải overwrite thẻ cũ"

    def test_rut_ef20_angel_luu_vao_held(self, board_map1, event_bus, player):
        """IT_CA_1 (EF_20 Angel) là held card → lưu vào slot."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_1"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        assert player.held_card == "IT_CA_1"

    def test_rut_ef2_discount_luu_vao_held(self, board_map1, event_bus, player):
        """IT_CA_2 (EF_2 Discount) là held card → lưu vào slot."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_2"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        assert player.held_card == "IT_CA_2"


# ---------------------------------------------------------------------------
# Task 1: Instant Card Tests
# ---------------------------------------------------------------------------

class TestInstantCardEffects:
    """Test instant card apply effect ngay."""

    def test_ef14_go_to_start_teleport(self, board_map1, event_bus, player):
        """IT_CA_16 (EF_14 go_to_start) → player teleport đến pos 1, nhận bonus."""
        player.position = 15  # bắt đầu ở đâu đó khác
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)
        initial_cash = player.cash

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_16"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        assert player.position == 1, "Player phải di chuyển về vị trí 1 (START)"
        assert player.cash > initial_cash, "Player phải nhận bonus khi về START"
        assert player.held_card is None or player.held_card != "IT_CA_16", \
            "IT_CA_16 là instant card, không được lưu vào held_card"

    def test_ef13_go_to_prison(self, board_map1, event_bus, player):
        """IT_CA_14 (EF_13 go_to_prison) → player đến PRISON tile, prison_turns_remaining=3."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_14"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        # PRISON là position 9 trên board_map1
        assert player.position == 9, "Player phải di chuyển đến PRISON tile (pos 9)"
        assert player.prison_turns_remaining == 3, "prison_turns_remaining phải = 3"

    def test_ef16_double_toll_debuff(self, board_map1, event_bus, player):
        """IT_CA_18 (EF_16 double_toll_debuff) → player.double_toll_turns = 1."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_18"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        assert player.double_toll_turns == 1, "double_toll_turns phải = 1"

    def test_card_drawn_event_always_published(self, board_map1, event_bus, player):
        """CARD_DRAWN event phải được publish khi rút bất kỳ thẻ nào."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_3"):
            strategy.on_land(player, tile, board_map1, event_bus)

        card_events = [e for e in event_bus.get_events() if e.event_type == EventType.CARD_DRAWN]
        assert len(card_events) == 1, "Phải có đúng 1 CARD_DRAWN event"
        assert card_events[0].data["card_id"] == "IT_CA_3"

    def test_ef7_virus_on_land(self, board_map1, event_bus, player, opponent):
        """IT_CA_8 (EF_7 virus) → opponent.virus_turns = 3."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)
        players = [player, opponent]

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_8"):
            events = strategy.on_land(player, tile, board_map1, event_bus, players=players)

        assert opponent.virus_turns == 3, "Opponent phải bị virus_turns = 3"


# ---------------------------------------------------------------------------
# Task 2: Toll Modifier Tests (LandStrategy)
# ---------------------------------------------------------------------------

class TestLandTollModifiers:
    """Test toll modifier checks theo thứ tự D-44 trong LandStrategy."""

    @pytest.fixture
    def board_land(self, space_positions, land_config):
        return Board(space_positions, land_config, map_id=1)

    def test_virus_skip_toll(self, board_land, event_bus):
        """owner.virus_turns=3 → player không trả toll, virus_turns reset về 0."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=500_000)
        owner.virus_turns = 3
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        initial_visitor_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_visitor_cash, "Visitor không trả tiền khi owner bị virus"
        assert owner.virus_turns == 0, "virus_turns phải reset về 0 khi có người visit"

    def test_double_toll_doubles_rent(self, board_land, event_bus):
        """player.double_toll_turns=1 → trả toll × 2."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=0)
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        visitor.double_toll_turns = 1

        strategy = LandStrategy()
        events = strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        # Rent cơ bản = 2 * BASE_UNIT = 2000; double → 4000
        from ctp.core.constants import BASE_UNIT
        expected_rent = 2 * BASE_UNIT * 2
        assert owner.cash == expected_rent, f"Owner phải nhận {expected_rent}, nhận {owner.cash}"

    def test_angel_waive_toll(self, board_land, event_bus):
        """player.held_card='IT_CA_1' (EF_20 Angel) → toll = 0, held_card = None."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=0)
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        visitor.held_card = "IT_CA_1"  # Angel
        initial_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_cash, "Angel card phải waive toll 100%"
        assert visitor.held_card is None, "Angel card phải được consume (held_card = None)"

    def test_discount_halve_toll(self, board_land, event_bus):
        """player.held_card='IT_CA_2' (EF_2 Discount) → trả toll // 2, held_card = None."""
        from ctp.tiles.land import LandStrategy
        from ctp.core.constants import BASE_UNIT

        owner = Player(player_id="owner", cash=0)
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        visitor.held_card = "IT_CA_2"  # Discount
        initial_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        base_rent = 2 * BASE_UNIT  # toll=2, level=1
        expected_paid = base_rent // 2
        assert visitor.cash == initial_cash - expected_paid, \
            f"Discount card phải trả 50% toll ({expected_paid})"
        assert visitor.held_card is None, "Discount card phải được consume"

    def test_priority_order_virus_beats_double_toll(self, board_land, event_bus):
        """Virus > double_toll: nếu owner bị virus, player không trả gì dù có double_toll."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=0)
        owner.virus_turns = 3
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        visitor.double_toll_turns = 1
        initial_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_cash, "Virus phải có priority cao hơn double_toll"
        assert owner.virus_turns == 0

    def test_virus_clear_when_owner_visits_own_tile(self, board_land, event_bus):
        """RISK-03: chủ đất tự ghé tile của mình với virus_turns > 0 → virus vẫn được clear."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=1_000_000)
        owner.virus_turns = 3
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        strategy = LandStrategy()
        strategy.on_land(owner, tile, board_land, event_bus, players=[owner])

        assert owner.virus_turns == 0, "virus_turns phải clear khi chủ đất tự ghé tile"


# ---------------------------------------------------------------------------
# Task 2: Toll Modifier Tests (ResortStrategy)
# ---------------------------------------------------------------------------

class TestResortTollModifiers:
    """Test toll modifier checks trong ResortStrategy."""

    @pytest.fixture
    def board_resort(self, space_positions, land_config):
        resort_config = {"initCost": 10, "tollCost": 2, "increaseRate": 1.5, "maxUpgrade": 3}
        return Board(space_positions, land_config, resort_config=resort_config, map_id=1)

    def test_resort_virus_skip_toll(self, board_resort, event_bus):
        """Resort: owner.virus_turns > 0 → visitor không trả toll."""
        from ctp.tiles.resort import ResortStrategy

        owner = Player(player_id="owner", cash=0)
        owner.virus_turns = 2
        owner.add_property(5)
        tile = board_resort.get_tile(5)  # RESORT position 5
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        initial_cash = visitor.cash

        strategy = ResortStrategy()
        strategy.on_land(visitor, tile, board_resort, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_cash, "Resort: visitor không trả toll khi owner bị virus"
        assert owner.virus_turns == 0, "virus_turns phải reset"

    def test_resort_angel_waive_toll(self, board_resort, event_bus):
        """Resort: player giữ Angel card → toll = 0."""
        from ctp.tiles.resort import ResortStrategy

        owner = Player(player_id="owner", cash=0)
        owner.add_property(5)
        tile = board_resort.get_tile(5)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        visitor.held_card = "IT_CA_1"
        initial_cash = visitor.cash

        strategy = ResortStrategy()
        strategy.on_land(visitor, tile, board_resort, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_cash, "Angel card phải waive resort toll"
        assert visitor.held_card is None
