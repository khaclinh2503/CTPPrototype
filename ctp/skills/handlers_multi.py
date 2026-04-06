"""Multi-trigger complex skill handlers: SK_GAY_NHU_Y, SK_HO_DIEP, SK_SO_10.

Each skill has 2 effects with different triggers.
- SK_GAY_NHU_Y: ON_OPPONENT_TRAVEL (E1) + ON_UPGRADE (E2)
- SK_HO_DIEP: ON_OPPONENT_MOVE_SKILL (E1) + ON_UPGRADE with color pair (E2)
- SK_SO_10: ON_LAND_TRAVEL (E1) + ON_PASS_START always-active (E2)

Design rules:
- D-52: GNY E1 fires in ANY turn (reactive, including opponent's turn)
- D-50: L5 creation fires ON_UPGRADE cascade (SK_MONG_NGUA, SK_BIEN_CAM)
- D-20: SK_GAY_NHU_Y mutually exclusive with SK_TEDDY
- D-47: SK_SO_10 E2 stacks additively with SK_MU_PHEP passing bonus
- D-54: GNY E2 is Skill Walk (immune to traps); GNY E1 is Travel Walk (susceptible)
- T-02.5-12: HoDiep E1 only fires once per opponent skill activation (enforced by caller)
"""

import random

from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# SK_GAY_NHU_Y — Gậy Như Ý
# ---------------------------------------------------------------------------

