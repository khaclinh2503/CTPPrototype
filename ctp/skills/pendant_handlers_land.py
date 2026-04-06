"""Pendant handlers for land/travel triggers.

Pendants implemented:
- PT_GIAY_BAY: ON_LAND_OPPONENT_WITH_TOLL — waive toll + teleport to Travel tile (D-51)
- PT_CUOP_NHA: ON_LAND_OPPONENT — steal property after toll resolved
- PT_MANG_NHEN: ON_LAND_OPPONENT — dual-rate: R1 free toll, R2 steal property (independent)
- PT_SIEU_TAXI: ON_LAND_TRAVEL (R1) + ON_LAND_OPPONENT (R2 free toll, D-52)

D-45 toll resolution order: free-toll pendants (GiayBay, MangNhen R1, SieuTaxi R2) check
before boost pendants.
GiayBay -> SieuTaxi R2 priority chain: if GiayBay active, SieuTaxi R2 skipped.
"""

import random

from ctp.skills.registry import PENDANT_HANDLERS
from ctp.core.board import SpaceId


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_player(players: list, player_id: str):
    """Tìm player theo player_id trong danh sách players."""
    for p in players:
        if p.player_id == player_id:
            return p
    return None


def _get_travel_tiles(board) -> list[int]:
    """Lấy danh sách position của tất cả TRAVEL tiles trên bàn cờ."""
    return [
        tile.position
        for tile in board.board
        if tile.space_id == SpaceId.TRAVEL
    ]


def _steal_property(player, tile, players: list) -> dict:
    """Thực hiện cướp property: đổi owner_id, cập nhật owned_properties của cả 2 player.

    Building level được giữ nguyên (CITY).
    Resort: chỉ đổi owner_id (D-28).

    Args:
        player: Player cướp property.
        tile: Tile bị cướp.
        players: Danh sách tất cả player trong game.

    Returns:
        Dict result {"type": "property_stolen", "position": tile.position}.
    """
    old_owner = _find_player(players, tile.owner_id)
    if old_owner is not None:
        old_owner.remove_property(tile.position)
    tile.owner_id = player.player_id
    player.add_property(tile.position)
    return {"type": "property_stolen", "position": tile.position}


# ---------------------------------------------------------------------------
# PT_GIAY_BAY handler
# ---------------------------------------------------------------------------

def handle_giay_bay(player, ctx: dict, cfg, engine) -> dict | None:
    """PT_GIAY_BAY: ON_LAND_OPPONENT_WITH_TOLL — miễn phí toll + teleport tới Travel tile.

    D-51: Chỉ kích hoạt khi là lượt của player (is_player_turn=True).
    Rank rates: B:1, A:3, S:5, R:10, SR:15.
    Effect: waive toll + teleport to chosen Travel tile (Travel Walk — susceptible to traps).
    D-45: GiayBay là free-toll pendant, check trước boost pendants.
    Priority: GiayBay check trước SieuTaxi R2 — nếu active thì SieuTaxi R2 bị skip.

    Args:
        player: Player đang landing.
        ctx: Context với board, players, is_player_turn, toll, travel_tiles.
        cfg: PendantEntry config cho PT_GIAY_BAY.
        engine: SkillEngine instance.

    Returns:
        {"type": "toll_waive_and_travel", "travel_pos": chosen_pos} nếu active.
        None nếu không active hoặc không phải lượt player.
    """
    # D-51: chỉ fire khi là lượt của player
    if not ctx.get("is_player_turn", False):
        return None

    board = ctx.get("board")
    if board is None:
        return None

    travel_tiles = _get_travel_tiles(board)
    # Nếu không có Travel tile: chỉ miễn toll, không di chuyển
    if not travel_tiles:
        rate = getattr(cfg.rank_rates, player.pendant_rank, 0)
        if random.randint(0, 99) < rate:
            ctx["giay_bay_active"] = True
            return {"type": "toll_waive"}
        return None

    rate = getattr(cfg.rank_rates, player.pendant_rank, 0)
    if random.randint(0, 99) < rate:
        # Stub AI: chọn Travel tile đầu tiên (strategic choice nằm ngoài scope)
        chosen_pos = travel_tiles[0]
        ctx["giay_bay_active"] = True
        return {"type": "toll_waive_and_travel", "travel_pos": chosen_pos}

    return None


PENDANT_HANDLERS["PT_GIAY_BAY"] = handle_giay_bay


# ---------------------------------------------------------------------------
# PT_CUOP_NHA handler
# ---------------------------------------------------------------------------

def handle_cuop_nha(player, ctx: dict, cfg, engine) -> dict | None:
    """PT_CUOP_NHA: ON_LAND_OPPONENT — cướp property sau khi toll đã được giải quyết.

    D-51: Chỉ kích hoạt khi là lượt của player (is_player_turn=True).
    Rank rates: B:5, A:7, S:10, R:15, SR:25.
    Effect fires AFTER toll resolved (kể cả toll=0 từ BuaSet/GiayBay).
    NOT blocked by PT_CHONG_MUA_NHA (cướp nhà != mua lại).
    Building level giữ nguyên cho CITY; Resort chỉ đổi owner_id (D-28).

    Args:
        player: Player đang landing.
        ctx: Context với board, players, is_player_turn, tile.
        cfg: PendantEntry config cho PT_CUOP_NHA.
        engine: SkillEngine instance.

    Returns:
        {"type": "property_stolen", "position": pos} nếu active.
        None nếu không active.
    """
    # D-51: chỉ fire khi là lượt của player
    if not ctx.get("is_player_turn", False):
        return None

    tile = ctx.get("tile")
    players = ctx.get("players", [])

    if tile is None or tile.owner_id is None or tile.owner_id == player.player_id:
        return None

    rate = getattr(cfg.rank_rates, player.pendant_rank, 0)
    if random.randint(0, 99) < rate:
        return _steal_property(player, tile, players)

    return None


