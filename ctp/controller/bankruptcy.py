"""Bankruptcy resolution for CTP game."""

from ctp.core.models import Player
from ctp.core.board import Board, SpaceId
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.constants import calc_invested_build_cost


def resolve_bankruptcy(player: Player, board: Board, event_bus: EventBus,
                       creditor: Player | None = None) -> list[GameEvent]:
    """Attempt to resolve bankruptcy by selling properties.

    Hai chế độ:
    - Có creditor (phá sản do trả thuê): bán TẤT CẢ property, chuyển toàn bộ
      tiền còn lại (cash hiện tại + tiền bán nhà) cho chủ đất, player bị loại.
    - Không có creditor (phá sản do thuế/nguyên nhân khác): bán rẻ nhất trước
      cho đến khi đủ tiền hoặc hết đất; bankrupt nếu vẫn không đủ.

    Args:
        player: The player to check for bankruptcy.
        board: The game board (for accessing property configs).
        event_bus: Event bus for publishing game events.
        creditor: Player nhận toàn bộ tài sản còn lại (chủ đất gây phá sản).

    Returns:
        List of events for any property sales and bankruptcy determination.
    """
    events = []

    if creditor is not None:
        # --- Phá sản do trả thuê: bán rẻ nhất trước cho đến khi đủ tiền ---
        while player.cash < 0 and player.owned_properties:
            prop_pos = min(
                player.owned_properties,
                key=lambda p: calc_invested_build_cost(board, p)
            )
            tile = board.get_tile(prop_pos)
            invested_cost = calc_invested_build_cost(board, prop_pos)
            sell_value = int(invested_cost * 0.5)

            player.cash += sell_value
            player.owned_properties.remove(prop_pos)
            tile.owner_id = None
            tile.building_level = 0
            tile.visit_count = 0

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

        # Nếu vẫn không đủ tiền sau khi bán hết → phá sản
        if player.cash < 0:
            player.is_bankrupt = True
            events.append(GameEvent(
                event_type=EventType.PLAYER_BANKRUPT,
                player_id=player.player_id,
                data={
                    "final_cash": player.cash,
                    "reason": "rent_unpayable",
                    "creditor": creditor.player_id,
                }
            ))
            event_bus.publish(events[-1])

    else:
        # --- Phá sản do thuế/nguyên nhân khác: bán rẻ nhất trước ---
        while player.cash < 0 and player.owned_properties:
            prop_pos = min(
                player.owned_properties,
                key=lambda p: calc_invested_build_cost(board, p)
            )
            tile = board.get_tile(prop_pos)
            invested_cost = calc_invested_build_cost(board, prop_pos)
            sell_value = int(invested_cost * 0.5)

            player.cash += sell_value
            player.owned_properties.remove(prop_pos)
            tile.owner_id = None
            tile.building_level = 0
            tile.visit_count = 0

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
