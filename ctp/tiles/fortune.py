"""FortuneStrategy — full card draw implementation cho Phase 02.1."""

import json
import os
import random
from typing import Any, Optional

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import calc_invested_build_cost, STARTING_CASH

# Effect IDs cho held cards (D-06)
_HELD_EFFECTS = {"EF_2", "EF_3", "EF_19", "EF_20", "EF_22"}

# Debug inject: nếu != None, lần rút thẻ tiếp theo sẽ dùng card này thay vì random
_debug_forced_card: Optional[str] = None


def set_debug_card(card_id: Optional[str]) -> None:
    """Set card sẽ được rút trong lần FortuneStrategy.on_land() tiếp theo.

    Dùng để test flow từng thẻ khi game đang chạy.
    Truyền None để xoá override.
    """
    global _debug_forced_card
    _debug_forced_card = card_id


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
    """Load và cache raw card data từ Card.json."""
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
        players: list | None = None,
        accept_card_fn=None,
        shield_block_fn=None,
        force_sell_select_fn=None,
        swap_city_select_fn=None,
        downgrade_select_fn=None,
        virus_select_fn=None,
        donate_select_fn=None,
    ) -> list[GameEvent]:
        """Rút thẻ, apply effect (held hoặc instant)."""
        events = []
        players = players or []

        pool = _load_card_pool(board.map_id)
        if not pool:
            return events

        global _debug_forced_card
        if _debug_forced_card is not None:
            card_id = _debug_forced_card
            _debug_forced_card = None  # consume — chỉ dùng 1 lần
            raw = _load_raw_card_data()
            card_data = pool.get(card_id) or raw.get(card_id, {})
        else:
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

        # Held card: hỏi player có muốn lấy không (D-05, D-06)
        if effect_id in _HELD_EFFECTS:
            want_accept = (accept_card_fn is None) or accept_card_fn(player, card_id)
            if want_accept:
                player.held_card = card_id
            return events

        # Instant card: apply effect ngay (D-07)
        effect_events = _apply_instant(
            card_id, effect_id, player, board, players, event_bus,
            shield_block_fn, force_sell_select_fn, swap_city_select_fn,
            downgrade_select_fn, virus_select_fn, donate_select_fn,
        )
        events.extend(effect_events)
        return events

    def on_pass(
        self, player: Player, tile: Tile, board: Board, event_bus,
        players: list | None = None
    ) -> list[GameEvent]:
        return []


def _try_block_attack(defender: Player, attacker_card: str, event_bus, shield_block_fn=None) -> bool:
    """Kiểm tra EF_3 Shield block. Hỏi defender qua callback nếu có.

    shield_block_fn(defender, attacker_card) -> bool:
      True = dùng thẻ (chặn + tiêu thẻ), False = bỏ qua (không chặn, giữ thẻ).
    Nếu shield_block_fn=None: auto-block (backward compat).

    Per D-15, RISK-05.
    """
    if defender.held_card is None:
        return False
    raw = _load_raw_card_data()
    held_effect = raw.get(defender.held_card, {}).get("effect", "")
    if held_effect != "EF_3":
        return False
    # Hỏi defender có muốn dùng thẻ không
    if shield_block_fn is not None:
        want_block = shield_block_fn(defender, attacker_card)
    else:
        want_block = True  # auto-block khi không có callback
    if not want_block:
        return False
    defender.held_card = None  # consume (D-08)
    event_bus.publish(GameEvent(
        event_type=EventType.CARD_EFFECT_SHIELD_BLOCKED,
        player_id=defender.player_id,
        data={"blocked_card": attacker_card, "attacker_card": attacker_card}
    ))
    return True


def _apply_instant(
    card_id: str, effect_id: str, player: Player, board: Board,
    players: list, event_bus, shield_block_fn=None, force_sell_select_fn=None,
    swap_city_select_fn=None, downgrade_select_fn=None, virus_select_fn=None,
    donate_select_fn=None,
) -> list[GameEvent]:
    """Dispatch instant card effects."""
    # Attack effects need shield_block_fn threaded through
    _attack = {"EF_4", "EF_5", "EF_6", "EF_7", "EF_8"}
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
        "EF_24": _ef_bank_stub,
        "EF_25": _ef_agency_stub,
        "EF_26": _ef_go_to_tax,
        "EF_30": _ef_go_to_water_slide,
    }
    handler = dispatch.get(effect_id)
    if handler:
        if effect_id == "EF_4":
            return handler(card_id, player, board, players, event_bus, shield_block_fn, force_sell_select_fn)
        if effect_id == "EF_5":
            return handler(card_id, player, board, players, event_bus, shield_block_fn, swap_city_select_fn)
        if effect_id == "EF_6":
            return handler(card_id, player, board, players, event_bus, shield_block_fn, downgrade_select_fn)
        if effect_id in ("EF_7", "EF_8"):
            return handler(card_id, player, board, players, event_bus, shield_block_fn, virus_select_fn)
        if effect_id == "EF_17":
            return handler(card_id, player, board, players, event_bus, donate_select_fn)
        if effect_id in _attack:
            return handler(card_id, player, board, players, event_bus, shield_block_fn)
        return handler(card_id, player, board, players, event_bus)
    return []


