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
    """Board layout matching Board.json SpacePosition7 (map_id=1). TAX tại pos 31."""
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
    """Board for map_id=2 — SpacePosition1 từ Board.json (GOD tại pos 5,13,21,29)."""
    sp = {
        "1":  {"spaceId": 7,  "opt": 0},
        "2":  {"spaceId": 3,  "opt": 1},
        "3":  {"spaceId": 4,  "opt": 2},
        "4":  {"spaceId": 3,  "opt": 2},
        "5":  {"spaceId": 10, "opt": 1},   # GOD
        "6":  {"spaceId": 3,  "opt": 3},
        "7":  {"spaceId": 3,  "opt": 4},
        "8":  {"spaceId": 6,  "opt": 101},
        "9":  {"spaceId": 5,  "opt": 0},   # PRISON
        "10": {"spaceId": 2,  "opt": 0},   # CHANCE
        "11": {"spaceId": 3,  "opt": 5},
        "12": {"spaceId": 3,  "opt": 6},
        "13": {"spaceId": 10, "opt": 2},   # GOD
        "14": {"spaceId": 3,  "opt": 7},
        "15": {"spaceId": 6,  "opt": 101},
        "16": {"spaceId": 3,  "opt": 8},
        "17": {"spaceId": 1,  "opt": 0},   # FESTIVAL
        "18": {"spaceId": 3,  "opt": 9},
        "19": {"spaceId": 2,  "opt": 0},   # CHANCE
        "20": {"spaceId": 3,  "opt": 10},
        "21": {"spaceId": 10, "opt": 3},   # GOD
        "22": {"spaceId": 3,  "opt": 11},
        "23": {"spaceId": 3,  "opt": 12},
        "24": {"spaceId": 6,  "opt": 101},
        "25": {"spaceId": 9,  "opt": 0},   # TRAVEL
        "26": {"spaceId": 3,  "opt": 13},
        "27": {"spaceId": 2,  "opt": 0},   # CHANCE
        "28": {"spaceId": 3,  "opt": 14},
        "29": {"spaceId": 10, "opt": 4},   # GOD
        "30": {"spaceId": 3,  "opt": 15},
        "31": {"spaceId": 6,  "opt": 102},
        "32": {"spaceId": 3,  "opt": 16},
    }
    return Board(sp, land_config, map_id=2)


