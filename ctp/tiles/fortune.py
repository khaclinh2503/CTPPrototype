"""FortuneStrategy — full card draw implementation cho Phase 02.1."""

import json
import os
import random
from typing import Optional

import json
import os
from typing import Any
from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import calc_invested_build_cost, STARTING_CASH

# Module-level cache để tránh đọc file nhiều lần (RISK-02 resolution)
_CARD_DATA_CACHE: Optional[dict] = None

# Effect IDs cho held cards (D-06)
_HELD_EFFECTS = {"EF_2", "EF_3", "EF_19", "EF_20", "EF_22"}


def _load_raw_card_data() -> dict:
    """Load Card.json một lần, cache kết quả."""
    global _CARD_DATA_CACHE
    if _CARD_DATA_CACHE is None:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "Card.json"
        )
        with open(config_path, encoding="utf-8") as f:
            _CARD_DATA_CACHE = json.load(f)["Card"]
    return _CARD_DATA_CACHE


def _load_card_pool(map_id: int) -> dict:
    """Tạo card pool cho map_id, lọc mapNotAvail và rate=0.

    Args:
        map_id: 1=Map1, 2=Map2, 3=Map3

    Returns:
        Dict card_id -> card_data (đã lọc).
    """
    raw = _load_raw_card_data()
    pool = {}
    for card_id, data in raw.items():
        rate = data.get("rate", 0)
        if rate == 0:
            continue  # D-03: rate=0 → skip
        map_not_avail = data.get("mapNotAvail", [])
        if map_id in map_not_avail:
            continue  # D-01/D-02: filter by map_id
        pool[card_id] = data
    return pool


def _draw_card(pool: dict) -> str:
    """Rút thẻ theo weighted random.

    Args:
        pool: Filtered card pool (card_id -> data với rate > 0).

    Returns:
        card_id được rút.
    """
    card_ids = list(pool.keys())
    weights = [pool[c]["rate"] for c in card_ids]
    return random.choices(card_ids, weights=weights, k=1)[0]

_card_data_cache: dict[str, Any] | None = None


def _load_raw_card_data() -> dict[str, Any]:
    """Load và cache raw card data từ Card.json.

    Returns:
        Dict mapping card_id -> {"effect": "EF_XX", ...}
    """
    global _card_data_cache
    if _card_data_cache is not None:
        return _card_data_cache
    card_json_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "Card.json"
    )
    with open(card_json_path, encoding="utf-8") as f:
        raw = json.load(f)
    _card_data_cache = raw.get("Card", {})
    return _card_data_cache


class FortuneStrategy(TileStrategy):
    """Strategy cho CHANCE tiles — full card draw implementation."""

    def on_land(
        self, player: Player, tile: Tile, board: Board, event_bus,
        players: list | None = None
    ) -> list[GameEvent]:
        """Rút thẻ, apply effect (held hoặc instant)."""
        events = []
        players = players or []

        pool = _load_card_pool(board.map_id)
        if not pool:
            return events

        card_id = _draw_card(pool)
        card_data = pool[card_id]
        effect_id = card_data.get("effect", "")

        # Publish CARD_DRAWN event (per D-45)
        events.append(GameEvent(
            event_type=EventType.CARD_DRAWN,
            player_id=player.player_id,
            data={"card_id": card_id, "effect": effect_id, "position": tile.position}
        ))
        event_bus.publish(events[-1])

        # Held card: lưu vào slot (overwrite), không apply effect ngay (D-05, D-06)
        if effect_id in _HELD_EFFECTS:
            player.held_card = card_id
            return events

        # Instant card: apply effect ngay (D-07)
        effect_events = _apply_instant(card_id, effect_id, player, board, players, event_bus)
        events.extend(effect_events)
        return events

    def on_pass(
        self, player: Player, tile: Tile, board: Board, event_bus,
        players: list | None = None
    ) -> list[GameEvent]:
        return []


def _try_block_attack(defender: Player, attacker_card: str, event_bus) -> bool:
    """Kiểm tra EF_3 Shield block. Consume nếu có. Return True nếu bị chặn.

    Per D-15, RISK-05.
    """
    if defender.held_card is not None:
        raw = _load_raw_card_data()
        held_effect = raw.get(defender.held_card, {}).get("effect", "")
        if held_effect == "EF_3":
            defender.held_card = None  # consume (D-08)
            event_bus.publish(GameEvent(
                event_type=EventType.CARD_EFFECT_SHIELD_BLOCKED,
                player_id=defender.player_id,
                data={"blocked_card": attacker_card, "attacker_card": attacker_card}
            ))
            return True
    return False


