"""Pet handlers for CTP game — PET_THIEN_THAN, PET_XI_CHO, PET_PHU_THU, PET_TROI_CHAN.

D-40: Pet stamina decrements on activation (handled by engine.fire_pet).
D-39: Rate based on pet tier.
T-02.5-16: tiles_needed_to_win is bounded — max 8 color groups + 4 sides + all resorts.
"""

import random

from ctp.core.board import Board, SpaceId
from ctp.skills.registry import PET_HANDLERS


# ---------------------------------------------------------------------------
# Win condition helper
# ---------------------------------------------------------------------------

def _get_board_sides(board: Board) -> list[list[int]]:
    """Return list of 4 sides, each a list of tile positions.

    Board 32 tiles diamond layout.
    Corners at 1, 9, 17, 25 (these belong to two sides each).
    Sides (inclusive of corners):
      Side 0: 1-9    (top-right edge)
      Side 1: 9-17   (bottom-right edge)
      Side 2: 17-25  (bottom-left edge)
      Side 3: 25-32 + [1]  (top-left edge)
    """
    return [
        list(range(1, 10)),            # side 0: positions 1-9
        list(range(9, 18)),            # side 1: positions 9-17
        list(range(17, 26)),           # side 2: positions 17-25
        list(range(25, 33)) + [1],     # side 3: positions 25-32 + wrap to 1
    ]


def tiles_needed_to_win(player, board: Board) -> int:
    """Return minimum tiles needed to complete any win condition.

    Win conditions (any 1 of 3):
    1. 3 color pairs: own both CITY tiles of same color for 3 different colors
    2. 1 full side: own ALL CITY + RESORT tiles on 1 board side
    3. All Resorts: own all Resort tiles on map

    Used by PET_XI_CHO to check if opponent is 1 tile away from winning.

    T-02.5-16: Result is bounded — max 8 color groups + 4 sides + all resorts.
    """
    player_id = player.player_id
    min_needed: float = float("inf")

    # --- Condition 1: 3 color pairs ---
    # Map opt -> color using land_config (color is the shared group identifier)
    # land_config structure: {"1": {str(opt): {"color": int, ...}, ...}}
    opt_to_color: dict[int, int] = {}
    map_cfg = getattr(board, "land_config", {}).get("1", {})
    for opt_str, land_data in map_cfg.items():
        color_val = land_data.get("color")
        if color_val is not None:
            opt_to_color[int(opt_str)] = color_val

    color_groups: dict[int, dict] = {}
    for tile in board.board:
        if tile.space_id == SpaceId.CITY:
            # Use mapped color if available, fall back to opt as group key
            color = opt_to_color.get(tile.opt, tile.opt)
            if color not in color_groups:
                color_groups[color] = {"owned": 0, "total": 0}
            color_groups[color]["total"] += 1
            if tile.owner_id == player_id:
                color_groups[color]["owned"] += 1

    complete_pairs = sum(
        1 for c in color_groups.values() if c["owned"] == c["total"]
    )
    if complete_pairs >= 3:
        return 0  # already won via condition 1

    needed_for_more_pairs = 3 - complete_pairs
    # tiles still needed per partial pair (pairs where we have some but not all)
    partial_shortfalls = sorted(
        c["total"] - c["owned"]
        for c in color_groups.values()
        if 0 < c["owned"] < c["total"]
    )
    if len(partial_shortfalls) >= needed_for_more_pairs:
        tiles_cond1 = sum(partial_shortfalls[:needed_for_more_pairs])
        min_needed = min(min_needed, tiles_cond1)
    # If not enough partial pairs, condition 1 might still be achievable
    # via unowned colors, but that's a longer path — skip optimization here.

    # --- Condition 2: 1 full side ---
    sides = _get_board_sides(board)
    for side_positions in sides:
        # Collect unique positions (sides share corners)
        seen = set()
        side_tiles = []
        for pos in side_positions:
            if pos in seen:
                continue
            seen.add(pos)
            tile = board.get_tile(pos)
            if tile.space_id in (SpaceId.CITY, SpaceId.RESORT):
                side_tiles.append(tile)

        if not side_tiles:
            continue
        needed = sum(1 for t in side_tiles if t.owner_id != player_id)
        min_needed = min(min_needed, needed)

    # --- Condition 3: All Resorts ---
    resorts = [t for t in board.board if t.space_id == SpaceId.RESORT]
    if resorts:
        needed_resorts = sum(1 for r in resorts if r.owner_id != player_id)
        if needed_resorts == 0:
            return 0  # already won via condition 3
        min_needed = min(min_needed, needed_resorts)

    return int(min_needed) if min_needed != float("inf") else 999


# ---------------------------------------------------------------------------
# PET_THIEN_THAN — ON_CANT_AFFORD_TOLL
# ---------------------------------------------------------------------------

