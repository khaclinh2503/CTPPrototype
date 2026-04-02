"""ResortStrategy - resort property logic."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class ResortStrategy(TileStrategy):
    """Strategy for Resort property tiles.

    Resort tiles work similarly to land but use different math:
    - maxUpgrade = 3 (vs 5 for land)
    - toll = tollCost * (increaseRate ^ level)
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player landing on a resort tile.

        Args:
            player: The player who landed.
            tile: The resort tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Check if tile is unowned
        if tile.owner_id is None:
            # Auto-buy unowned resort (Phase 1 - no AI decision)
            resort_config = board.get_resort_config()
            if resort_config is None:
                return events

            price = resort_config.get("initCost", 0)

            if player.cash >= price:
                # Purchase the resort
                player.cash -= price
                player.add_property(tile.position)
                tile.owner_id = player.player_id
                tile.building_level = 1

                events.append(GameEvent(
                    event_type=EventType.PROPERTY_PURCHASED,
                    player_id=player.player_id,
                    data={
                        "position": tile.position,
                        "property": "Resort",
                        "price": price,
                        "level": 1
                    }
                ))
                event_bus.publish(events[-1])
        else:
            # Tile is owned - pay rent
            if tile.owner_id != player.player_id and not player.is_bankrupt:
                resort_config = board.get_resort_config()
                if resort_config is None:
                    return events

                # Calculate toll: tollCost * (increaseRate ^ level)
                toll_cost = resort_config.get("tollCost", 0)
                increase_rate = resort_config.get("increaseRate", 1)
                level = tile.building_level if tile.building_level > 0 else 1

                rent = int(toll_cost * (increase_rate ** level))

                if player.cash >= rent:
                    player.cash -= rent

                    events.append(GameEvent(
                        event_type=EventType.RENT_PAID,
                        player_id=player.player_id,
                        data={
                            "position": tile.position,
                            "amount": rent,
                            "recipient": tile.owner_id,
                            "level": tile.building_level
                        }
                    ))
                    event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player passing a resort tile.

        Resort tiles have no pass-through effect.

        Returns:
            Empty list (no events).
        """
        return []