def _apply_instant(
    card_id: str, effect_id: str, player: Player, board: Board,
    players: list, event_bus
) -> list[GameEvent]:
    """Dispatch instant card effects."""
    dispatch = {
        "EF_4":  _ef_force_sell,
        "EF_5":  _ef_swap_city,
        "EF_6":  _ef_downgrade,
        "EF_7":  _ef_virus,
        "EF_8":  _ef_yellow_sand,
        "EF_10": _ef_go_to_festival,
        "EF_11": _ef_go_to_festival_tile,
        "EF_12": _ef_go_to_travel,
        "EF_13": _ef_go_to_prison,
        "EF_14": _ef_go_to_start,
        "EF_15": _ef_host_festival,
        "EF_16": _ef_double_toll_debuff,
        "EF_17": _ef_donate_city,
        "EF_18": _ef_charity,
        "EF_21": _ef_go_to_god,
        "EF_26": _ef_go_to_tax,
        "EF_30": _ef_go_to_water_slide,
    }
    handler = dispatch.get(effect_id)
    if handler:
        return handler(card_id, player, board, players, event_bus)
    return []


# --- Group B: Attack cards ---

def _ef_force_sell(card_id, player, board, players, event_bus):
    """EF_4: Force sell một tile của opponent đắt nhất. IT_CA_4."""
    events = []
    opponent = _richest_opponent(player, players)
    if not opponent:
        return events
    if _try_block_attack(opponent, card_id, event_bus):
        return events
    # Tìm tile có building_level cao nhất của opponent
    target_tile = None
    for pos in opponent.owned_properties:
        t = board.get_tile(pos)
        if target_tile is None or t.building_level > target_tile.building_level:
            target_tile = t
    if target_tile is None:
        return events
    # Tính refund 50% invested cost
    invested = calc_invested_build_cost(board, target_tile.position)
    refund = int(invested * 0.5)
    # Reset tile về unowned
    if board.festival_tile_position == target_tile.position:
        board.festival_tile_position = None
        target_tile.festival_level = 0
    target_tile.owner_id = None
    target_tile.building_level = 0
    target_tile.is_golden = False
    target_tile.visit_count = 0
    opponent.remove_property(target_tile.position)
    opponent.receive(refund)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_FORCE_SELL,
        player_id=player.player_id,
        data={"target_player": opponent.player_id, "position": target_tile.position, "refund": refund}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_swap_city(card_id, player, board, players, event_bus):
    """EF_5: Swap ownership giữa 1 CITY của mình và 1 CITY của opponent. IT_CA_5."""
    events = []
    # Tìm CITY tiles của mình (per Claude's Discretion: nếu không có CITY → no effect)
    my_cities = [
        board.get_tile(pos)
        for pos in player.owned_properties
        if board.get_tile(pos).space_id == SpaceId.CITY
    ]
    if not my_cities:
        return events
    opponent = _richest_opponent(player, players)
    if not opponent:
        return events
    if _try_block_attack(opponent, card_id, event_bus):
        return events
    their_cities = [
        board.get_tile(pos)
        for pos in opponent.owned_properties
        if board.get_tile(pos).space_id == SpaceId.CITY
    ]
    if not their_cities:
        return events
    # Stub AI: đổi tile rẻ nhất của mình lấy tile đắt nhất của đối thủ (D-19)
    my_tile = min(my_cities, key=lambda t: t.building_level)
    their_tile = max(their_cities, key=lambda t: t.building_level)
    # Swap ownership (per RISK-08: building_level và festival_level theo tile)
    my_tile.owner_id = opponent.player_id
    their_tile.owner_id = player.player_id
    player.remove_property(my_tile.position)
    player.add_property(their_tile.position)
    opponent.remove_property(their_tile.position)
    opponent.add_property(my_tile.position)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_SWAP_CITY,
        player_id=player.player_id,
        data={"my_pos": my_tile.position, "their_pos": their_tile.position, "opponent": opponent.player_id}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_downgrade(card_id, player, board, players, event_bus):
    """EF_6/7: Hạ building_level của opponent tile 1 bậc. IT_CA_6, IT_CA_7."""
    events = []
    opponent = _richest_opponent(player, players)
    if not opponent:
        return events
    if _try_block_attack(opponent, card_id, event_bus):
        return events
    # Stub AI: tile có building_level cao nhất
    target_tile = None
    for pos in opponent.owned_properties:
        t = board.get_tile(pos)
        if t.space_id in (SpaceId.CITY, SpaceId.RESORT):
            if target_tile is None or t.building_level > target_tile.building_level:
                target_tile = t
    if target_tile is None:
        return events
    target_tile.building_level = max(0, target_tile.building_level - 1)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_DOWNGRADE,
        player_id=player.player_id,
        data={"target_player": opponent.player_id, "position": target_tile.position, "new_level": target_tile.building_level}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_virus(card_id, player, board, players, event_bus):
    """EF_7: toll = 0 trên CITY cùng cặp màu của opponent trong 5 lượt. IT_CA_8, IT_CA_10."""
    return _apply_color_pair_debuff(card_id, player, board, players, event_bus, debuff_rate=0.0)


