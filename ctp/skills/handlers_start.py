"""Handlers cho ON_PASS_START triggers: SK_GRAMMY, SK_MU_PHEP.

D-23: nhà cấp 3 = building_level 4
D-47: Additive stacking cho passing bonus modifiers
"""

import random

from ctp.core.board import SpaceId
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# SK_GRAMMY handler
# ---------------------------------------------------------------------------

def handle_grammy(player, ctx, cfg, engine):
    """SK_GRAMMY: Claims 1 random unowned CITY tile, builds to L4 (nhà cấp 3).

    Trigger: ON_PASS_START
    Rate check: handled by engine (A: base=16%+1%/star, S: base=22%+2%/star)

    Args:
        player: Player triggering the skill.
        ctx: Context dict with keys: board, players.
        cfg: SkillEntry config.
        engine: SkillEngine instance.

    Returns:
        dict with type="grammy_claim" and position, or None if no unowned CITY.
    """
    board = ctx["board"]
    unowned = [
        t for t in board.board
        if t.space_id == SpaceId.CITY and t.owner_id is None
    ]
    if not unowned:
        return None

    chosen = random.choice(unowned)
    chosen.owner_id = player.player_id
    chosen.building_level = 4  # D-23: nhà cấp 3 = L4
    player.add_property(chosen.position)
    return {"type": "grammy_claim", "position": chosen.position}


# ---------------------------------------------------------------------------
# SK_MU_PHEP handler
# ---------------------------------------------------------------------------

def handle_mu_phep(player, ctx, cfg, engine):
    """SK_MU_PHEP: Tăng tiền thưởng qua Start theo % value (always_active).

    Trigger: ON_PASS_START
    always_active: True — không cần rate check, engine sẽ gọi trực tiếp.

    Value formula (D-05): value = base_value + (star - min_star) * chance
    Ranks: B(base=41,chance=2), A(base=51,chance=3), S(base=66,chance=5)

    Args:
        player: Player triggering the skill.
        ctx: Context dict with keys: board, players.
        cfg: SkillEntry config.
        engine: SkillEngine instance.

    Returns:
        dict with type="passing_bonus_modifier" and percent_increase=value.
    """
    rank = player.rank
    if rank == "R":
        rank = "S"  # D-03: Rank R uses S config
    rc = cfg.rank_config.get(rank)
    if rc is None:
        return None

    # D-05: value = base_value + (star - min_star) * chance
    value = rc.base_rate + (player.star - rc.min_star) * rc.chance
    return {"type": "passing_bonus_modifier", "percent_increase": value}


# ---------------------------------------------------------------------------
# SO_10 Effect 2 helper (gọi từ Plan 11 handler)
# ---------------------------------------------------------------------------

def so_10_passing_bonus_modifier(player, ctx, cfg, engine):
    """SK_SO_10 Effect 2: Cố định +50% passing bonus, always active, no rank/star scaling.

    Trigger: ON_PASS_START (gọi từ SK_SO_10 handler tại Plan 11)

    Args:
        player: Player triggering the skill.
        ctx: Context dict.
        cfg: SkillEntry config.
        engine: SkillEngine instance.

    Returns:
        dict with type="passing_bonus_modifier" and percent_increase=50.
    """
    return {"type": "passing_bonus_modifier", "percent_increase": 50}


# ---------------------------------------------------------------------------
# D-47: Additive stacking helper
# ---------------------------------------------------------------------------

def calc_total_passing_bonus(base_bonus: float, modifiers: list[dict]) -> float:
    """Tính tổng tiền thưởng qua Start sau khi áp dụng tất cả modifier.

    D-47: Additive stacking — tất cả percent_increase cộng dồn vào base_bonus.
    Ví dụ: MuPhep S5★ (+86%) + SO_10 (+50%) on 150,000 = 150,000 * (1 + 0.86 + 0.50)
         = 150,000 * 2.36 = 354,000

    Args:
        base_bonus: Tiền thưởng qua Start cơ bản (trước khi có modifier).
        modifiers: List các dict kết quả từ fire() calls, mỗi dict có thể có:
                   {"type": "passing_bonus_modifier", "percent_increase": float}

    Returns:
        Total passing bonus sau stacking.
    """
    total_pct = sum(
        m["percent_increase"]
        for m in modifiers
        if m.get("type") == "passing_bonus_modifier"
    )
    return base_bonus * (1 + total_pct / 100)


# ---------------------------------------------------------------------------
# Register handlers
# ---------------------------------------------------------------------------

SKILL_HANDLERS["SK_GRAMMY"] = handle_grammy
SKILL_HANDLERS["SK_MU_PHEP"] = handle_mu_phep
