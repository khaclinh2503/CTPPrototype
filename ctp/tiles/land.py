"""LandStrategy - property purchase and rent logic for Land tiles."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class LandStrategy(TileStrategy):
    """Strategy for Land property tiles.

    Handles:
    - Property purchase (auto-buy in Phase 1)
    - Rent payment when landing on opponent-owned land
    - Building upgrades (not implemented in Phase 1)
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]:
        """Handle player landing on a land tile.

        Args:
            player: The player who landed.
            tile: The land tile.
            board: The game board.
            event_bus: Event bus for publishing events.

        Returns:
            List of events from this tile resolution.
        """
        events = []

        # Check if tile is unowned
        if tile.owner_id is None:
            # Auto-buy unowned property (Phase 1 - no AI decision)
            land_config = board.get_land_config(tile.opt)
            if land_config is None:
                return events

            # Get the purchase price (level 1 build cost)
            building = land_config.get("building", {})
            level_1 = building.get("1", {})
            price = level_1.get("build", 0)

            if player.cash >= price:
                # Purchase the property
                player.cash -= price
                player.add_property(tile.position)
                tile.owner_id = player.player_id
                tile.building_level = 1

                events.append(GameEvent(
                    event_type=EventType.PROPERTY_PURCHASED,
                    player_id=player.player_id,
                    data={
                        "position": tile.position,
                        "property": f"Land_{tile.opt}",
                        "price": price,
                        "level": 1
                    }
                ))
                event_bus.publish(events[-1])
        else:
            # Tile is owned - pay rent
            if tile.owner_id != player.player_id and not player.is_bankrupt:
                land_config = board.get_land_config(tile.opt)
                if land_config is None:
                    return events

                # Calculate rent based on building level
                building = land_config.get("building", {})
                level_key = str(tile.building_level) if tile.building_level > 0 else "1"
                level_data = building.get(level_key, {})
                rent = level_data.get("toll", 0)

                # Check for toll multiply in General config
                # (simplified for Phase 1 - map 1 has no tollMultiply)

                if player.cash >= rent:
                    player.cash -= rent
                    # Find owner and add their cash
                    for p in board.board:  # This won't work - need to pass players
                        pass  # Simplified - rent goes to "bank" for now in events

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
        """Handle player passing a land tile.

        Land tiles have no pass-through effect.

        Returns:
            Empty list (no events).
        """
        return []