"""Toll modifier helpers cho Phase 02.1 card effects.

Shared logic cho LandStrategy và ResortStrategy: virus/double_toll/angel/discount checks.
"""

import json
import os
from typing import Optional
from ctp.core.models import Player
from ctp.core.events import GameEvent, EventType

_CARD_EFFECT_CACHE: Optional[dict] = None


def _get_held_card_effect(card_id: str) -> str:
    """Tra effect_id của card_id từ Card.json cache."""
    global _CARD_EFFECT_CACHE
    if _CARD_EFFECT_CACHE is None:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "Card.json"
        )
        with open(config_path, encoding="utf-8") as f:
            _CARD_EFFECT_CACHE = {k: v["effect"] for k, v in json.load(f)["Card"].items()}
    return _CARD_EFFECT_CACHE.get(card_id, "")


def apply_toll_modifiers(
    player: Player, owner: Optional[Player], tile, rent: float, event_bus,
    use_card_fn=None,
    skill_toll_waived: bool = False,
    skill_toll_multiply: float = 1.0,
    skill_toll_boost_pct: int = 0,
) -> tuple[float, bool]:
    """Apply skill + virus/double_toll/held_card modifiers lên rent.

    Order: skill_waive → skill_multiply → skill_boost → tile_debuff → double_toll → EF_20 Angel → EF_2 Discount.

    Args:
        player: Player đang trả toll.
        owner: Owner của tile (có thể None).
        tile: Tile đang trả toll (để check toll_debuff_turns).
        rent: Toll gốc đã tính.
        event_bus: Event bus.
        use_card_fn: Optional callback (player, card_id, toll_amount) -> bool.
            Nếu None (headless/AI): luôn dùng thẻ.
            Nếu trả về False: giữ thẻ, trả toll bình thường.
        skill_toll_waived: True nếu BuaSet/GiayBay/MangNhen/SieuTaxi waive toll.
        skill_toll_multiply: NgoiSao toll multiplier (default 1.0).
        skill_toll_boost_pct: TuiBaGang/KetVang boost percent (default 0).

    Returns:
        (modified_rent, skip_toll) — nếu skip_toll=True thì không trừ tiền.
    """
    # Step 0: Skill-based toll modifiers (from pre-toll hooks in FSM)
    if skill_toll_waived:
        return 0.0, True

    if skill_toll_multiply != 1.0:
        rent = int(rent * skill_toll_multiply)

    if skill_toll_boost_pct > 0:
        rent = int(rent * (1 + skill_toll_boost_pct / 100))

    # Step 1: tile-level virus/yellow-sand debuff — clear ngay khi visitor đầu tiên đặt chân vào
    if tile.toll_debuff_turns > 0:
        rate = tile.toll_debuff_rate   # 0.0 = miễn phí, 0.5 = giảm 50%
        tile.toll_debuff_turns = 0
        tile.toll_debuff_rate  = 1.0
        if rate == 0.0:
            event_bus.publish(GameEvent(
                event_type=EventType.CARD_EFFECT_VIRUS,
                player_id=owner.player_id if owner else "",
                data={"tile_pos": tile.position, "cleared_by": player.player_id}
            ))
            return 0.0, True
        else:
            rent = int(rent * rate)

    # Step 2: double_toll self-debuff (D-12)
    if player.double_toll_turns > 0:
        rent = int(rent * 2)

    # Step 3: EF_20 Angel — waive toll 100%
    if player.held_card is not None:
        effect = _get_held_card_effect(player.held_card)
        if effect == "EF_20":
            want_use = (use_card_fn is None) or use_card_fn(player, player.held_card, int(rent))
            if want_use:
                player.held_card = None
                event_bus.publish(GameEvent(
                    event_type=EventType.CARD_EFFECT_ANGEL,
                    player_id=player.player_id,
                    data={"toll_waived": rent}
                ))
                return 0.0, True
            # else: user giữ thẻ, trả toll bình thường

        # Step 4: EF_2 Discount — 50%
        if effect == "EF_2":
            want_use = (use_card_fn is None) or use_card_fn(player, player.held_card, int(rent))
            if want_use:
                original = rent
                rent = rent // 2
                player.held_card = None
                event_bus.publish(GameEvent(
                    event_type=EventType.CARD_EFFECT_DISCOUNT_TOLL,
                    player_id=player.player_id,
                    data={"original_toll": original, "paid_toll": rent}
                ))

    return rent, False