# --- Group B: Attack cards ---

def _ef_force_sell(card_id, player, board, players, event_bus, shield_block_fn=None, force_sell_select_fn=None):
    """EF_4: Force sell 1 tile của opponent do player chọn. IT_CA_4."""
    events = []

    if force_sell_select_fn is not None:
        # Human or delegated selection: callback returns (opponent_id, tile_pos) or None (skip)
        result = force_sell_select_fn(player, board, players)
        if result is None:
            return events  # player bỏ qua, thẻ vẫn tiêu
        opponent_id, tile_pos = result
        opponent = next((p for p in players if p.player_id == opponent_id), None)
        if not opponent:
            return events
        target_tile = board.get_tile(tile_pos)
    else:
        # AI: chọn richest opponent + tile building_level cao nhất
        opponent = _richest_opponent(player, players)
        if not opponent:
            return events
        target_tile = None
        for pos in opponent.owned_properties:
            t = board.get_tile(pos)
            if target_tile is None or t.building_level > target_tile.building_level:
                target_tile = t
        if target_tile is None:
            return events

    if _try_block_attack(opponent, card_id, event_bus, shield_block_fn):
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


def _ef_swap_city(card_id, player, board, players, event_bus, shield_block_fn=None, swap_city_select_fn=None):
    """EF_5: Swap ownership giữa 1 CITY của mình và 1 CITY của opponent. IT_CA_5.

    Human: 2-step popup — chọn CITY của mình, rồi chọn CITY của đối thủ.
    Sau đó check EF_3 shield của đối thủ. Nếu không có hoặc không dùng → swap.
    AI: đổi tile rẻ nhất của mình ↔ tile đắt nhất của đối thủ giàu nhất.
    """
    events = []
    my_cities = [
        board.get_tile(pos)
        for pos in player.owned_properties
        if board.get_tile(pos).space_id == SpaceId.CITY
    ]
    if not my_cities:
        return events

    if swap_city_select_fn is not None:
        # Human: 2-step selection — (my_pos, opponent_id, their_pos) or None
        result = swap_city_select_fn(player, board, players)
        if result is None:
            return events
        my_pos, opponent_id, their_pos = result
        my_tile = board.get_tile(my_pos)
        opponent = next((p for p in players if p.player_id == opponent_id), None)
        if opponent is None:
            return events
        their_tile = board.get_tile(their_pos)
    else:
        # AI: đổi tile rẻ nhất của mình lấy tile đắt nhất của đối thủ giàu nhất
        opponent = _richest_opponent(player, players)
        if not opponent:
            return events
        their_cities = [
            board.get_tile(pos)
            for pos in opponent.owned_properties
            if board.get_tile(pos).space_id == SpaceId.CITY
        ]
        if not their_cities:
            return events
        my_tile = min(my_cities, key=lambda t: t.building_level)
        their_tile = max(their_cities, key=lambda t: t.building_level)

    # Check EF_3 shield của đối thủ
    if _try_block_attack(opponent, card_id, event_bus, shield_block_fn):
        return events

    # Swap ownership (building_level và festival_level theo tile, không đổi)
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