@pytest.fixture
def board_map3(land_config):
    """Board for map_id=3 — SpacePosition6 từ Board.json (WATER_SLIDE tại pos 2,10,18,26)."""
    sp = {
        "1":  {"spaceId": 7,  "opt": 0},
        "2":  {"spaceId": 40, "opt": 1},   # WATER_SLIDE
        "3":  {"spaceId": 3,  "opt": 1},
        "4":  {"spaceId": 4,  "opt": 2},
        "5":  {"spaceId": 3,  "opt": 2},
        "6":  {"spaceId": 3,  "opt": 3},
        "7":  {"spaceId": 3,  "opt": 4},
        "8":  {"spaceId": 6,  "opt": 101},
        "9":  {"spaceId": 1,  "opt": 0},
        "10": {"spaceId": 40, "opt": 2},   # WATER_SLIDE
        "11": {"spaceId": 2,  "opt": 0},   # CHANCE
        "12": {"spaceId": 3,  "opt": 5},
        "13": {"spaceId": 3,  "opt": 6},
        "14": {"spaceId": 3,  "opt": 7},
        "15": {"spaceId": 6,  "opt": 101},
        "16": {"spaceId": 3,  "opt": 8},
        "17": {"spaceId": 5,  "opt": 0},   # PRISON
        "18": {"spaceId": 40, "opt": 3},   # WATER_SLIDE
        "19": {"spaceId": 3,  "opt": 9},
        "20": {"spaceId": 2,  "opt": 0},   # CHANCE
        "21": {"spaceId": 3,  "opt": 10},
        "22": {"spaceId": 3,  "opt": 11},
        "23": {"spaceId": 3,  "opt": 12},
        "24": {"spaceId": 6,  "opt": 101},
        "25": {"spaceId": 9,  "opt": 0},   # TRAVEL
        "26": {"spaceId": 40, "opt": 4},   # WATER_SLIDE
        "27": {"spaceId": 3,  "opt": 13},
        "28": {"spaceId": 2,  "opt": 0},   # CHANCE
        "29": {"spaceId": 3,  "opt": 14},
        "30": {"spaceId": 3,  "opt": 15},
        "31": {"spaceId": 6,  "opt": 102},
        "32": {"spaceId": 3,  "opt": 16},
    }
    return Board(sp, land_config, map_id=3)


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


    def test_it_ca_11_map_availability(self):
        """IT_CA_11 có trong map 1 (có TAX), không có trong map 2 và 3 (không có TAX)."""
        assert "IT_CA_11" in _load_card_pool(map_id=1), "IT_CA_11 phải có trong map 1"
        for map_id in [2, 3]:
            pool = _load_card_pool(map_id=map_id)
            assert "IT_CA_11" not in pool, f"IT_CA_11 không được có trong map {map_id}"

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
        """IT_CA_14 (EF_13 go_to_prison) → player đến PRISON tile, prison_turns_remaining > 0."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_14"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        # PRISON là position 9 trên board_map1
        assert player.position == 9, "Player phải di chuyển đến PRISON tile (pos 9)"
        assert player.prison_turns_remaining > 0, "player phải bị giam (prison_turns_remaining > 0)"

    def test_ef16_double_toll_debuff(self, board_map1, event_bus, player):
        """IT_CA_18 (EF_16 double_toll_debuff) → player.double_toll_turns = 2.

        Giá trị 2 (không phải 1) vì FSM decrements ở đầu ROLL trước khi di chuyển,
        nên cần value=2 để sau decrement còn 1 và fire khi trả toll.
        """
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_18"):
            events = strategy.on_land(player, tile, board_map1, event_bus)

        assert player.double_toll_turns == 2, "double_toll_turns phải = 2 (sẽ = 1 sau ROLL decrement)"

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
        """IT_CA_8 (EF_7 virus) → tile.toll_debuff_turns=5, toll_debuff_rate=0.0 (tile-level)."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        # Opponent sở hữu một CITY tile tại pos 2
        opponent.add_property(2)
        city_tile = board_map1.get_tile(2)
        city_tile.owner_id = opponent.player_id
        city_tile.building_level = 1

        players = [player, opponent]
        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_8"):
            events = strategy.on_land(player, tile, board_map1, event_bus, players=players)

        assert city_tile.toll_debuff_turns == 5, "EF_7: tile.toll_debuff_turns phải = 5"
        assert city_tile.toll_debuff_rate == 0.0, "EF_7 (virus): toll_debuff_rate phải = 0.0 (miễn phí)"

    def test_ef8_yellow_sand_on_land(self, board_map1, event_bus, player, opponent):
        """IT_CA_9 (EF_8 yellow_sand) → tile.toll_debuff_turns=5, toll_debuff_rate=0.5 (tile-level)."""
        strategy = FortuneStrategy()
        tile = board_map1.get_tile(13)

        opponent.add_property(2)
        city_tile = board_map1.get_tile(2)
        city_tile.owner_id = opponent.player_id
        city_tile.building_level = 1

        players = [player, opponent]
        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_9"):
            strategy.on_land(player, tile, board_map1, event_bus, players=players)

        assert city_tile.toll_debuff_turns == 5, "EF_8: tile.toll_debuff_turns phải = 5"
        assert city_tile.toll_debuff_rate == 0.5, "EF_8 (yellow_sand): toll_debuff_rate phải = 0.5 (giảm 50%)"

    def test_ef21_go_to_god(self, board_map2, event_bus, player):
        """IT_CA_22 (EF_21) → player teleport đến GOD tile gần nhất.
        Player ở pos 10 (CHANCE) → GOD gần nhất theo chiều tiến là pos 13.
        """
        strategy = FortuneStrategy()
        tile = board_map2.get_tile(10)  # CHANCE tile trên Map 2
        player.position = 10

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_22"):
            strategy.on_land(player, tile, board_map2, event_bus)

        assert player.position == 13, "Player phải được teleport đến GOD tile gần nhất (pos 13)"
        god_events = [e for e in event_bus.get_events()
                      if e.event_type == EventType.CARD_EFFECT_GO_TO_GOD]
        assert len(god_events) == 1
        assert god_events[0].data["target_position"] == 13

    def test_ef30_go_to_water_slide(self, board_map3, event_bus, player):
        """IT_CA_30 (EF_30) → player teleport đến WATER_SLIDE tile gần nhất.
        Player ở pos 11 (CHANCE) → WATER_SLIDE gần nhất theo chiều tiến là pos 18.
        """
        strategy = FortuneStrategy()
        tile = board_map3.get_tile(11)  # CHANCE tile trên Map 3
        player.position = 11

        with patch("ctp.tiles.fortune._draw_card", return_value="IT_CA_30"):
            strategy.on_land(player, tile, board_map3, event_bus)

        assert player.position == 18, "Player phải được teleport đến WATER_SLIDE gần nhất (pos 18)"
        ws_events = [e for e in event_bus.get_events()
                     if e.event_type == EventType.CARD_EFFECT_GO_TO_WATER_SLIDE]
        assert len(ws_events) == 1
        assert ws_events[0].data["target_position"] == 18


