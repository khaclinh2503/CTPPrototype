"""Position/same-tile + travel skill handlers.

Covers:
- SK_SUNG_VANG: ON_MOVE_TO_OPPONENT — steals 15% cash + rate-based teleport
- SK_LOC_XOAY:  ON_MOVE_TO_OPPONENT — disables skills/cards + rate-based teleport
- SK_TOC_CHIEN: ON_LAND_TRAVEL      — grants extra roll after Travel tile

D-51: Only fire during player's own turn (is_player_turn must be True).
Execution order when both SungVang and LocXoay fire at same tile:
  SungVang E1 (steal) -> LocXoay check -> SungVang E2 (teleport) check
"""

import random

from ctp.core.constants import calc_invested_build_cost
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _most_expensive_property(board, player):
    """Return the tile position with the highest invested build cost owned by
    player, or None if player owns no properties.

    Args:
        board: Board instance.
        player: Player instance.

    Returns:
        int position of most expensive property, or None.
    """
    if not player.owned_properties:
        return None
    return max(
        player.owned_properties,
        key=lambda pos: calc_invested_build_cost(board, pos),
    )


# ---------------------------------------------------------------------------
# SK_SUNG_VANG — Sừng Vàng
# Trigger: ON_MOVE_TO_OPPONENT
# Effect 1 (100%): steal 15% of opponent's cash
# Effect 2 (rate-based): teleport opponent to player's most expensive property
# During interaction: opponent cannot active skills or use held cards
# D-51: only fires during player's own turn
# Rate: A base=28 chance=2 / S base=38 chance=3
# ---------------------------------------------------------------------------

def handle_sung_vang(player, ctx, cfg, engine):
    """Handler for SK_SUNG_VANG.

    Args:
        player: Player who owns the skill.
        ctx: Dict with keys: opponent (Player), board, players, is_player_turn.
        cfg: SkillEntry config object.
        engine: SkillEngine instance.

    Returns:
        dict with effect details, or None if conditions not met.
    """
    # D-51: only fire on player's own turn
    if not ctx.get("is_player_turn", False):
        return None

    opponent = ctx.get("opponent")
    board = ctx.get("board")
    if opponent is None or board is None:
        return None

    result = {}

    # --- Effect 1 (always, 100%): steal 15% cash + block interaction ---
    stolen = opponent.cash * 0.15
    opponent.cash -= stolen
    player.cash += stolen
    result["stolen"] = stolen
    result["effect1"] = True

    # Block opponent interaction for duration of this event
    # (flags set before any further processing)
    opponent.skills_disabled_this_turn = True
    opponent.cards_disabled_this_turn = True
    result["opponent_blocked"] = True

    # --- Effect 2 (rate-based): teleport opponent to most expensive property ---
    rate = engine.calc_rate(cfg, player)
    if random.randint(0, 99) < rate:
        target_pos = _most_expensive_property(board, player)
        if target_pos is not None:
            opponent.move_to(target_pos)
            result["effect2"] = True
            result["teleport_to"] = target_pos

    return result


SKILL_HANDLERS["SK_SUNG_VANG"] = handle_sung_vang


# ---------------------------------------------------------------------------
# SK_LOC_XOAY — Lốc Xoáy
# Trigger: ON_MOVE_TO_OPPONENT
# Primary rate check, then secondary 60% fixed check
# On both pass:
#   1. opponent.skills_disabled_this_turn = True
#   2. opponent.cards_disabled_this_turn = True
#   3. Teleport opponent to player's most expensive property (tile effect fires)
#      If player has no properties: teleport skipped, disable still happens
# D-51: only fires during player's own turn
# Rate: A base=38 chance=2 / S base=48 chance=3 / secondary_rate=60
# ---------------------------------------------------------------------------

_LOC_XOAY_SECONDARY_RATE = 60


def handle_loc_xoay(player, ctx, cfg, engine):
    """Handler for SK_LOC_XOAY.

    Args:
        player: Player who owns the skill.
        ctx: Dict with keys: opponent (Player), board, players, is_player_turn.
        cfg: SkillEntry config object.
        engine: SkillEngine instance.

    Returns:
        dict with effect details, or None if conditions not met.
    """
    # D-51: only fire on player's own turn
    if not ctx.get("is_player_turn", False):
        return None

    opponent = ctx.get("opponent")
    board = ctx.get("board")
    if opponent is None or board is None:
        return None

    # Primary rate check (done by engine before calling handler when cfg.always_active=False,
    # but SK_LOC_XOAY has its own secondary check so we re-evaluate here)
    rate = engine.calc_rate(cfg, player)
    if random.randint(0, 99) >= rate:
        return None

    # Secondary 60% fixed check
    if random.randint(0, 99) >= _LOC_XOAY_SECONDARY_RATE:
        return None

    result = {}

    # Disable opponent skills + cards for rest of turn
    opponent.skills_disabled_this_turn = True
    opponent.cards_disabled_this_turn = True
    result["skills_disabled"] = True
    result["cards_disabled"] = True

    # Teleport opponent to most expensive property (skip if none)
    target_pos = _most_expensive_property(board, player)
    if target_pos is not None:
        opponent.move_to(target_pos)
        result["teleport_to"] = target_pos
    else:
        result["teleport_to"] = None

    return result


SKILL_HANDLERS["SK_LOC_XOAY"] = handle_loc_xoay


# ---------------------------------------------------------------------------
# SK_TOC_CHIEN — Tốc Chiến
# Trigger: ON_LAND_TRAVEL (after Travel tile resolution)
# Effect: grant player an extra roll
# Rate: A base=40 chance=2 / S base=50 chance=4
# Note: engine handles primary rate check via cfg.always_active=False
# ---------------------------------------------------------------------------

def handle_toc_chien(player, ctx, cfg, engine):
    """Handler for SK_TOC_CHIEN.

    Args:
        player: Player who owns the skill.
        ctx: Dict with keys: board, players.
        cfg: SkillEntry config object.
        engine: SkillEngine instance.

    Returns:
        dict {"type": "extra_roll"} to signal extra roll, or None.
    """
    # Rate check handled by engine (cfg.always_active=False)
    # This handler is only called when rate check passed
    return {"type": "extra_roll"}


SKILL_HANDLERS["SK_TOC_CHIEN"] = handle_toc_chien
