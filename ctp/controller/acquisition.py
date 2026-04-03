"""Acquisition flow: player mua đất từ đối thủ (forced sale)."""

from ctp.core.models import Player
from ctp.core.board import Board, Tile, SpaceId
from ctp.core.constants import calc_invested_build_cost
from ctp.core.events import EventBus, GameEvent, EventType


def resolve_acquisition(
    player: Player,
    tile: Tile,
    board: Board,
    players: list[Player],
    event_bus: EventBus,
    acquire_rate: float = 1.0,
) -> list[GameEvent]:
    """Xử lý acquisition khi player đứng ô đất người khác.

    Flow:
    1. Chỉ apply cho CITY tiles có owner khác player
    2. Chỉ khi chưa Landmark (building_level < 5)
    3. Tính acquire_price = tổng build cost các cấp đã xây * acquire_rate
    4. Nếu player đủ tiền -> forced buy (B không có quyền từ chối)
    5. Transfer: A pay -> B receive, tile.owner_id = A, building_level giữ nguyên

    Stub AI: luôn mua nếu đủ tiền.

    Args:
        player: Player muốn mua đất (A).
        tile: Tile hiện tại player đứng.
        board: Game board.
        players: Danh sách tất cả players.
        event_bus: Event bus để publish events.
        acquire_rate: Hệ số mua (từ Board.json General.acquireRate, default 1.0).

    Returns:
        List of GameEvents (PROPERTY_ACQUIRED nếu mua thành công).
    """
    events = []

    # Chỉ CITY tiles
    if tile.space_id != SpaceId.CITY:
        return events

    # Chỉ đất người khác
    if tile.owner_id is None or tile.owner_id == player.player_id:
        return events

    # Chỉ khi chưa max level (Landmark = level 5)
    if tile.building_level >= 5:
        return events

    # Giá cướp = tổng build cost các cấp đã xây * acquireRate
    total_build_cost = calc_invested_build_cost(board, tile.position)
    acquire_price = int(total_build_cost * acquire_rate)

    if not player.can_afford(acquire_price):
        return events

    # Stub: luôn mua (per D-14)
    # Tìm owner
    owner = next((p for p in players if p.player_id == tile.owner_id), None)
    if not owner:
        return events

    # Transfer ownership
    player.cash -= acquire_price
    owner.receive(acquire_price)
    owner.remove_property(tile.position)
    player.add_property(tile.position)
    tile.owner_id = player.player_id

    events.append(GameEvent(
        event_type=EventType.PROPERTY_ACQUIRED,
        player_id=player.player_id,
        data={
            "position": tile.position,
            "from_player": owner.player_id,
            "price": acquire_price,
            "level": tile.building_level,
        }
    ))
    event_bus.publish(events[-1])
    return events