def handle_thien_than(player, ctx: dict, cfg, engine) -> dict:
    """Waive toll completely when player cannot afford it.

    Trigger: ON_CANT_AFFORD_TOLL
    Max stamina: 1 — only activates once per game.
    Stamina decrement is handled by engine.fire_pet() before this is called.

    Args:
        player: The Player whose pet is firing.
        ctx: Context dict (board, players, toll_amount, etc.).
        cfg: PetEntry config.
        engine: SkillEngine instance.

    Returns:
        {"type": "toll_waive_pet"}
    """
    return {"type": "toll_waive_pet"}


# ---------------------------------------------------------------------------
# PET_XI_CHO — ON_OPPONENT_BUILD
# ---------------------------------------------------------------------------

def handle_xi_cho(player, ctx: dict, cfg, engine) -> dict | None:
    """Build L1 on empty CITY tile + block acquisition when opponent near win.

    Trigger: ON_OPPONENT_BUILD
    Condition: tiles_needed_to_win(opponent, board) == 1
    Max stamina: 3.
    Stamina decrement is handled by engine.fire_pet().

    Args:
        player: The Player whose pet is firing.
        ctx: Must contain "board" (Board) and "opponent" (Player).
        cfg: PetEntry config.
        engine: SkillEngine instance.

    Returns:
        {"type": "xi_cho_claim", "position": int} or None if no empty tile.
    """
    board: Board = ctx["board"]
    opponent = ctx["opponent"]

    # Condition check: opponent must be exactly 1 tile away from winning
    if tiles_needed_to_win(opponent, board) != 1:
        return None

    # Find empty CITY tiles
    empty = [
        t for t in board.board
        if t.space_id == SpaceId.CITY and t.owner_id is None
    ]
    if not empty:
        return None

    chosen = random.choice(empty)
    chosen.owner_id = player.player_id
    chosen.building_level = 1
    player.add_property(chosen.position)

    # Block acquisition for 1 turn
    chosen.acquisition_blocked_turns = 1

    return {"type": "xi_cho_claim", "position": chosen.position}


# ---------------------------------------------------------------------------
# PET_PHU_THU — ON_OPPONENT_ACQUIRE_YOURS
# ---------------------------------------------------------------------------

# Steal ratio per tier (index = tier - 1)
_PHU_THU_STEAL_RATIOS = [0.5, 0.75, 1.0, 1.5, 2.0]


def handle_phu_thu(player, ctx: dict, cfg, engine) -> dict:
    """Steal X% of acquisition cost from opponent when they acquire player's tile.

    Trigger: ON_OPPONENT_ACQUIRE_YOURS
    Steal ratios by tier: 50%, 75%, 100%, 150%, 200%
    Tier 4-5: steal > 100% — opponent pays acquisition cost PLUS extra penalty.
    Max stamina: 3.
    Stamina decrement is handled by engine.fire_pet().

    Args:
        player: The Player whose pet is firing.
        ctx: Must contain "opponent" (Player) and "acquisition_cost" (float).
        cfg: PetEntry config.
        engine: SkillEngine instance.

    Returns:
        {"type": "phu_thu_steal", "amount": float}
    """
    steal_ratio = _PHU_THU_STEAL_RATIOS[player.pet_tier - 1]
    acquisition_cost: float = ctx["acquisition_cost"]
    steal_amount = acquisition_cost * steal_ratio

    ctx["opponent"].cash -= steal_amount
    player.cash += steal_amount

    return {"type": "phu_thu_steal", "amount": steal_amount}


# ---------------------------------------------------------------------------
# PET_TROI_CHAN — ON_OPPONENT_PASS_YOURS
# ---------------------------------------------------------------------------

def handle_troi_chan(player, ctx: dict, cfg, engine) -> dict:
    """Bind opponent for 1 turn — must roll even to move.

    Trigger: ON_OPPONENT_PASS_YOURS
    Effect: opponent.bound_turns += 1 (stacks if already bound).
    Max stamina: 5.
    Stamina decrement is handled by engine.fire_pet().

    FSM integration (at ROLL start):
        if player.bound_turns > 0:
            roll dice
            if odd: bound_turns -= 1, skip MOVE
            if even: bound_turns -= 1, move normally
        Check uses RAW dice result (SK_XXCT ±1 not counted per GD note).

    Args:
        player: The Player whose pet is firing.
        ctx: Must contain "opponent" (Player).
        cfg: PetEntry config.
        engine: SkillEngine instance.

    Returns:
        {"type": "bind_opponent", "target": str}
    """
    opponent = ctx["opponent"]
    opponent.bound_turns += 1  # stack if already bound

    return {"type": "bind_opponent", "target": opponent.player_id}


# ---------------------------------------------------------------------------
# Register all pet handlers
# ---------------------------------------------------------------------------

PET_HANDLERS["PET_THIEN_THAN"] = handle_thien_than
PET_HANDLERS["PET_XI_CHO"] = handle_xi_cho
PET_HANDLERS["PET_PHU_THU"] = handle_phu_thu
PET_HANDLERS["PET_TROI_CHAN"] = handle_troi_chan