def _ef_downgrade(card_id, player, board, players, event_bus, shield_block_fn=None, downgrade_select_fn=None):
    """EF_6: Player chọn 1 CITY của opponent (không phải Landmark L5) để hạ 1 bậc.
    Nếu về 0 thì mất quyền sở hữu. Nếu không có ô hợp lệ: bỏ qua hiệu ứng, mất thẻ.
    IT_CA_6, IT_CA_7."""
    events = []

    # Kiểm tra trước: có ô hợp lệ nào không (CITY, non-Landmark, của đối thủ còn sống)?
    has_valid_target = any(
        board.get_tile(pos).space_id == SpaceId.CITY and board.get_tile(pos).building_level < 5
        for p in players
        if p.player_id != player.player_id and not p.is_bankrupt
        for pos in p.owned_properties
    )
    if not has_valid_target:
        ev = GameEvent(
            event_type=EventType.CARD_EFFECT_DOWNGRADE,
            player_id=player.player_id,
            data={"skipped": True, "reason": "no_valid_target"},
        )
        events.append(ev)
        event_bus.publish(ev)
        return events

    if downgrade_select_fn is not None:
        # Human: callback trả về (opponent_id, tile_pos) hoặc None (bỏ qua)
        result = downgrade_select_fn(player, board, players)
        if result is None:
            return events
        opponent_id, tile_pos = result
        opponent = next((p for p in players if p.player_id == opponent_id), None)
        target_tile = board.get_tile(tile_pos) if opponent else None
        if opponent is None or target_tile is None:
            return events
        if _try_block_attack(opponent, card_id, event_bus, shield_block_fn):
            return events
    else:
        # AI: chọn richest opponent + CITY (non-Landmark) có building_level cao nhất
        opponent = _richest_opponent(player, players)
        if not opponent:
            return events
        if _try_block_attack(opponent, card_id, event_bus, shield_block_fn):
            return events
        target_tile = None
        for pos in opponent.owned_properties:
            t = board.get_tile(pos)
            if t.space_id == SpaceId.CITY and t.building_level < 5:
                if target_tile is None or t.building_level > target_tile.building_level:
                    target_tile = t
        if target_tile is None:
            return events

    target_tile.building_level = max(0, target_tile.building_level - 1)
    lost_ownership = target_tile.building_level == 0
    if lost_ownership:
        target_tile.owner_id = None
        opponent.remove_property(target_tile.position)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_DOWNGRADE,
        player_id=player.player_id,
        data={
            "target_player": opponent.player_id,
            "position": target_tile.position,
            "new_level": target_tile.building_level,
            "lost_ownership": lost_ownership,
        }
    ))
    event_bus.publish(events[-1])
    return events


def _ef_virus(card_id, player, board, players, event_bus, shield_block_fn=None, virus_select_fn=None):
    """EF_7: toll = 0 trên CITY cùng cặp màu của opponent trong 5 lượt. IT_CA_8, IT_CA_10."""
    return _apply_color_pair_debuff(card_id, player, board, players, event_bus, debuff_rate=0.0, shield_block_fn=shield_block_fn, virus_select_fn=virus_select_fn)


def _ef_yellow_sand(card_id, player, board, players, event_bus, shield_block_fn=None, virus_select_fn=None):
    """EF_8: toll giảm 50% trên CITY cùng cặp màu của opponent trong 5 lượt. IT_CA_9."""
    return _apply_color_pair_debuff(card_id, player, board, players, event_bus, debuff_rate=0.5, shield_block_fn=shield_block_fn, virus_select_fn=virus_select_fn)


def _apply_color_pair_debuff(card_id, player, board, players, event_bus, debuff_rate: float, shield_block_fn=None, virus_select_fn=None):
    """Virus/yellow-sand: áp tile-level debuff lên 1 tile target của opponent.

    - Human: virus_select_fn callback hiện popup chọn tile; trả None = bỏ qua (mất thẻ).
    - AI: chọn tile có building_level cao nhất của opponent (CITY only).
    - Nếu toàn bộ cặp màu của tile đó đều cùng chủ opponent → debuff cả cặp.
    - Visitor đầu tiên nhảy vào tile bị debuff: miễn phí + xóa debuff tile đó ngay.
    - Duration: 5 lượt (countdown mỗi END_TURN trong FSM).
    """
    events = []

    if virus_select_fn is not None:
        # Human: callback trả về (opponent_id, tile_pos) hoặc None (bỏ qua)
        result = virus_select_fn(player, board, players, card_id=card_id)
        if result is None:
            return events
        opponent_id, tile_pos = result
        opponent = next((p for p in players if p.player_id == opponent_id), None)
        target_tile = board.get_tile(tile_pos) if opponent else None
        if opponent is None or target_tile is None:
            return events
        if _try_block_attack(opponent, card_id, event_bus, shield_block_fn):
            return events
    else:
        # AI: chọn richest opponent + CITY có building_level cao nhất
        opponent = _richest_opponent(player, players)
        if not opponent:
            return events
        if _try_block_attack(opponent, card_id, event_bus, shield_block_fn):
            return events

        # Chọn tile CITY của opponent có building_level cao nhất
        target_tile = None
        for pos in opponent.owned_properties:
            t = board.get_tile(pos)
            if t.space_id == SpaceId.CITY:
                if target_tile is None or t.building_level > target_tile.building_level:
                    target_tile = t
        if target_tile is None:
            return events

    # Tìm color pair: tất cả CITY tile cùng màu với target
    color_group_positions = board.get_color_group_positions(target_tile.opt)
    affected_positions = [target_tile.position]

    # Nếu toàn bộ cặp màu đều thuộc opponent → debuff cả cặp
    # Ghi chú: phải check color_group_positions không rỗng trước để tránh vacuous truth
    if color_group_positions:
        color_group_tiles = [board.get_tile(p) for p in color_group_positions]
        if all(t.owner_id == opponent.player_id for t in color_group_tiles):
            affected_positions = color_group_positions

    # Áp debuff lên từng tile
    for pos in affected_positions:
        t = board.get_tile(pos)
        t.toll_debuff_turns = 5
        t.toll_debuff_rate  = debuff_rate

    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_VIRUS,
        player_id=player.player_id,
        data={
            "target_player":      opponent.player_id,
            "affected_positions": affected_positions,
            "debuff_rate":        debuff_rate,
            "duration":           5,
        }
    ))
    event_bus.publish(events[-1])
    return events


