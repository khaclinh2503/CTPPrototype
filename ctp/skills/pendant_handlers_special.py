"""Special trigger pendant handlers: PT_DKXX2, PT_XICH_NGOC, PT_CHONG_MUA_NHA, PT_SIEU_SAO_CHEP.

Pendant triggers covered:
  - ON_DKXX_CHECK: PT_DKXX2, PT_XICH_NGOC R2
  - ON_PRISON_ROLL: PT_XICH_NGOC R1
  - ON_OPPONENT_LAND_YOURS: PT_CHONG_MUA_NHA
  - ON_OPPONENT_UPGRADE_SYMBOL: PT_SIEU_SAO_CHEP R1
  - ON_GAME_START: PT_SIEU_SAO_CHEP R2
"""

import random

from ctp.skills.registry import PENDANT_HANDLERS


# ---------------------------------------------------------------------------
# PT_DKXX2 — ON_DKXX_CHECK
# Boost player's dkxx_bonus_pool by rank rate.
# Rank rates: B:2, A:3, S:4, R:12, SR:18
# ---------------------------------------------------------------------------

def handle_dkxx2(player, ctx, cfg, engine):
    """PT_DKXX2: Boost dkxx_bonus_pool when DKXX check fires.

    ON_DKXX_CHECK — called by FSM.ROLL phase.
    The engine's fire_pendants already does the outer rate check using
    cfg.rank_rates for the player's pendant_rank; this handler fires only
    when that check passes.

    Args:
        player: Player whose pendant is firing.
        ctx: Trigger context dict (board, players, …).
        cfg: PendantEntry config object.
        engine: SkillEngine instance.

    Returns:
        dict {"type": "dkxx_boost", "amount": rate} on activation.
    """
    rate = getattr(cfg.rank_rates, player.pendant_rank, 0)
    player.dkxx_bonus_pool += rate
    return {"type": "dkxx_boost", "amount": rate}


PENDANT_HANDLERS["PT_DKXX2"] = handle_dkxx2


# ---------------------------------------------------------------------------
# PT_XICH_NGOC — 2 triggers, 2 rate configs
# R1 (ON_PRISON_ROLL): boost doubles rate for prison escape roll.
# R2 (ON_DKXX_CHECK): boost dkxx_bonus_pool (same mechanism as PT_DKXX2).
# ---------------------------------------------------------------------------

def handle_xich_ngoc(player, ctx, cfg, engine):
    """PT_XICH_NGOC: Dual-trigger handler dispatched by trigger name in ctx.

    The caller (fire_pendants) does NOT do an outer rate check for
    multi-trigger pendants — this handler performs its own rate checks
    based on the active trigger.

    Context key expected: ctx["trigger"] — the trigger string that fired.

    Rate 1 (ON_PRISON_ROLL):   B:20, A:40, S:60, R:80, SR:100
    Rate 2 (ON_DKXX_CHECK):    B:2,  A:4,  S:6,  R:10, SR:14

    Args:
        player: Player whose pendant is firing.
        ctx: Must contain ctx["trigger"] to identify which rate to use.
        cfg: PendantEntry config object (has rank_rates and rank_rates_2).
        engine: SkillEngine instance.

    Returns:
        dict for the activated effect, or None if rate check failed.
    """
    trigger = ctx.get("trigger", "")

    if trigger == "ON_PRISON_ESCAPE_CHECK":
        rate1 = getattr(cfg.rank_rates, player.pendant_rank, 0)
        if random.randint(0, 99) < rate1:
            return {"type": "prison_doubles_boost", "boost_pct": rate1}
        return None

    if trigger == "ON_DKXX_CHECK":
        rate2 = getattr(cfg.rank_rates_2, player.pendant_rank, 0)
        if random.randint(0, 99) < rate2:
            player.dkxx_bonus_pool += rate2
            return {"type": "dkxx_boost", "amount": rate2}
        return None

    return None


PENDANT_HANDLERS["PT_XICH_NGOC"] = handle_xich_ngoc


# ---------------------------------------------------------------------------
# PT_CHONG_MUA_NHA — ON_OPPONENT_LAND_YOURS (acquisition check time)
# Block acquisition with compound rate:
#   block_rate = active_factor[building_level] * pendant_rate
# active_factor: {1: 0.15, 2: 0.35, 3: 0.60, 4: 1.0, 5: 1.0}
# Rank rates: B:10, A:20, S:43, R:62, SR:70
# ---------------------------------------------------------------------------

