"""Pendant handlers for own-land and opponent-land triggers.

Handlers:
- PT_TU_TRUONG: ON_LAND_OWN — refund % build cost (R1 always), pull opponents within 4 tiles at L5 (R2 rate)
- PT_BAN_TAY_VANG: ON_LAND_OWN at L5 — pull all opponents on same board side
- PT_TUI_BA_GANG: E1 ON_OPPONENT_LAND_YOURS (toll boost), E2 ON_SAME_TILE (steal % cash)
- PT_KET_VANG: E1 ON_OPPONENT_LAND_YOURS (toll boost), E2 ON_LAND_OWN (refund % build cost)

Decision refs:
- D-24: building_level == 5 is "Biểu Tượng" (Symbol/L5)
- D-27: "same side" = 1 of 4 sides of the 32-tile rhombus board
- D-48: Skip opponents already at player.position when pulling
- always_active: pendants always fire without rate check per trigger config
"""

import random

from ctp.core.constants import calc_invested_build_cost
from ctp.skills.registry import PENDANT_HANDLERS


# ---------------------------------------------------------------------------
# PT_TU_TRUONG
# ---------------------------------------------------------------------------

def handle_tu_truong(player, ctx, cfg, engine):
    """PT_TU_TRUONG — two effects on ON_LAND_OWN.

    R1 (always): Refund % of invested build cost.
        Rates: B:4%, A:10%, S:15%, R:25%, SR:50%
    R2 (rate check, L5 only): Pull opponents within 4 tiles to this position.
        Rates: B:4%, A:5%, S:10%, R:25%, SR:42%

    Args:
        player: Player who landed on own property.
        ctx: Context dict — must contain 'board', 'players'.
        cfg: PendantEntry config object with rank_rates / rank_rates_2.
        engine: SkillEngine instance.

    Returns:
        dict with 'refund' and optionally 'pulled' keys, or None if no effect.
    """
    board = ctx.get("board")
    players = ctx.get("players", [])
    tile = board.get_tile(player.position)
    result = {}

    # R1 — always fires: refund % of invested build cost
    refund_rates = {"B": 4, "A": 10, "S": 15, "R": 25, "SR": 50}
    rank = player.pendant_rank
    refund_pct = refund_rates.get(rank, 0)
    invested = calc_invested_build_cost(board, player.position)
    if invested > 0 and refund_pct > 0:
        refund = invested * (refund_pct / 100)
        player.cash += refund
        result["refund"] = refund

    # R2 — rate check, only at L5 (Biểu Tượng, D-24)
    if tile.building_level == 5:
        pull_rates = {"B": 4, "A": 5, "S": 10, "R": 25, "SR": 42}
        pull_pct = pull_rates.get(rank, 0)
        if random.randint(0, 99) < pull_pct:
            pulled = []
            for opp in players:
                if opp.player_id == player.player_id:
                    continue
                if opp.is_bankrupt:
                    continue
                # D-48: Skip opponents already at this position
                if opp.position == player.position:
                    continue
                distance = abs(opp.position - player.position)
                # Circular board distance (32 tiles)
                distance = min(distance, 32 - distance)
                if 0 < distance <= 4:
                    opp.move_to(player.position)
                    pulled.append(opp.player_id)
            if pulled:
                result["pulled"] = pulled

    return result if result else None


PENDANT_HANDLERS["PT_TU_TRUONG"] = handle_tu_truong


# ---------------------------------------------------------------------------
# PT_BAN_TAY_VANG
# ---------------------------------------------------------------------------

def handle_ban_tay_vang(player, ctx, cfg, engine):
    """PT_BAN_TAY_VANG — pull all opponents on same board side when landing L5.

    Only fires at building_level == 5 (Biểu Tượng, D-24).
    "Same side" = get_row_non_corner_positions (D-27).
    D-48: Skip opponents already at player.position.

    Rate per rank: B:2%, A:5%, S:20%, R:50%, SR:85%

    Args:
        player: Player who landed on own L5 property.
        ctx: Context dict — must contain 'board', 'players'.
        cfg: PendantEntry config object.
        engine: SkillEngine instance.

    Returns:
        dict with 'pulled' list of player_ids, or None if not triggered.
    """
    board = ctx.get("board")
    players = ctx.get("players", [])
    tile = board.get_tile(player.position)

    # Only fires at Biểu Tượng (L5)
    if tile.building_level != 5:
        return None

    rate_per_rank = {"B": 2, "A": 5, "S": 20, "R": 50, "SR": 85}
    rank = player.pendant_rank
    rate = rate_per_rank.get(rank, 0)

    if random.randint(0, 99) >= rate:
        return None

    # D-27: get all non-corner positions on same side of board
    side_positions = board.get_row_non_corner_positions(player.position)
    # Include current position in the valid side set for membership check
    same_side_set = set(side_positions)

    pulled = []
    for opp in players:
        if opp.player_id == player.player_id:
            continue
        if opp.is_bankrupt:
            continue
        # D-48: Skip opponents already at player.position
        if opp.position == player.position:
            continue
        if opp.position in same_side_set:
            opp.move_to(player.position)
            pulled.append(opp.player_id)

    return {"pulled": pulled} if pulled else None


