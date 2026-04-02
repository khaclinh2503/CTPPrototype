"""Upgrade logic: player nâng cấp đất sau mỗi turn."""

from ctp.core.models import Player
from ctp.core.board import Board, SpaceId
from ctp.core.constants import BASE_UNIT
from ctp.core.events import EventBus, GameEvent, EventType


def resolve_upgrades(
    player: Player,
    board: Board,
    event_bus: EventBus,
    eligible_positions: dict[int, int] | None = None,
) -> list[GameEvent]:
    """Upgrade properties của player theo rule eligible_positions.

    Rules:
    - Khi trigger, player có thể xây từ cấp hiện tại lên đến max_level
      (tất cả các cấp liên tiếp, không giới hạn số cấp hay số ô).
    - max_level do FSM quyết định:
        - Thông thường: 4 (tối đa L3)
        - Khi ô đang ở L3: 5 (cho phép lên Landmark)

    Args:
        player: Player để upgrade properties.
        board: Game board.
        event_bus: Event bus để publish events.
        eligible_positions: Dict {tile_position: max_level} do FSM quyết định.
            Nếu None thì upgrade tất cả (backward compat cho tests cũ).

    Returns:
        List of GameEvents (PROPERTY_UPGRADED cho mỗi lần upgrade thành công).
    """
    events = []

    positions = (
        list(eligible_positions.keys())
        if eligible_positions is not None
        else list(player.owned_properties)
    )

    for pos in positions:
        tile = board.get_tile(pos)

        if tile.space_id != SpaceId.CITY:
            continue

        if eligible_positions is not None:
            if pos not in eligible_positions:
                continue
            max_level = eligible_positions[pos]
        else:
            max_level = 5  # backward compat

        land_config = board.get_land_config(tile.opt)
        if not land_config:
            continue

        building = land_config.get("building", {})

        while tile.building_level < max_level:
            next_level = tile.building_level + 1
            level_data = building.get(str(next_level), {})
            upgrade_cost = level_data.get("build", 0) * BASE_UNIT

            if not player.can_afford(upgrade_cost):
                break

            player.cash -= upgrade_cost
            tile.building_level = next_level

            event = GameEvent(
                event_type=EventType.PROPERTY_UPGRADED,
                player_id=player.player_id,
                data={
                    "position": pos,
                    "new_level": next_level,
                    "cost": upgrade_cost,
                }
            )
            events.append(event)
            event_bus.publish(event)

    return events
