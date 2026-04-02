"""Bankruptcy resolution for CTP game."""

from ctp.core.models import Player
from ctp.core.board import Board, SpaceId
from ctp.core.events import EventBus, GameEvent, EventType


def resolve_bankruptcy(player: Player, board: Board, event_bus: EventBus) -> list[GameEvent]:
    """Attempt to resolve bankruptcy by selling properties.

    Properties are sold in order of cheapest first (to maximize
    the number of properties that can be saved). Each property
    sells for sell_rate * total_build_cost.

    Args:
        player: The player to check for bankruptcy.
        board: The game board (for accessing property configs).
        event_bus: Event bus for publishing game events.

    Returns:
        List of events for any property sales and bankruptcy determination.
    """
    events = []

    # Sell properties in order: cheapest first
    while player.cash < 0 and player.owned_properties:
        # Find cheapest property to sell
        prop_pos = min(
            player.owned_properties,
            key=lambda p: _total_build_cost(board, p)
        )
        tile = board.get_tile(prop_pos)
        sell_value = _total_build_cost(board, prop_pos) * 0.5  # sellRate = 0.5

        player.cash += sell_value
        player.owned_properties.remove(prop_pos)
        tile.owner_id = None
        tile.building_level = 0

        events.append(GameEvent(
            event_type=EventType.PROPERTY_SOLD,
            player_id=player.player_id,
            data={
                "position": prop_pos,
                "value": sell_value,
                "tile_type": tile.space_id.name
            }
        ))
        event_bus.publish(events[-1])

    # Check if still bankrupt
    if player.cash < 0:
        player.is_bankrupt = True
        events.append(GameEvent(
            event_type=EventType.PLAYER_BANKRUPT,
            player_id=player.player_id,
            data={
                "final_cash": player.cash,
                "reason": "insufficient_assets"
            }
        ))
        event_bus.publish(events[-1])

    return events


def _total_build_cost(board: Board, position: int) -> int:
    """Calculate total build cost for a property (for selling).

    Args:
        board: The game board.
        position: Tile position (1-32).

    Returns:
        Total build cost (sum of all building levels), or 0 if not applicable.
    """
    tile = board.get_tile(position)

    if tile.space_id == SpaceId.LAND:
        config = board.get_land_config(tile.opt)
        if config is None:
            return 0
        building = config.get("building", {})
        return sum(b.get("build", 0) for b in building.values())

    if tile.space_id == SpaceId.RESORT:
        resort_config = board.get_resort_config()
        if resort_config is None:
            return 0
        # For resort, use initCost as base
        return resort_config.get("initCost", 0)

    return 0  # Simplified for other types