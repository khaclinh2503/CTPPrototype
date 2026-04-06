"""MOVE-trigger skill handlers: SK_CAM_CO, SK_PHA_HUY + trap check helper.

D-57: SK_CAM_CO and SK_PHA_HUY only fire during "dice_walk" or "sweep_walk".
D-55: Traps (illusion / stop_sign) affect Dice Walk, Sweep Walk, Travel Walk.
      Teleport and Skill Walk are immune.

Handler signature: handler(player, ctx, cfg, engine) -> result | None
  ctx keys for ON_MOVE_PASS:
    tile          - Tile being passed
    board         - Board instance
    movement_type - str: "dice_walk" | "sweep_walk" | "travel_walk" | "teleport" | "skill_walk"
    players       - list[Player] (used by SK_PHA_HUY to find tile owner)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ctp.core.board import SpaceId
from ctp.core.constants import calc_invested_build_cost
from ctp.skills.registry import SKILL_HANDLERS

if TYPE_CHECKING:
    from ctp.core.board import Board, Tile
    from ctp.core.models import Player

# Movement types that allow SK_CAM_CO / SK_PHA_HUY to fire (D-57)
_MOVE_SKILL_ALLOWED = frozenset({"dice_walk", "sweep_walk"})

# Movement types that are immune to traps (D-55)
_TRAP_IMMUNE = frozenset({"teleport", "skill_walk"})


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _find_player(players: list, player_id: str):
    """Return the player with the given player_id, or None."""
    for p in players:
        if p.player_id == player_id:
            return p
    return None


# ---------------------------------------------------------------------------
# SK_CAM_CO handler
# ---------------------------------------------------------------------------

def handle_cam_co(player: "Player", ctx: dict, cfg, engine) -> dict | None:
    """SK_CAM_CO — Cắm Cờ: claim unowned CITY tiles while passing during move.

    D-57: Only fires during dice_walk or sweep_walk.
    Rate: uses player.cam_co_current_rate (initialized to calc_rate at turn start).
    Rate decay: [1, 3, 5, 7] per activation within the turn.

    Returns:
        dict with action="cam_co_claimed", position=<pos> if tile claimed.
        None otherwise.
    """
    movement_type: str = ctx.get("movement_type", "")
    if movement_type not in _MOVE_SKILL_ALLOWED:
        return None

    tile = ctx["tile"]

    # Only targets unowned CITY tiles
    if tile.space_id != SpaceId.CITY:
        return None
    if tile.owner_id is not None:
        return None

    # Rate check using per-turn decaying rate
    rate = player.cam_co_current_rate
    if random.randint(0, 99) >= rate:
        return None

    # Claim tile
    tile.owner_id = player.player_id
    player.add_property(tile.position)
    # building_level stays 0 (player has not built anything)

    # Apply rate decay for next check this turn
    decay = [1, 3, 5, 7]
    if player.cam_co_decay_index < len(decay):
        player.cam_co_current_rate -= decay[player.cam_co_decay_index]
        player.cam_co_decay_index += 1

    return {"action": "cam_co_claimed", "position": tile.position}


SKILL_HANDLERS["SK_CAM_CO"] = handle_cam_co


# ---------------------------------------------------------------------------
# SK_PHA_HUY handler
# ---------------------------------------------------------------------------

def handle_pha_huy(player: "Player", ctx: dict, cfg, engine) -> dict | None:
    """SK_PHA_HUY — Phá Hủy: destroy opponent property while passing; get 50% refund.

    D-57: Only fires during dice_walk or sweep_walk.
    After destruction: immediately chain SK_CAM_CO check on the (now empty) tile.

    Returns:
        dict with action="pha_huy_destroyed", position=<pos>, refund=<amount> if destroyed.
        None otherwise.
    """
    movement_type: str = ctx.get("movement_type", "")
    if movement_type not in _MOVE_SKILL_ALLOWED:
        return None

    tile = ctx["tile"]
    board = ctx["board"]
    players: list = ctx.get("players", [])

    # Only targets opponent-owned CITY or RESORT tiles
    if tile.space_id not in (SpaceId.CITY, SpaceId.RESORT):
        return None
    if tile.owner_id is None:
        return None
    if tile.owner_id == player.player_id:
        return None

    # Calculate refund before modifying tile
    invested = calc_invested_build_cost(board, tile.position)
    refund = invested * 0.5

    # Give refund and destroy tile
    player.cash += refund
    owner = _find_player(players, tile.owner_id)
    if owner is not None:
        owner.remove_property(tile.position)
    tile.building_level = 0
    tile.owner_id = None

    # Chain: tile is now unowned — check SK_CAM_CO immediately (same move step)
    if "SK_CAM_CO" in player.skills and engine is not None:
        engine.fire("ON_MOVE_PASS", player, ctx)

    return {
        "action": "pha_huy_destroyed",
        "position": tile.position,
        "refund": refund,
    }


SKILL_HANDLERS["SK_PHA_HUY"] = handle_pha_huy


# ---------------------------------------------------------------------------
# Trap check helper
# ---------------------------------------------------------------------------

def check_traps(board: "Board", player: "Player", tile_position: int, movement_type: str):
    """D-55: Check illusion / stop_sign traps during movement.

    Teleport and Skill Walk are immune (returns immediately without checking).
    Dice Walk, Sweep Walk, and Travel Walk are susceptible.

    Illusion: does NOT affect the player who placed it (board.illusion_owner_id).

    Args:
        board: Game board.
        player: Moving player.
        tile_position: Position of the tile being entered.
        movement_type: Current movement type string.

    Returns:
        (should_stop: bool, trap_type: str | None)
        should_stop=True means movement must stop at this tile.
        trap_type is "illusion" or "stop_sign" or None.
    """
    if movement_type in _TRAP_IMMUNE:
        return False, None

    # Illusion check (SK_AO_ANH)
    illusion_owner = getattr(board, "illusion_owner_id", None)
    if (
        board.illusion_position is not None
        and board.illusion_position == tile_position
        and player.player_id != illusion_owner
    ):
        board.illusion_position = None  # consumed on trigger
        return True, "illusion"

    # Stop sign check (SK_BIEN_CAM)
    if (
        board.stop_sign_position is not None
        and board.stop_sign_position == tile_position
    ):
        board.stop_sign_position = None  # consumed on trigger
        return True, "stop_sign"

    return False, None
