"""Bankruptcy resolution for CTP game."""

from ctp.core.models import Player
from ctp.core.board import Board, SpaceId
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.constants import calc_invested_build_cost


def resolve_bankruptcy(player: Player, board: Board, event_bus: EventBus) -> list[GameEvent]:
    """Attempt to resolve bankruptcy by selling properties.

    Properties are sold cheapest first (to maximize the number of
    properties that can be saved). Each property sells for
    sellRate (0.5) * calc_invested_build_cost (only invested levels).

    Args:
        player: The player to check for bankruptcy.
        board: The game board (for accessing property configs).
        event_bus: Event bus for publishing game events.

    Returns:
        List of events for any property sales and bankruptcy determination.
    """
    events = []

    # Sell properties cheapest first
    while player.cash < 0 and player.owned_properties:
        # Find cheapest property to sell (by invested cost)
        prop_pos = min(
            player.owned_properties,
            key=lambda p: calc_invested_build_cost(board, p)
        )
        tile = board.get_tile(prop_pos)

        # Sell value = 50% of invested build cost only (not all 5 levels)
        invested_cost = calc_invested_build_cost(board, prop_pos)
        sell_value = int(invested_cost * 0.5)  # sellRate = 0.5

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
