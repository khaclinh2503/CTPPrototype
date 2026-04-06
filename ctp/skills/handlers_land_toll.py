"""Skill handlers for RESOLVE_TILE toll interactions.

Covers: SK_BUA_SET (ON_LAND_OPPONENT), SK_NGOI_SAO (ON_OPPONENT_LAND_YOURS),
        SK_CUONG_CHE (ON_OPPONENT_MOVE_TO_YOURS).

D-45: Free-toll skills checked first; boost only applies if toll > 0.
D-49: SK_CUONG_CHE only fires during OTHER player's turn (not skill owner's turn).
D-51: SK_BUA_SET only fires during PLAYER's own turn.
D-48: SK_CUONG_CHE skips if opponent already at target L5.
D-54: Teleport movement is immune to traps; Skill Walk movement is immune.
"""

import random

from ctp.core.board import SpaceId
from ctp.core.constants import calc_invested_build_cost
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# SK_BUA_SET — waive toll + move to nearest unowned CITY
# Trigger: ON_LAND_OPPONENT (fires in player's own turn — D-51)
# ---------------------------------------------------------------------------

def handle_bua_set(player, ctx: dict, cfg, engine) -> dict | None:
    """SK_BUA_SET: Waive toll and reposition to nearest unowned CITY.

    D-51: Only fires when is_player_turn=True (player's own turn).
    Effect 1: Toll waived (toll = 0).
    Effect 2: Acquisition/upgrade proceed normally (handled by FSM).
    Effect 3: After acquisition/upgrade, move to nearest unowned CITY tile.
              Tile effect at destination does NOT trigger (repositioned only).

    ctx keys required:
        tile: Tile player landed on.
        board: Board instance.
        is_player_turn: bool — True if this is the acting player's own turn.

    Returns:
        dict with type="toll_waive" and move_to_nearest_unowned=True, or None.
    """
    if not ctx.get("is_player_turn", False):
        return None  # D-51: only own turn

    board = ctx["board"]
    current_pos = player.position

    nearest_pos = _find_nearest_unowned_city(board, current_pos)

    return {
        "type": "toll_waive",
        "move_to_nearest_unowned": True,
        "destination": nearest_pos,  # None if no unowned CITY exists
    }


def _find_nearest_unowned_city(board, from_pos: int) -> int | None:
    """Find nearest unowned CITY tile from from_pos (forward wrap-around).

    Args:
        board: Board instance.
        from_pos: Starting position (1-32).

    Returns:
        Position (1-32) of nearest unowned CITY, or None.
    """
    for steps in range(1, 33):
        candidate = ((from_pos - 1 + steps) % 32) + 1
        tile = board.get_tile(candidate)
        if tile.space_id == SpaceId.CITY and tile.owner_id is None:
            return candidate
    return None


# ---------------------------------------------------------------------------
# SK_NGOI_SAO — double toll + 70% angel card destruction
# Trigger: ON_OPPONENT_LAND_YOURS (reactive, fires in any turn — D-52)
# ---------------------------------------------------------------------------

ANGEL_CARD_ITEM_ID = "IT_CA_1"  # Thiên Thần card item id
ANGEL_DESTROY_CHANCE = 70       # percent


def handle_ngoi_sao(player, ctx: dict, cfg, engine) -> dict | None:
    """SK_NGOI_SAO: Double toll; 70% chance to destroy opponent's angel card.

    Effect 1: Toll × 2 (always when skill activates).
    Effect 2: If opponent has Thiên Thần (IT_CA_1):
        - 70%: card destroyed, opponent still pays toll × 2.
        - 30%: card works normally (toll waived).

    ctx keys required:
        opponent: Player who landed on this tile.
        tile: Tile that was landed on.
        board: Board instance (optional, for context).

    Returns:
        dict with type="toll_multiply", factor=2, angel_destroyed=bool | None.
    """
    opponent = ctx.get("opponent")
    if opponent is None:
        return None

    angel_destroyed = False

    if opponent.held_card == ANGEL_CARD_ITEM_ID:
        # Opponent attempts to use angel card to counter
        if random.randint(1, 100) <= ANGEL_DESTROY_CHANCE:
            # 70%: card destroyed, opponent still pays toll × 2
            opponent.held_card = None
            angel_destroyed = True
            # toll_multiply still applies (angel failed)
        else:
            # 30%: angel card works normally — toll is waived entirely
            opponent.held_card = None
            return {
                "type": "toll_multiply",
                "factor": 2,
                "angel_destroyed": False,
                "angel_blocked": True,  # angel succeeded, toll waived
                "toll_waived": True,
            }

    return {
        "type": "toll_multiply",
        "factor": 2,
        "angel_destroyed": angel_destroyed,
        "angel_blocked": False,
    }


# ---------------------------------------------------------------------------
# SK_CUONG_CHE — teleport opponent to most expensive L5 (Biểu Tượng)
# Trigger: ON_OPPONENT_MOVE_TO_YOURS (reactive, fires during OTHER's turn — D-49)
# ---------------------------------------------------------------------------

def handle_cuong_che(player, ctx: dict, cfg, engine) -> dict | None:
    """SK_CUONG_CHE: Teleport opponent to player's most expensive L5 property.

    D-49: Only fires during OTHER player's turn (not skill owner's turn).
    D-48: Skip if opponent is already at the target L5 position.
    Fail silently if player has no L5 properties.
    Tile effect (toll) at L5 triggers normally after teleport.

    ctx keys required:
        opponent: Player being teleported.
        board: Board instance.
        is_opponent_turn: bool — True if this is the opponent's turn.

    Returns:
        dict with type="teleport", destination=int, or None.
    """
    # D-49: only during opponent's turn (not owner's own turn)
    if not ctx.get("is_opponent_turn", False):
        return None

    opponent = ctx.get("opponent")
    board = ctx.get("board")
    if opponent is None or board is None:
        return None

    # Find all L5 (Biểu Tượng) properties owned by this player
    landmarks = [
        board.get_tile(pos)
        for pos in player.owned_properties
        if board.get_tile(pos).building_level == 5
    ]

    if not landmarks:
        return None  # Fail silently — no L5 properties

    # Choose most expensive L5 by invested build cost
    target_tile = max(
        landmarks,
        key=lambda t: calc_invested_build_cost(board, t.position),
    )

    # D-48: skip if opponent already at target
    if opponent.position == target_tile.position:
        return None

    return {
        "type": "teleport",
        "destination": target_tile.position,
        "movement_type": "teleport",  # D-54: immune to traps
    }


# ---------------------------------------------------------------------------
# Register handlers
# ---------------------------------------------------------------------------

SKILL_HANDLERS["SK_BUA_SET"] = handle_bua_set
SKILL_HANDLERS["SK_NGOI_SAO"] = handle_ngoi_sao
SKILL_HANDLERS["SK_CUONG_CHE"] = handle_cuong_che