def _ef_yellow_sand(card_id, player, board, players, event_bus):
    """EF_8: toll giảm 50% trên CITY cùng cặp màu của opponent trong 5 lượt. IT_CA_9."""
    return _apply_color_pair_debuff(card_id, player, board, players, event_bus, debuff_rate=0.5)


def _apply_color_pair_debuff(card_id, player, board, players, event_bus, debuff_rate: float):
    """Set player-level virus debuff on opponent per D-11/D-22."""
    events = []
    opponent = _richest_opponent(player, players)
    if not opponent:
        return events
    if _try_block_attack(opponent, card_id, event_bus):
        return events

    # Player-level virus: affects ALL owned tiles, not individual tiles
    opponent.virus_turns = 3

    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_VIRUS,
        player_id=player.player_id,
        data={
            "target_player": opponent.player_id,
            "duration": 3,
        }
    ))
    event_bus.publish(events[-1])
    return events


# --- Group C: Self-debuff cards ---

def _ef_go_to_start(card_id, player, board, players, event_bus):
    """EF_14: Teleport đến START, nhận passing bonus. IT_CA_16."""
    events = []
    passing_bonus = int(STARTING_CASH * 0.15)  # passingBonusRate=0.15 per GDD
    player.move_to(1)
    player.receive(passing_bonus)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_START,
        player_id=player.player_id,
        data={"bonus_received": passing_bonus}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_go_to_prison(card_id, player, board, players, event_bus):
    """EF_13: Teleport đến PRISON, prison_turns_remaining = 3. IT_CA_14."""
    events = []
    prison_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.PRISON)
    if prison_pos is None:
        return events
    player.move_to(prison_pos)
    player.enter_prison()
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_PRISON,
        player_id=player.player_id,
        data={"position": prison_pos}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_double_toll_debuff(card_id, player, board, players, event_bus):
    """EF_16: Self-debuff — double_toll_turns = 1. IT_CA_18."""
    events = []
    player.double_toll_turns = 1
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_DOUBLE_TOLL_DEBUFF,
        player_id=player.player_id,
        data={"duration_turns": 1}
    ))
    event_bus.publish(events[-1])
    return events


# --- Group D: Teleport cards ---

def _ef_go_to_festival(card_id, player, board, players, event_bus):
    """EF_10: Teleport đến FESTIVAL tile hiện tại. IT_CA_12."""
    events = []
    fest_pos = board.festival_tile_position
    if fest_pos is None:
        # Fallback: tìm FESTIVAL tile đầu tiên trên board
        fest_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.FESTIVAL)
    if fest_pos is None:
        return events
    player.move_to(fest_pos)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_FESTIVAL,
        player_id=player.player_id,
        data={"target_position": fest_pos}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_go_to_festival_tile(card_id, player, board, players, event_bus):
    """EF_11: Teleport đến tile có festival_level cao nhất. IT_CA_13.

    Per Claude's Discretion: nếu nhiều tile có festival → chọn festival_level cao nhất.
    """
    events = []
    # Tìm tile có festival_level > 0, chọn cao nhất
    best_tile = None
    for tile in board.board:
        if tile.festival_level > 0:
            if best_tile is None or tile.festival_level > best_tile.festival_level:
                best_tile = tile
    if best_tile is None:
        return events
    player.move_to(best_tile.position)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_FESTIVAL_TILE,
        player_id=player.player_id,
        data={"target_position": best_tile.position}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_go_to_travel(card_id, player, board, players, event_bus):
    """EF_12: Teleport đến TRAVEL tile, set pending_travel = True. IT_CA_15.

    Per RESEARCH.md: set cả hai trực tiếp, không gọi TravelStrategy.on_land() lại.
    """
    events = []
    travel_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.TRAVEL)
    if travel_pos is None:
        return events
    player.move_to(travel_pos)
    player.pending_travel = True
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_TRAVEL,
        player_id=player.player_id,
        data={"target_position": travel_pos}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_go_to_tax(card_id, player, board, players, event_bus):
    """EF_26: Teleport đến TAX tile. IT_CA_11 (mapNotAvail=[2])."""
    events = []
    tax_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.TAX)
    if tax_pos is None:
        return events
    player.move_to(tax_pos)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_TAX,
        player_id=player.player_id,
        data={"target_position": tax_pos}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_go_to_water_slide(card_id, player, board, players, event_bus):
    """EF_30: Teleport đến WATER_SLIDE tile gần nhất. IT_CA_30 (Map 3 only)."""
    events = []
    ws_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.WATER_SLIDE)
    if ws_pos is None:
        return events
    player.move_to(ws_pos)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_WATER_SLIDE,
        player_id=player.player_id,
        data={"target_position": ws_pos}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_go_to_god(card_id, player, board, players, event_bus):
    """EF_21: Teleport đến GOD tile gần nhất theo chiều tiến. IT_CA_22 (Map 2 only)."""
    events = []
    god_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.GOD)
    if god_pos is None:
        return events
    player.move_to(god_pos)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_GOD,
        player_id=player.player_id,
        data={"target_position": god_pos}
    ))
    event_bus.publish(events[-1])
    return events