# ---------------------------------------------------------------------------
# Task 2: Toll Modifier Tests (LandStrategy)
# ---------------------------------------------------------------------------

class TestLandTollModifiers:
    """Test toll modifier checks theo thứ tự D-44 trong LandStrategy."""

    @pytest.fixture
    def board_land(self, space_positions, land_config):
        return Board(space_positions, land_config, map_id=1)

    def test_virus_skip_toll(self, board_land, event_bus):
        """tile.toll_debuff_turns>0, rate=0.0 → visitor không trả toll, debuff cleared."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=500_000)
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1
        tile.toll_debuff_turns = 3
        tile.toll_debuff_rate = 0.0  # virus: miễn phí hoàn toàn

        visitor = Player(player_id="visitor", cash=1_000_000)
        initial_visitor_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_visitor_cash, "Visitor không trả tiền khi tile bị virus debuff"
        assert tile.toll_debuff_turns == 0, "toll_debuff_turns phải được clear khi visitor land"

    def test_no_virus_normal_toll(self, board_land, event_bus):
        """owner.virus_turns==0 → visitor trả toll bình thường."""
        from ctp.tiles.land import LandStrategy
        from ctp.core.constants import BASE_UNIT

        owner = Player(player_id="owner", cash=500_000)
        owner.add_property(2)
        owner.virus_turns = 0
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1

        visitor = Player(player_id="visitor", cash=1_000_000)
        initial_visitor_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        full_toll = 2 * BASE_UNIT
        assert visitor.cash == initial_visitor_cash - full_toll, "Visitor phải trả toll bình thường khi owner không bị virus"

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
        """tile.toll_debuff_turns>0 (virus) beats double_toll: không trả gì dù visitor có double_toll."""
        from ctp.tiles.land import LandStrategy

        owner = Player(player_id="owner", cash=0)
        owner.add_property(2)
        tile = board_land.get_tile(2)
        tile.owner_id = "owner"
        tile.building_level = 1
        tile.toll_debuff_turns = 3
        tile.toll_debuff_rate = 0.0  # virus

        visitor = Player(player_id="visitor", cash=1_000_000)
        visitor.double_toll_turns = 1
        initial_cash = visitor.cash

        strategy = LandStrategy()
        strategy.on_land(visitor, tile, board_land, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_cash, "Tile virus debuff phải có priority cao hơn double_toll"
        assert tile.toll_debuff_turns == 0, "toll_debuff_turns phải được clear khi visitor land"


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
        """Resort: tile.toll_debuff_turns>0 (virus) → visitor không trả toll, debuff cleared."""
        from ctp.tiles.resort import ResortStrategy

        owner = Player(player_id="owner", cash=0)
        owner.add_property(5)
        tile = board_resort.get_tile(5)  # RESORT position 5
        tile.owner_id = "owner"
        tile.building_level = 1
        tile.toll_debuff_turns = 2
        tile.toll_debuff_rate = 0.0  # virus

        visitor = Player(player_id="visitor", cash=1_000_000)
        initial_cash = visitor.cash

        strategy = ResortStrategy()
        strategy.on_land(visitor, tile, board_resort, event_bus, players=[owner, visitor])

        assert visitor.cash == initial_cash, "Resort: visitor không trả toll khi tile bị virus debuff"
        assert tile.toll_debuff_turns == 0, "toll_debuff_turns phải được clear khi visitor land"

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