# --- Group C: Self-debuff cards ---

def _ef_go_to_start(card_id, player, board, players, event_bus):
    """EF_14: Đi từng ô về START (move_type=3), nhận passing bonus. IT_CA_16."""
    events = []
    old_pos = player.position
    passing_bonus = int(STARTING_CASH * 0.15)  # passingBonusRate=0.15 per GDD
    player.move_to(1)
    player.receive(passing_bonus)
    # move_type=3: walk tile-by-tile về START (phân biệt với walk bình thường=1 và teleport=2)
    events.append(GameEvent(
        event_type=EventType.PLAYER_MOVE,
        player_id=player.player_id,
        data={"old_pos": old_pos, "new_pos": 1, "move_type": 3}
    ))
    event_bus.publish(events[-1])
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_START,
        player_id=player.player_id,
        data={"old_pos": old_pos, "new_pos": 1, "bonus_received": passing_bonus}
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
    """EF_16: Self-debuff — double toll cho lượt tiếp theo. IT_CA_18.

    double_toll_turns = 2 vì FSM decrements ở đầu ROLL (trước khi di chuyển),
    nên cần value=2 để sau khi decrement vẫn còn 1 và fire khi trả toll.
    """
    events = []
    player.double_toll_turns = 2
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
    """EF_11: Teleport đến tile đang tổ chức lễ hội. IT_CA_13.

    Dùng board.festival_tile_position (ô đang active festival).
    Nếu không có festival đang diễn ra → kết thúc lượt (trả về empty).
    """
    events = []
    fest_pos = board.festival_tile_position
    if fest_pos is None:
        return events
    player.move_to(fest_pos)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_GO_TO_FESTIVAL_TILE,
        player_id=player.player_id,
        data={"target_position": fest_pos}
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


def _ef_donate_city(card_id, player, board, players, event_bus, donate_select_fn=None):
    """EF_17: Tặng 1 tile cho 1 player khác. IT_CA_19.

    Human: donate_select_fn callback 2 bước (chọn tile → chọn người nhận), bắt buộc.
    AI: tặng tile rẻ nhất cho player nghèo nhất.
    """
    events = []
    if not player.owned_properties:
        return events
    recipients = [p for p in players if not p.is_bankrupt and p.player_id != player.player_id]
    if not recipients:
        return events

    if donate_select_fn is not None:
        # Human: callback trả về (tile_pos, recipient_id) — bắt buộc, không thể bỏ qua
        result = donate_select_fn(player, board, players)
        if result is None:
            return events
        tile_pos, recipient_id = result
        give_tile = board.get_tile(tile_pos)
        recipient = next((p for p in recipients if p.player_id == recipient_id), None)
        if recipient is None:
            return events
    else:
        # AI: tile rẻ nhất → player nghèo nhất
        give_tile = min(
            (board.get_tile(pos) for pos in player.owned_properties),
            key=lambda t: t.building_level
        )
        recipient = min(recipients, key=lambda p: p.cash + len(p.owned_properties) * 100_000)

    give_tile.owner_id = recipient.player_id
    player.remove_property(give_tile.position)
    recipient.add_property(give_tile.position)
    events.append(GameEvent(
        event_type=EventType.CARD_EFFECT_DONATE_CITY,
        player_id=player.player_id,
        data={"position": give_tile.position, "recipient": recipient.player_id}
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


# --- Group F: Map 3 stubs (EF_24, EF_25) ---

def _ef_bank_stub(card_id, player, board, players, event_bus):
    """EF_24: Bank effect — Map 3 only stub. IT_CA_24."""
    events = []
    events.append(GameEvent(
        event_type=EventType.CARD_DRAWN,
        player_id=player.player_id,
        data={"card_id": card_id, "effect": "EF_24", "stub": True}
    ))
    event_bus.publish(events[-1])
    return events


def _ef_agency_stub(card_id, player, board, players, event_bus):
    """EF_25: Agency effect — Map 3 only stub. IT_CA_25."""
    events = []
    events.append(GameEvent(
        event_type=EventType.CARD_DRAWN,
        player_id=player.player_id,
        data={"card_id": card_id, "effect": "EF_25", "stub": True}
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