PENDANT_HANDLERS["PT_BAN_TAY_VANG"] = handle_ban_tay_vang


# ---------------------------------------------------------------------------
# PT_TUI_BA_GANG
# ---------------------------------------------------------------------------

def handle_tui_ba_gang(player, ctx, cfg, engine):
    """PT_TUI_BA_GANG — two independent effects.

    E1 (ON_OPPONENT_LAND_YOURS, always_active): Boost toll by %.
        Rates: B:10%, A:20%, S:30%, R:50%, SR:60%
        Returns {"type": "toll_boost", "percent": N}

    E2 (ON_SAME_TILE, always_active): Steal % of opponent's cash.
        Rates: B:5%, A:7%, S:10%, R:15%, SR:36%

    Trigger is determined by ctx['trigger'] key. The caller must set this.

    Args:
        player: Owning player.
        ctx: Context dict — must contain 'trigger', 'board', 'players'.
        cfg: PendantEntry config object.
        engine: SkillEngine instance.

    Returns:
        For E1: {"type": "toll_boost", "percent": N}
        For E2: {"type": "steal", "stolen": total_stolen}
        None if trigger not recognized or no effect.
    """
    trigger = ctx.get("trigger", "")
    rank = player.pendant_rank

    if trigger == "ON_OPPONENT_LAND_YOURS":
        # E1: toll boost
        toll_boost_rates = {"B": 10, "A": 20, "S": 30, "R": 50, "SR": 60}
        pct = toll_boost_rates.get(rank, 0)
        if pct > 0:
            return {"type": "toll_boost", "percent": pct}
        return None

    if trigger == "ON_SAME_TILE":
        # E2: steal % from same-tile opponents
        steal_rates = {"B": 5, "A": 7, "S": 10, "R": 15, "SR": 36}
        steal_pct = steal_rates.get(rank, 0)
        if steal_pct == 0:
            return None

        players = ctx.get("players", [])
        total_stolen = 0.0
        for opp in players:
            if opp.player_id == player.player_id:
                continue
            if opp.is_bankrupt:
                continue
            if opp.position == player.position:
                stolen = opp.cash * (steal_pct / 100)
                opp.cash -= stolen
                player.cash += stolen
                total_stolen += stolen

        return {"type": "steal", "stolen": total_stolen} if total_stolen > 0 else None

    return None


PENDANT_HANDLERS["PT_TUI_BA_GANG"] = handle_tui_ba_gang


# ---------------------------------------------------------------------------
# PT_KET_VANG
# ---------------------------------------------------------------------------

def handle_ket_vang(player, ctx, cfg, engine):
    """PT_KET_VANG — two independent effects.

    E1 (ON_OPPONENT_LAND_YOURS, always_active): Boost toll by %.
        Rates: B:10%, A:20%, S:30%, R:50%, SR:60%
        Returns {"type": "toll_boost", "percent": N}
        Stacks additively with PT_TUI_BA_GANG E1 (D-45).

    E2 (ON_LAND_OWN, always_active): Refund % of invested build cost.
        Rates: B:10%, A:15%, S:25%, R:50%, SR:60%

    Trigger is determined by ctx['trigger'] key.

    Args:
        player: Owning player.
        ctx: Context dict — must contain 'trigger', 'board'.
        cfg: PendantEntry config object.
        engine: SkillEngine instance.

    Returns:
        For E1: {"type": "toll_boost", "percent": N}
        For E2: {"type": "refund", "amount": N}
        None if trigger not recognized or no effect.
    """
    trigger = ctx.get("trigger", "")
    rank = player.pendant_rank

    if trigger == "ON_OPPONENT_LAND_YOURS":
        # E1: toll boost
        toll_boost_rates = {"B": 10, "A": 20, "S": 30, "R": 50, "SR": 60}
        pct = toll_boost_rates.get(rank, 0)
        if pct > 0:
            return {"type": "toll_boost", "percent": pct}
        return None

    if trigger == "ON_LAND_OWN":
        # E2: refund % of invested build cost
        refund_rates = {"B": 10, "A": 15, "S": 25, "R": 50, "SR": 60}
        refund_pct = refund_rates.get(rank, 0)
        if refund_pct == 0:
            return None

        board = ctx.get("board")
        if board is None:
            return None

        invested = calc_invested_build_cost(board, player.position)
        if invested <= 0:
            return None

        refund = invested * (refund_pct / 100)
        player.cash += refund
        return {"type": "refund", "amount": refund}

    return None


PENDANT_HANDLERS["PT_KET_VANG"] = handle_ket_vang
