"""UPGRADE-trigger skill handlers: SK_TEDDY, SK_O_KY_DIEU, SK_MONG_NGUA.

D-23: "Nha cap 3" = building_level 4 (L4)
D-24: "Bieu Tuong" = building_level 5 (L5 max)
D-28: Resort chi co 1 cap — khi cuop chi doi owner_id
D-50: Khi Teddy tao L5, phat tin hieu ON_UPGRADE cascade (SK_MONG_NGUA, SK_BIEN_CAM)
T-02.5-08: Bounded loop (exactly 32 iterations) cho sweep_walk
"""

import random

from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.skills.registry import SKILL_HANDLERS

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _find_player(players: list, player_id: str) -> Player | None:
    """Tim Player theo player_id trong danh sach players."""
    for p in players:
        if p.player_id == player_id:
            return p
    return None


def _find_resort_on_side(board: Board, tile_pos: int) -> object | None:
    """Tim Resort tile tren cung canh ban co voi tile_pos.

    Dung get_row_non_corner_positions() de lay cac o cung hang,
    sau do quet RESORT.

    Args:
        board: Board instance.
        tile_pos: Vi tri o dat vua xay Bieu Tuong.

    Returns:
        Tile object neu tim thay Resort, None neu khong co.
    """
    positions = board.get_row_non_corner_positions(tile_pos)
    for pos in positions:
        tile = board.get_tile(pos)
        if tile.space_id == SpaceId.RESORT:
            return tile
    return None


# ---------------------------------------------------------------------------
# SK_TEDDY handler
# ---------------------------------------------------------------------------


def handle_teddy(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_TEDDY: ON_UPGRADE — nang cap thang len L5, 60% co the di den Travel.

    Effect 1 (da active — duoc goi sau khi rate check pass):
        Nang cap tile len L5 (mien phi — chi tra tien den chosen_level).

    Effect 2 (60% fixed):
        Di chuyen den Travel tile gan nhat (Skill Walk immune per D-54).

    D-50: Sau khi tao L5, phat tin hieu ON_UPGRADE cascade cho
          SK_MONG_NGUA va SK_BIEN_CAM.

    D-20: Mutually exclusive voi SK_GAY_NHU_Y (enforce o cap assign).

    ctx keys:
        tile: Tile dang duoc nang cap.
        board: Board instance.
        players: Danh sach tat ca Player.
        chosen_level: Cap player da tra tien (truoc khi Teddy can thiep).
    """
    tile = ctx.get("tile")
    board = ctx.get("board")
    players = ctx.get("players", [])

    if tile is None or board is None:
        return None

    # Effect 1: nang cap len L5
    tile.building_level = 5

    result: dict = {"type": "upgrade_to_l5", "move_to_travel": False, "travel_pos": None}

    # D-50: phat tin hieu ON_UPGRADE cascade (new_level=5) cho cac skill khac
    # Engine goi handler ngay neu co (SK_MONG_NGUA, SK_BIEN_CAM)
    cascade_ctx = dict(ctx)
    cascade_ctx["new_level"] = 5
    cascade_ctx["from_teddy"] = True  # tranh vong lap
    if not ctx.get("from_teddy"):
        engine.fire("ON_UPGRADE", player, cascade_ctx)

    # Effect 2: 60% di den Travel tile
    if random.randint(0, 99) < 60:
        travel_pos = board.find_nearest_tile_by_space_id(player.position, SpaceId.TRAVEL)
        if travel_pos is not None:
            player.move_to(travel_pos)
            result["move_to_travel"] = True
            result["travel_pos"] = travel_pos

    return result


SKILL_HANDLERS["SK_TEDDY"] = handle_teddy


# ---------------------------------------------------------------------------
# SK_O_KY_DIEU handler
# ---------------------------------------------------------------------------


def handle_o_ky_dieu(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_O_KY_DIEU: ON_UPGRADE — chi trigger khi nang cap len L4 (nha cap 3).

    Effect: Player di chuyen 32 buoc tien (1 vong day du — Sweep Walk).
    - Di qua START → nhan thuong passing bonus binh thuong.
    - CamCo/PhaHuy trigger moi buoc (Sweep Walk per D-57).
    - Bep/stop_sign check moi buoc (D-55).
    - Tile effect tai o ket thuc (chinh o xuat phat) KHONG trigger lai.

    D-23: new_level == 4 <=> "Nha cap 3".
    T-02.5-08: Bounded loop exactly 32 iterations.

    ctx keys:
        tile: Tile dang duoc nang cap.
        board: Board instance.
        new_level: Cap moi sau khi nang cap.
    """
    new_level = ctx.get("new_level")

    # Chi trigger khi nang dung len L4 (D-23)
    if new_level != 4:
        return None

    return {"type": "sweep_walk", "steps": 32}


SKILL_HANDLERS["SK_O_KY_DIEU"] = handle_o_ky_dieu


# ---------------------------------------------------------------------------
# SK_MONG_NGUA handler
# ---------------------------------------------------------------------------


def handle_mong_ngua(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_MONG_NGUA: ON_UPGRADE — chi trigger khi xay Bieu Tuong (L5).

    Effect: Lay Resort tile cung canh ban co voi o vua xay L5.
    - Resort chua co chu -> lay mien phi.
    - Resort cua doi thu -> cuop (chi doi owner_id per D-28).
    - Resort cua chinh player -> khong co tac dung.
    - Khong tim thay Resort tren canh do -> fail silently.

    D-24: new_level == 5 <=> "Bieu Tuong".
    D-28: Resort chi co 1 cap, khi cuop chi doi owner_id.

    ctx keys:
        tile: Tile dang duoc nang cap.
        board: Board instance.
        players: Danh sach tat ca Player.
        new_level: Cap moi sau khi nang cap.
    """
    new_level = ctx.get("new_level")

    # Chi trigger khi nang dung len L5 (D-24)
    if new_level != 5:
        return None

    tile = ctx.get("tile")
    board = ctx.get("board")
    players = ctx.get("players", [])

    if tile is None or board is None:
        return None

    resort = _find_resort_on_side(board, tile.position)
    if resort is None:
        return None  # Khong co Resort tren canh nay, fail silently

    if resort.owner_id == player.player_id:
        return None  # Da so huu, khong co tac dung

    result: dict = {
        "type": "claim_resort",
        "resort_pos": resort.position,
        "stolen_from": None,
    }

    if resort.owner_id is None:
        # Lay mien phi
        resort.owner_id = player.player_id
        player.add_property(resort.position)
    else:
        # Cuop tu doi thu — D-28: chi doi owner_id
        old_owner = _find_player(players, resort.owner_id)
        if old_owner is not None:
            old_owner.remove_property(resort.position)
            result["stolen_from"] = old_owner.player_id
        resort.owner_id = player.player_id
        player.add_property(resort.position)

    return result


SKILL_HANDLERS["SK_MONG_NGUA"] = handle_mong_ngua