PENDANT_HANDLERS["PT_CUOP_NHA"] = handle_cuop_nha


# ---------------------------------------------------------------------------
# PT_MANG_NHEN handler
# ---------------------------------------------------------------------------

def handle_mang_nhen(player, ctx: dict, cfg, engine) -> dict | None:
    """PT_MANG_NHEN: ON_LAND_OPPONENT — 2 independent rate checks.

    D-51: Chỉ kích hoạt khi là lượt của player (is_player_turn=True).
    R1 (free toll): Rank rates B:3, A:5, S:8, R:20, SR:30 — check trước.
    R2 (steal property, AFTER toll): Rank rates B:5, A:7, S:10, R:15, SR:25 — check sau, độc lập.
    Cả hai rate check độc lập — có thể cùng active trong 1 event.

    Args:
        player: Player đang landing.
        ctx: Context với board, players, is_player_turn, tile.
        cfg: PendantEntry config cho PT_MANG_NHEN (với rank_rates_2).
        engine: SkillEngine instance.

    Returns:
        Dict kết quả với R1/R2 outcomes, hoặc None nếu không có effect nào.
    """
    # D-51: chỉ fire khi là lượt của player
    if not ctx.get("is_player_turn", False):
        return None

    tile = ctx.get("tile")
    players = ctx.get("players", [])

    results = {}

    # R1: free toll check (độc lập)
    rate1 = getattr(cfg.rank_rates, player.pendant_rank, 0)
    r1_active = random.randint(0, 99) < rate1
    if r1_active:
        results["toll_waived"] = True

    # R2: steal property check (độc lập, sau toll)
    r2_active = False
    if cfg.rank_rates_2 is not None and tile is not None and tile.owner_id is not None and tile.owner_id != player.player_id:
        rate2 = getattr(cfg.rank_rates_2, player.pendant_rank, 0)
        r2_active = random.randint(0, 99) < rate2
        if r2_active:
            steal_result = _steal_property(player, tile, players)
            results["property_stolen"] = steal_result["position"]

    if not results:
        return None

    result = {"type": "mang_nhen_result"}
    result.update(results)
    return result


PENDANT_HANDLERS["PT_MANG_NHEN"] = handle_mang_nhen


# ---------------------------------------------------------------------------
# PT_SIEU_TAXI handler
# ---------------------------------------------------------------------------

def handle_sieu_taxi(player, ctx: dict, cfg, engine) -> dict | None:
    """PT_SIEU_TAXI: 2 triggers với 2 rate độc lập.

    R1 (ON_LAND_TRAVEL): Rank rates B:30, A:40, S:50, R:66, SR:76
    - Khi landing tại Travel tile: chọn bất kỳ tile nào để di chuyển ngay.

    R2 (ON_LAND_OPPONENT): Rank rates B:3, A:5, S:8, R:20, SR:35
    - D-52: Fires trong BẤT KỲ lượt nào (kể cả khi bị kéo bởi skill đối thủ).
    - Free toll.
    - Priority: chỉ check nếu PT_GIAY_BAY chưa active trong event này.

    Args:
        player: Player đang landing.
        ctx: Context với board, players, is_player_turn, trigger, tile.
        cfg: PendantEntry config cho PT_SIEU_TAXI (với rank_rates_2).
        engine: SkillEngine instance.

    Returns:
        {"type": "instant_travel", "destination": pos} cho R1.
        {"type": "toll_waive"} cho R2.
        None nếu không active.
    """
    trigger = ctx.get("trigger", "ON_LAND_TRAVEL")
    board = ctx.get("board")

    # R1: ON_LAND_TRAVEL
    if trigger == "ON_LAND_TRAVEL":
        rate1 = getattr(cfg.rank_rates, player.pendant_rank, 0)
        if random.randint(0, 99) < rate1:
            # Stub AI: chọn tile đầu tiên trên board (strategic destination nằm ngoài scope)
            chosen_pos = 1
            if board is not None:
                # Chọn vị trí bất kỳ (không phải TRAVEL tile nơi đang đứng)
                for t in board.board:
                    if t.position != player.position:
                        chosen_pos = t.position
                        break
            return {"type": "instant_travel", "destination": chosen_pos}

    # R2: ON_LAND_OPPONENT — D-52: fires bất kể is_player_turn
    elif trigger == "ON_LAND_OPPONENT":
        # Priority: chỉ check nếu GiayBay chưa active
        if ctx.get("giay_bay_active"):
            return None

        if cfg.rank_rates_2 is not None:
            rate2 = getattr(cfg.rank_rates_2, player.pendant_rank, 0)
            if random.randint(0, 99) < rate2:
                return {"type": "toll_waive"}

    return None


PENDANT_HANDLERS["PT_SIEU_TAXI"] = handle_sieu_taxi
