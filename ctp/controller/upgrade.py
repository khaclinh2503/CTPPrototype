"""Upgrade logic: player nâng cấp đất sau mỗi turn."""

from ctp.core.models import Player
from ctp.core.board import Board, SpaceId
from ctp.core.constants import BASE_UNIT
from ctp.core.events import EventBus, GameEvent, EventType


def resolve_upgrades(
    player: Player,
    board: Board,
    event_bus: EventBus,
) -> list[GameEvent]:
    """Upgrade tất cả properties của player nếu đủ tiền.

    Stub (per D-15): luôn upgrade nếu đủ tiền và chưa max.
    Thứ tự: upgrade theo thứ tự trong owned_properties.
    Max level CITY = 5.

    Args:
        player: Player để upgrade properties.
        board: Game board.
        event_bus: Event bus để publish events.

    Returns:
        List of GameEvents (PROPERTY_UPGRADED cho mỗi lần upgrade thành công).
    """
    events = []

    for pos in list(player.owned_properties):  # copy list vì có thể thay đổi
        tile = board.get_tile(pos)

        if tile.space_id != SpaceId.CITY:
            continue

        if tile.building_level >= 5:
            continue

        land_config = board.get_land_config(tile.opt)
        if not land_config:
            continue

        next_level = tile.building_level + 1
        building = land_config.get("building", {})
        level_data = building.get(str(next_level), {})
        upgrade_cost = level_data.get("build", 0) * BASE_UNIT

        if player.can_afford(upgrade_cost):
            player.cash -= upgrade_cost
            tile.building_level = next_level

            events.append(GameEvent(
                event_type=EventType.PROPERTY_UPGRADED,
                player_id=player.player_id,
                data={
                    "position": pos,
                    "new_level": next_level,
                    "cost": upgrade_cost,
                }
            ))
            event_bus.publish(events[-1])

    return events
