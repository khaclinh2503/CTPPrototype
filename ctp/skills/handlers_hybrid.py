"""Hybrid upgrade+land skill handlers: SK_AO_ANH, SK_BIEN_CAM.

Both skills have dual triggers (ON_UPGRADE + ON_LAND own L5) and set board-level traps.

D-55 (trap checking on move) is handled in handlers_move.check_traps — not here.
"""

from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# Helper: find opponent's most expensive property (stub AI for SK_BIEN_CAM)
# ---------------------------------------------------------------------------

def _choose_stop_sign_position(board, players, current_player) -> int | None:
    """Stub AI: choose opponent's most expensive property tile.

    Returns the position of the highest-value tile owned by an opponent,
    or None if no opponent property exists.

    Args:
        board: Board instance.
        players: List of all Player objects.
        current_player: The player placing the stop sign.

    Returns:
        Tile position (1-32) or None.
    """
    best_pos = None
    best_toll = -1

    for tile in board.board:
        if tile.owner_id is None or tile.owner_id == current_player.player_id:
            continue
        if tile.building_level == 0:
            continue
        land_cfg = board.get_land_config(tile.opt)
        if land_cfg is None:
            continue
        level_cfg = land_cfg.get("building", {}).get(str(tile.building_level))
        if level_cfg is None:
            continue
        toll = level_cfg.get("toll", 0) if isinstance(level_cfg, dict) else getattr(level_cfg, "toll", 0)
        if toll > best_toll:
            best_toll = toll
            best_pos = tile.position

    return best_pos


# ---------------------------------------------------------------------------
# SK_AO_ANH — Ảo Ảnh
# Triggers: ON_UPGRADE (any level), ON_LAND (own property at L5)
# Effect: place illusion at current tile; creator is immune
# ---------------------------------------------------------------------------

def handle_ao_anh(player, ctx, cfg, engine):
    """Place illusion trap at current tile.

    ON_UPGRADE: always triggers (any level).
    ON_LAND: only triggers when landing on own property at building_level == 5.

    Global singleton: new illusion overwrites old one (any owner).
    Creator immune — checked in movement code via board.illusion_owner_id.

    Args:
        player: Player who owns the skill.
        ctx: dict with keys:
            - tile: Tile object (current tile)
            - board: Board object
            - trigger: str, "ON_UPGRADE" or "ON_LAND"
        cfg: SkillEntry config.
        engine: SkillEngine instance.

    Returns:
        dict with illusion_position set, or None if condition not met.
    """
    trigger = ctx.get("trigger")
    tile = ctx.get("tile")
    board = ctx.get("board")

    if tile is None or board is None:
        return None

    if trigger == "ON_LAND":
        # Only triggers at own L5
        if tile.owner_id != player.player_id or tile.building_level != 5:
            return None
    # ON_UPGRADE: always valid (no level restriction)

    # Place illusion — overwrites any existing one (global singleton)
    board.illusion_position = tile.position
    board.illusion_owner_id = player.player_id  # creator immune

    return {"illusion_position": tile.position, "illusion_owner_id": player.player_id}


SKILL_HANDLERS["SK_AO_ANH"] = handle_ao_anh


# ---------------------------------------------------------------------------
# SK_BIEN_CAM — Biển Cấm
# Triggers: ON_UPGRADE (only to L5), ON_LAND (own L5)
# Effect: player chooses any tile to place stop sign; affects everyone
# ---------------------------------------------------------------------------

def handle_bien_cam(player, ctx, cfg, engine):
    """Place stop sign trap at a chosen tile.

    ON_UPGRADE: only triggers when upgrading to building_level == 5.
    ON_LAND: only triggers when landing on own property at building_level == 5.

    Global singleton: new sign overwrites old one (any owner).
    Unlike illusion, stop sign affects EVERYONE including creator.

    Args:
        player: Player who owns the skill.
        ctx: dict with keys:
            - tile: Tile object (current tile)
            - board: Board object
            - trigger: str, "ON_UPGRADE" or "ON_LAND"
            - new_level: int (only present for ON_UPGRADE), level upgraded to
            - choose_fn: optional callable(board, players, player) -> int | None
            - players: list of all Player objects (for stub AI)
        cfg: SkillEntry config.
        engine: SkillEngine instance.

    Returns:
        dict with stop_sign_position set, or None if condition not met.
    """
    trigger = ctx.get("trigger")
    tile = ctx.get("tile")
    board = ctx.get("board")

    if tile is None or board is None:
        return None

    if trigger == "ON_UPGRADE":
        # Only triggers when upgrading to L5
        new_level = ctx.get("new_level")
        if new_level != 5:
            return None
    elif trigger == "ON_LAND":
        # Only triggers at own L5
        if tile.owner_id != player.player_id or tile.building_level != 5:
            return None
    else:
        return None

    # Determine target position
    choose_fn = ctx.get("choose_fn")
    players = ctx.get("players", [])

    if choose_fn is not None:
        chosen_pos = choose_fn(board)
    else:
        # Stub AI: choose opponent's most expensive property
        chosen_pos = _choose_stop_sign_position(board, players, player)

    if chosen_pos is None:
        # Fallback: place on current tile
        chosen_pos = tile.position

    # Place stop sign — overwrites any existing one (global singleton)
    board.stop_sign_position = chosen_pos

    return {"stop_sign_position": chosen_pos}


SKILL_HANDLERS["SK_BIEN_CAM"] = handle_bien_cam