_ACTIVE_FACTORS = {1: 0.15, 2: 0.35, 3: 0.60, 4: 1.0, 5: 1.0}


def handle_chong_mua_nha(player, ctx, cfg, engine):
    """PT_CHONG_MUA_NHA: Block acquisition when opponent lands on player's tile.

    The engine does an outer rate check using cfg.rank_rates for pendant_rank
    before calling this handler; this handler performs the compound-rate block
    check itself to correctly account for the active_factor by building_level.

    Context expected: ctx["tile"] — the Tile object the opponent landed on.

    Args:
        player: Player who owns the tile (the defender).
        ctx: Trigger context, must contain ctx["tile"].
        cfg: PendantEntry config object.
        engine: SkillEngine instance.

    Returns:
        dict {"type": "acquisition_blocked"} if block succeeds, else None.

    Note:
        This pendant only blocks normal acquisition (opponent buying the tile).
        It does NOT block PT_CUOP_NHA or PT_MANG_NHEN steal mechanics.
    """
    tile = ctx.get("tile")
    if tile is None:
        return None

    pendant_rate = getattr(cfg.rank_rates, player.pendant_rank, 0) / 100
    level = tile.building_level
    active_factor = _ACTIVE_FACTORS.get(level, 1.0)
    block_rate = active_factor * pendant_rate

    if random.randint(0, 99) < block_rate * 100:
        return {"type": "acquisition_blocked"}
    return None


PENDANT_HANDLERS["PT_CHONG_MUA_NHA"] = handle_chong_mua_nha


# ---------------------------------------------------------------------------
# PT_SIEU_SAO_CHEP — 2 triggers
# R1 (ON_OPPONENT_UPGRADE_SYMBOL): create random L5 on owned property < L5.
# R2 (ON_GAME_START): double starting cash.
# ---------------------------------------------------------------------------

def handle_sieu_sao_chep(player, ctx, cfg, engine):
    """PT_SIEU_SAO_CHEP: Dual-trigger handler — copy L5 or double starting cash.

    Context key expected: ctx["trigger"] — the trigger string that fired.

    Rate 1 (ON_OPPONENT_UPGRADE_SYMBOL): B:5, A:7, S:10, R:15, SR:30
    Rate 2 (ON_GAME_START):              B:10, A:15, S:20, R:75, SR:90

    D-50 cascade: when Rate1 creates an L5, the FSM must fire
    ON_UPGRADE cascade for SK_MONG_NGUA, SK_BIEN_CAM and any other
    skill sensitive to landmark creation. The return dict signals this
    via "cascade_upgrade": True.

    Args:
        player: Player whose pendant is firing.
        ctx: Must contain ctx["trigger"] and ctx["board"] for Rate1.
        cfg: PendantEntry config object (has rank_rates and rank_rates_2).
        engine: SkillEngine instance.

    Returns:
        dict for the activated effect, or None if rate check failed or
        no eligible property for Rate1.
    """
    trigger = ctx.get("trigger", "")
    board = ctx.get("board")

    if trigger == "ON_OPPONENT_UPGRADE_SYMBOL":
        rate1 = getattr(cfg.rank_rates, player.pendant_rank, 0)
        if random.randint(0, 99) < rate1:
            if board is not None:
                candidates = [
                    pos for pos in player.owned_properties
                    if board.get_tile(pos).building_level < 5
                ]
            else:
                candidates = []

            if candidates:
                chosen_pos = random.choice(candidates)
                board.get_tile(chosen_pos).building_level = 5
                # D-50: signal FSM to fire ON_UPGRADE cascade for SK_MONG_NGUA, SK_BIEN_CAM
                return {
                    "type": "create_landmark",
                    "position": chosen_pos,
                    "cascade_upgrade": True,
                }
        return None

    if trigger == "ON_GAME_START":
        rate2 = getattr(cfg.rank_rates_2, player.pendant_rank, 0)
        if random.randint(0, 99) < rate2:
            player.cash *= 2
            return {"type": "double_starting_cash"}
        return None

    return None


PENDANT_HANDLERS["PT_SIEU_SAO_CHEP"] = handle_sieu_sao_chep
