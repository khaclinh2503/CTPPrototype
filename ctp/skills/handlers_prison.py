"""handlers_prison.py — Prison + landmark skill handlers.

Skills:
- SK_JOKER: Prison escape skill (ON_ENTER_PRISON)
- SK_HQXX: Hộp Quà Xúc Xắc — any-tile skill (ON_LAND)
- SK_LAU_DAI_TINH_AI: Lâu Đài Tình Ái — L5 landmark pull (ON_LAND)

Rate configs:
- SK_JOKER: A: base=50, chance=2; S: base=60, chance=3
- SK_HQXX: A: base=20, chance=1; S: base=25, chance=2
- SK_LAU_DAI_TINH_AI: A: base=38, chance=2; S: base=48, chance=3
"""

import random
from ctp.core.board import SpaceId
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# SK_JOKER handler
# ---------------------------------------------------------------------------

def handle_joker(player, ctx, cfg, engine):
    """SK_JOKER: Prison escape with city-teleport + extra roll.

    TH1 (is_player_turn=True): All 3 effects immediately:
        1. exit_prison()
        2. Move to chosen unowned CITY tile (tile effect does NOT trigger)
        3. Return {"type": "extra_roll"}

    TH2 (is_player_turn=False): Only exit immediately, defer 2+3:
        1. exit_prison()
        2. player.joker_pending = True (handled at next turn start)

    D-54: Movement to unowned CITY is Skill Walk immune (tile effect skipped).
    T-02.5-07: Only exit_prison() when actually in prison to avoid double-exit.
    """
    board = ctx.get("board")
    is_player_turn = ctx.get("is_player_turn", True)
    choose_fn = ctx.get("choose_fn")

    # T-02.5-07: Guard against double-exit
    if player.prison_turns_remaining <= 0:
        return None

    # Effect 1: immediate exit prison
    player.exit_prison()

    if is_player_turn:
        # TH1: all 3 effects now
        _move_to_unowned_city(player, board, choose_fn)
        return {"type": "extra_roll"}
    else:
        # TH2: defer effects 2+3 to next turn
        player.joker_pending = True
        return {"type": "joker_pending"}


def resolve_joker_pending(player, ctx):
    """Resolve deferred SK_JOKER effects at start of player's next turn.

    Called by FSM at turn start when player.joker_pending is True.
    Effects: move to unowned CITY + grant extra roll.

    Args:
        player: Player with joker_pending=True.
        ctx: Context dict with board, choose_fn.

    Returns:
        {"type": "extra_roll"} to signal extra roll needed.
    """
    player.joker_pending = False
    board = ctx.get("board")
    choose_fn = ctx.get("choose_fn")
    _move_to_unowned_city(player, board, choose_fn)
    return {"type": "extra_roll"}


def _move_to_unowned_city(player, board, choose_fn=None):
    """Move player to an unowned CITY tile.

    If no unowned CITY exists, skip the move (per SK_JOKER spec).
    Stub AI: choose nearest to current position (forward direction).

    Args:
        player: Player to move.
        board: Board instance.
        choose_fn: Optional callable(list[Tile]) -> Tile for selection.
    """
    if board is None:
        return

    unowned = [
        t for t in board.board
        if t.space_id == SpaceId.CITY and t.owner_id is None
    ]
    if not unowned:
        return  # no unowned CITY — skip move, effects 1+3 still apply

    if choose_fn is not None:
        chosen = choose_fn(unowned)
    else:
        # Stub AI: nearest in forward direction from current position
        chosen = _nearest_forward(player.position, unowned)

    if chosen is not None:
        player.move_to(chosen.position)


def _nearest_forward(from_pos: int, tiles: list) -> object:
    """Return the tile nearest to from_pos in forward (clockwise) direction.

    Args:
        from_pos: Current position (1-32).
        tiles: List of Tile objects to search.

    Returns:
        Nearest Tile in forward direction, or None if list is empty.
    """
    if not tiles:
        return None

    positions = {t.position: t for t in tiles}
    for steps in range(1, 33):
        candidate = ((from_pos - 1 + steps) % 32) + 1
        if candidate in positions:
            return positions[candidate]
    return None


SKILL_HANDLERS["SK_JOKER"] = handle_joker


# ---------------------------------------------------------------------------
# SK_HQXX handler
# ---------------------------------------------------------------------------

def handle_hqxx(player, ctx, cfg, engine):
    """SK_HQXX: Hộp Quà Xúc Xắc — extra roll + push same-side opponents + reset doubles.

    3 simultaneous effects:
    1. Grant extra roll (return {"type": "extra_roll"})
    2. Push opponents on same board side to prison
    3. Reset player.consecutive_doubles = 0
    """
    board = ctx.get("board")
    players = ctx.get("players", [])

    # Effect 3: reset doubles
    player.consecutive_doubles = 0

    # Effect 2: push same-side opponents to prison
    if board is not None:
        side_positions = board.get_row_non_corner_positions(player.position)
        for opp in players:
            if opp.player_id != player.player_id and not opp.is_bankrupt:
                if opp.position in side_positions:
                    opp.enter_prison()

    # Effect 1: grant extra roll
    return {"type": "extra_roll"}


SKILL_HANDLERS["SK_HQXX"] = handle_hqxx


# ---------------------------------------------------------------------------
# SK_LAU_DAI_TINH_AI handler
# ---------------------------------------------------------------------------

def handle_lau_dai_tinh_ai(player, ctx, cfg, engine):
    """SK_LAU_DAI_TINH_AI: Lâu Đài Tình Ái — pull random opponent to player's L5.

    Only fires when:
    - tile.owner_id == player.player_id (own tile)
    - tile.building_level == 5 (L5 landmark)

    D-48: Skip if chosen opponent is already at this position.
    Tile effect (toll) triggers normally for the pulled opponent — caller's responsibility.
    """
    tile = ctx.get("tile")
    players = ctx.get("players", [])

    # Guard: only fire at own L5
    if tile is None:
        return None
    if tile.owner_id != player.player_id:
        return None
    if tile.building_level != 5:
        return None

    # Find non-bankrupt opponents
    opponents = [
        p for p in players
        if p.player_id != player.player_id and not p.is_bankrupt
    ]
    if not opponents:
        return None

    target = random.choice(opponents)

    # D-48: skip if opponent already at this position
    if target.position == player.position:
        return {"type": "lau_dai_tinh_ai_skipped", "reason": "already_at_position"}

    target.move_to(player.position)
    return {"type": "lau_dai_tinh_ai_pull", "target_id": target.player_id}


SKILL_HANDLERS["SK_LAU_DAI_TINH_AI"] = handle_lau_dai_tinh_ai
