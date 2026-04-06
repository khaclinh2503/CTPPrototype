"""Handlers cho ACQUIRE-trigger skills: SK_MC2, SK_TRUM_DU_LICH.

SK_MC2 (ON_ACQUIRE): claim random unowned CITY tile với level = acquired tile level.
SK_TRUM_DU_LICH E1 (ON_ACQUIRE): giống MC2, nhưng loại trừ tile MC2 đã claim (stack).
SK_TRUM_DU_LICH E2 (ON_LAND_RESORT): forced acquisition của Resort đối thủ.
"""

import random
from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _claim_random_unowned_city(
    player: Player,
    board: Board,
    building_level: int,
    exclude_positions: list[int] | None = None,
):
    """Claim random unowned CITY tile, set to given building_level.

    Used by SK_MC2 and SK_TRUM_DU_LICH E1.

    Args:
        player: Player claiming the tile.
        board: Game board.
        building_level: Building level to set on the claimed tile.
        exclude_positions: Tile positions to exclude from the pool (already claimed).

    Returns:
        The claimed Tile, or None if no unowned CITY is available.
    """
    exclude = exclude_positions or []
    unowned = [
        t for t in board.board
        if t.space_id == SpaceId.CITY
        and t.owner_id is None
        and t.position not in exclude
    ]
    if not unowned:
        return None
    chosen = random.choice(unowned)
    chosen.owner_id = player.player_id
    chosen.building_level = building_level
    player.add_property(chosen.position)
    return chosen


# ---------------------------------------------------------------------------
# SK_MC2 handler
# ---------------------------------------------------------------------------

def handle_mc2(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_MC2 ON_ACQUIRE: claim random unowned CITY với level của tile vừa mua.

    Rate config:
        A: base=21, chance=1
        S: base=26, chance=2

    ctx keys:
        tile: Tile just acquired.
        board: Game board.
        acquired_level: building_level of the acquired tile.
        excluded_positions: (out) list updated với vị trí MC2 đã claim (dùng cho stack).

    Returns:
        {"type": "city_claimed", "position": int, "level": int} hoặc None.
    """
    board = ctx.get("board")
    acquired_level = ctx.get("acquired_level", 1)

    claimed = _claim_random_unowned_city(player, board, acquired_level)
    if claimed is None:
        return None

    # Cập nhật excluded_positions trong ctx để TrumDuLich E1 loại trừ tile này (stack)
    excluded = ctx.setdefault("excluded_positions", [])
    excluded.append(claimed.position)

    return {"type": "city_claimed", "skill": "SK_MC2", "position": claimed.position, "level": claimed.building_level}


SKILL_HANDLERS["SK_MC2"] = handle_mc2


# ---------------------------------------------------------------------------
# SK_TRUM_DU_LICH handlers
# ---------------------------------------------------------------------------

def handle_trum_du_lich(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_TRUM_DU_LICH dispatcher — routes đến E1 (ON_ACQUIRE) hoặc E2 (ON_LAND_RESORT).

    Trigger E1 (ON_ACQUIRE):
        Claim random unowned CITY; khi stack với MC2, loại trừ tile MC2 đã claim.
        Rate config E1: A: base=21, chance=1; S: base=26, chance=1

    Trigger E2 (ON_LAND_RESORT):
        Forced acquisition của Resort đối thủ nếu player đủ tiền.
        Rate config E2: A: base=15, chance=5; S: base=30, chance=5

    Returns:
        Result dict từ E1/E2, hoặc None.
    """
    trigger = ctx.get("trigger", "ON_ACQUIRE")
    if trigger == "ON_LAND_RESORT":
        return _handle_trum_du_lich_e2(player, ctx, cfg, engine)
    return _handle_trum_du_lich_e1(player, ctx, cfg, engine)


def _handle_trum_du_lich_e1(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_TRUM_DU_LICH Effect 1 (ON_ACQUIRE): giống MC2, nhưng loại trừ MC2's claimed tile.

    Khi stack với SK_MC2:
        MC2 fires trước → thêm claimed.position vào ctx["excluded_positions"]
        TrumDuLich E1 fires sau → loại trừ các ô đó khỏi pool

    Returns:
        {"type": "city_claimed", "skill": "SK_TRUM_DU_LICH_E1", "position": int, "level": int} hoặc None.
    """
    board = ctx.get("board")
    acquired_level = ctx.get("acquired_level", 1)
    exclude = ctx.get("excluded_positions", [])

    claimed = _claim_random_unowned_city(player, board, acquired_level, exclude_positions=exclude)
    if claimed is None:
        return None

    return {
        "type": "city_claimed",
        "skill": "SK_TRUM_DU_LICH_E1",
        "position": claimed.position,
        "level": claimed.building_level,
    }


def _handle_trum_du_lich_e2(player: Player, ctx: dict, cfg, engine) -> dict | None:
    """SK_TRUM_DU_LICH Effect 2 (ON_LAND_RESORT): forced acquisition của Resort đối thủ.

    Flow:
        1. Toll Resort đã được trả trước khi handler này được gọi.
        2. Kiểm tra tile là Resort thuộc đối thủ.
        3. Tính acquisition price = initCost * BASE_UNIT (qua calc_invested_build_cost).
        4. Nếu player đủ tiền → trả về lệnh acquisition để game engine xử lý.
           (PT_CHONG_MUA_NHA có thể block ở giai đoạn engine xử lý lệnh này)
        5. Nếu không đủ tiền → fail silently.

    ctx keys:
        tile: Resort tile player vừa đứng.
        board: Game board.
        players: List of players.

    Returns:
        {"type": "resort_acquisition", "tile_pos": int, "price": int} hoặc None.
    """
    from ctp.core.constants import calc_invested_build_cost

    tile = ctx.get("tile")
    board = ctx.get("board")

    if tile is None or board is None:
        return None

    # Kiểm tra là Resort thuộc đối thủ
    if tile.space_id != SpaceId.RESORT:
        return None
    if tile.owner_id is None or tile.owner_id == player.player_id:
        return None

    # Tính acquisition price (dùng chung logic với CITY acquisition)
    acq_price = calc_invested_build_cost(board, tile.position)
    if acq_price <= 0:
        # Fallback: nếu resort chưa được cấu hình invest cost → fail silently
        return None

    if not player.can_afford(acq_price):
        return None

    return {
        "type": "resort_acquisition",
        "skill": "SK_TRUM_DU_LICH_E2",
        "tile_pos": tile.position,
        "price": acq_price,
    }


SKILL_HANDLERS["SK_TRUM_DU_LICH"] = handle_trum_du_lich