def _gay_nhu_y_e1(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """E1: Follow opponent to Travel tile (reactive, fires in any turn).

    D-52: fires in opponent's turn when opponent reaches Travel tile.
    D-54: This is Travel Walk — susceptible to traps.
    Passing START: player receives passing bonus normally.
    Tile effect at Travel tile triggers normally for this player.
    """
    travel_pos = ctx.get("travel_tile_position")
    if travel_pos is None:
        return None

    current_pos = player.position
    # Calculate forward steps from current position to travel_pos (1-indexed, 32 tiles)
    steps = (travel_pos - current_pos) % 32
    if steps == 0:
        steps = 32  # full lap if already at same position

    return {
        "type": "travel_walk",
        "destination": travel_pos,
        "steps": steps,
        "trigger_tile_effect": True,   # tile effect at destination triggers normally
        "pass_start_bonus": True,      # passing START grants bonus
    }


def _gay_nhu_y_e2(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """E2: Upgrade to L5 + 70% chance move to Travel tile (same mechanic as SK_TEDDY).

    D-50: L5 creation fires ON_UPGRADE cascade.
    D-54: Move to Travel is Skill Walk (immune to traps).
    Secondary rate: 70% (fixed, not rank/star dependent).
    """
    board: Board = ctx.get("board")
    tile = ctx.get("tile")  # tile being upgraded

    # Upgrade to L5
    if tile is not None:
        tile.building_level = 5

    # 70% chance: move to nearest Travel tile (Skill Walk, immune per D-54)
    move_to_travel = random.randint(0, 99) < 70

    if move_to_travel and board is not None:
        travel_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.TRAVEL)
        if travel_pos:
            return {
                "type": "upgrade_to_l5",
                "move_to_travel": True,
                "travel_pos": travel_pos,
                "walk_type": "skill_walk",  # D-54: Skill Walk immune to traps
            }

    return {
        "type": "upgrade_to_l5",
        "move_to_travel": False,
    }


def handle_gay_nhu_y(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_GAY_NHU_Y dispatcher — routes to E1 or E2 based on trigger.

    E1: ON_OPPONENT_TRAVEL — follow opponent to Travel tile (reactive)
    E2: ON_UPGRADE — upgrade to L5 + 70% move to Travel

    Uses rank_config for E1 rate, rank_config_2 for E2 rate.
    Rate check is handled by SkillEngine.fire() using the appropriate config
    (engine caller passes trigger in ctx["trigger"]).
    """
    trigger = ctx.get("trigger")
    if trigger == "ON_OPPONENT_TRAVEL":
        return _gay_nhu_y_e1(player, ctx, cfg, engine)
    elif trigger == "ON_UPGRADE":
        return _gay_nhu_y_e2(player, ctx, cfg, engine)
    return None


SKILL_HANDLERS["SK_GAY_NHU_Y"] = handle_gay_nhu_y


# ---------------------------------------------------------------------------
# SK_HO_DIEP — Hồ Điệp
# ---------------------------------------------------------------------------

# Skills that trigger HoDiep E1 (reactive counter)
# T-02.5-12: Only fires once per opponent skill activation
MONITORED_SKILLS = {
    "SK_HQXX",       # extra roll
    "SK_TOC_CHIEN",  # extra roll after Travel
    "SK_JOKER",      # extra roll after leaving prison
    "SK_MOONWALK",   # choose movement direction
    "SK_XXCT",       # adjust ±1 step
    "SK_SO_10",      # use Travel immediately
    "SK_GAY_NHU_Y",  # follow opponent to Travel (E1 only)
}


def player_has_color_pair(player: Player, board: Board) -> bool:
    """Check if player owns at least 2 CITY tiles of the same color.

    Args:
        player: Player to check.
        board: Game board with tile and land config data.

    Returns:
        True if player owns a color pair (>= 2 CITY tiles of same color).
    """
    color_counts: dict[int, int] = {}
    for pos in player.owned_properties:
        tile = board.get_tile(pos)
        if tile.space_id == SpaceId.CITY:
            land_cfg = board.get_land_config(tile.opt)
            if land_cfg is not None:
                color = land_cfg.get("color") if isinstance(land_cfg, dict) else getattr(land_cfg, "color", None)
                if color is not None:
                    color_counts[color] = color_counts.get(color, 0) + 1
    return any(count >= 2 for count in color_counts.values())


def _find_nearest_unowned_city_on_side(board: Board, side_positions: list[int]) -> int | None:
    """Find nearest unowned CITY tile on the given board side.

    Args:
        board: Game board.
        side_positions: List of positions on the same board side.

    Returns:
        Position of nearest unowned CITY, or None if none found.
    """
    for pos in side_positions:
        tile = board.get_tile(pos)
        if tile.space_id == SpaceId.CITY and tile.owner_id is None:
            return pos
    return None


def _ho_diep_e1(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """E1: Send opponent to prison when they activate a monitored skill.

    T-02.5-12: Only fires once per opponent skill activation.
    Reactive — fires in opponent's turn.
    """
    opponent_skill_id = ctx.get("activated_skill_id")
    if opponent_skill_id not in MONITORED_SKILLS:
        return None

    opponent = ctx.get("opponent")
    if opponent is None:
        return None

    opponent.enter_prison()
    return {
        "type": "send_to_prison",
        "target": opponent.player_id,
        "triggered_by": opponent_skill_id,
    }


def _ho_diep_e2(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """E2: Move to nearest unowned CITY on same board side when building with color pair.

    Activates on ON_UPGRADE when player owns a color pair (>= 2 CITY tiles of same color).
    D-54: Teleport — tile effect does NOT trigger (just repositioned).
    Fails silently if no unowned CITY on same side.
    """
    board: Board = ctx.get("board")
    tile = ctx.get("tile")  # tile being upgraded

    if board is None or tile is None:
        return None

    # Check color pair requirement
    if not player_has_color_pair(player, board):
        return None

    # Find nearest unowned CITY on same board side
    side_positions = board.get_row_non_corner_positions(tile.position)
    nearest_empty_pos = _find_nearest_unowned_city_on_side(board, side_positions)

    if nearest_empty_pos is None:
        return None  # fail silently if no empty CITY on same side

    player.move_to(nearest_empty_pos)
    return {
        "type": "teleport_to_empty",
        "position": nearest_empty_pos,
        "trigger_tile_effect": False,  # D-54: Teleport, no tile effect
    }


def handle_ho_diep(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_HO_DIEP dispatcher — routes to E1 or E2 based on trigger.

    E1: ON_OPPONENT_MOVE_SKILL — send opponent to prison (reactive)
    E2: ON_UPGRADE — teleport to nearest unowned CITY (requires color pair)
    """
    trigger = ctx.get("trigger")
    if trigger == "ON_OPPONENT_MOVE_SKILL":
        return _ho_diep_e1(player, ctx, cfg, engine)
    elif trigger == "ON_UPGRADE":
        return _ho_diep_e2(player, ctx, cfg, engine)
    return None


SKILL_HANDLERS["SK_HO_DIEP"] = handle_ho_diep


# ---------------------------------------------------------------------------
# SK_SO_10 — Số 10
# ---------------------------------------------------------------------------

def _so_10_choose_destination(player: Player, board: Board) -> int | None:
    """Stub AI: choose best destination tile.

    Priority:
    1. Nearest unowned CITY tile
    2. Player's most expensive owned CITY tile (to collect toll)
    Falls back to player's current position if nothing else.

    Args:
        player: Current player.
        board: Game board.

    Returns:
        Position to move to (1-32).
    """
    # Priority 1: nearest unowned CITY (forward search)
    for steps in range(1, 33):
        candidate = ((player.position - 1 + steps) % 32) + 1
        tile = board.get_tile(candidate)
        if tile.space_id == SpaceId.CITY and tile.owner_id is None:
            return candidate

    # Priority 2: player's most expensive owned CITY (by building level)
    best_pos = None
    best_level = -1
    for pos in player.owned_properties:
        tile = board.get_tile(pos)
        if tile.space_id == SpaceId.CITY and tile.building_level > best_level:
            best_level = tile.building_level
            best_pos = pos

    if best_pos is not None:
        return best_pos

    # Fallback: stay at current position
    return player.position


def _so_10_e1(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """E1: After Travel tile resolves, move to any chosen tile immediately.

    D-54: Tile effect at destination does NOT trigger (just repositioned).
    AI stub: choose nearest unowned CITY or own most expensive.
    """
    board: Board = ctx.get("board")
    if board is None:
        return None

    # Allow ctx to override destination (for tests / future UI)
    chosen_pos = ctx.get("chosen_destination")
    if chosen_pos is None:
        chosen_pos = _so_10_choose_destination(player, board)

    if chosen_pos is None:
        return None

    return {
        "type": "instant_travel",
        "destination": chosen_pos,
        "trigger_tile_effect": False,  # D-54: no tile effect at destination
    }


def _so_10_e2(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """E2: Always-active 50% passing bonus increase (no rank/star scaling).

    D-47: Stacks additively with SK_MU_PHEP (e.g., 86% + 50% = 136% total increase).
    Fixed 50% regardless of rank/star.
    """
    return {
        "type": "passing_bonus_modifier",
        "percent_increase": 50,
    }


def handle_so_10(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_SO_10 dispatcher — routes to E1 or E2 based on trigger.

    E1: ON_LAND_TRAVEL — instant travel to any chosen tile after Travel resolves
    E2: ON_PASS_START — always-active 50% passing bonus modifier (D-47 stacking)
    """
    trigger = ctx.get("trigger")
    if trigger == "ON_LAND_TRAVEL":
        return _so_10_e1(player, ctx, cfg, engine)
    elif trigger == "ON_PASS_START":
        return _so_10_e2(player, ctx, cfg, engine)
    return None


SKILL_HANDLERS["SK_SO_10"] = handle_so_10