# --- Group E: Economy/Social cards ---

def _ef_host_festival(card_id, player, board, players, event_bus):
    """EF_15: Đặt festival marker miễn phí trên tile đang sở hữu. IT_CA_17."""
    events = []
    if not player.owned_properties:
        return events
    # Stub AI: chọn tile có building_level cao nhất (D-34)
    best_tile = max(
        (board.get_tile(pos) for pos in player.owned_properties
         if board.get_tile(pos).space_id in (SpaceId.CITY, SpaceId.RESORT)),
        key=lambda t: t.building_level,
        default=None
    )
    if best_tile is None:
        return events
    # Clear festival tile cũ nếu có
    if board.festival_tile_position is not None and board.festival_tile_position != best_tile.position:
        old_tile = board.get_tile(board.festival_tile_position)
        old_tile.festival_level = 0
    best_tile.festival_level += 1
    board.festival_tile_position = best_tile.position
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_HOST_FESTIVAL,
        player_id=player.player_id,
        data={"position": best_tile.position}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_donate_city(card_id, player, board, players, event_bus):
    """EF_17: Tặng tile rẻ nhất cho player nghèo nhất. IT_CA_19."""
    events = []
    if not player.owned_properties:
        return events
    # Tìm player nghèo nhất (ít tài sản, không bankrupt, không phải mình)
    recipients = [p for p in players if not p.is_bankrupt and p.player_id != player.player_id]
    if not recipients:
        return events
    poorest = min(recipients, key=lambda p: p.cash + len(p.owned_properties) * 100_000)
    # Tile rẻ nhất: building_level thấp nhất
    give_tile = min(
        (board.get_tile(pos) for pos in player.owned_properties),
        key=lambda t: t.building_level
    )
    give_tile.owner_id = poorest.player_id
    player.remove_property(give_tile.position)
    poorest.add_property(give_tile.position)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_DONATE_CITY,
        player_id=player.player_id,
        data={"position": give_tile.position, "recipient": poorest.player_id}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_charity(card_id, player, board, players, event_bus):
    """EF_18: Mỗi player (trừ nghèo nhất) đóng 100k cho player nghèo nhất. IT_CA_20."""
    events = []
    active = [p for p in players if not p.is_bankrupt]
    if len(active) < 2:
        return events
    poorest = min(active, key=lambda p: p.cash + len(p.owned_properties) * 100_000)
    donation_per_player = int(STARTING_CASH * 0.1)  # 100k = 10% × 1_000_000
    total = 0
    for p in active:
        if p.player_id == poorest.player_id:
            continue
        p.pay(donation_per_player)
        total += donation_per_player
    poorest.receive(total)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_CHARITY,
        player_id=player.player_id,
        data={"recipient": poorest.player_id, "total_received": total}
    ))
    event_bus.publish(events[-1])
    return events


# --- Helpers ---

def _richest_opponent(player: Player, players: list) -> Optional[Player]:
    """Trả về opponent không bankrupt có tổng assets cao nhất (stub AI target per D-18)."""
    opponents = [p for p in players if not p.is_bankrupt and p.player_id != player.player_id]
    if not opponents:
        return None
    return max(opponents, key=lambda p: p.cash + len(p.owned_properties) * 100_000)
