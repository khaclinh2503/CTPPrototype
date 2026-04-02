"""LandStrategy - property purchase and rent logic for City (CITY) tiles."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import BASE_UNIT, calc_invested_build_cost


class LandStrategy(TileStrategy):
    """Strategy for CITY property tiles (spaceId=3).

    Handles:
    - Property purchase (auto-buy in Phase 2 stub)
    - Rent payment when landing on opponent-owned land
    - Rent transfer to owner
    - BASE_UNIT scaled prices
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a city tile.

        Args:
            player: The player who landed.
            tile: The city tile.
            board: The game board.
            event_bus: Event bus for publishing events.
            players: All players (needed for rent transfer to owner).

        Returns:
            List of events from this tile resolution.
        """
        events = []

        if tile.owner_id is None:
            # Auto-buy unowned property
            land_config = board.get_land_config(tile.opt)
            if land_config is None:
                return events

            # Price = level 1 build cost * BASE_UNIT
            building = land_config.get("building", {})
            level_1 = building.get("1", {})
            price = level_1.get("build", 0) * BASE_UNIT

            if player.cash >= price:
                player.cash -= price
                player.add_property(tile.position)
                tile.owner_id = player.player_id
                tile.building_level = 1

                events.append(GameEvent(
                    event_type=EventType.PROPERTY_PURCHASED,
                    player_id=player.player_id,
                    data={
                        "position": tile.position,
                        "property": f"City_{tile.opt}",
                        "price": price,
                        "level": 1
                    }
                ))
                event_bus.publish(events[-1])

        else:
            # Tile is owned - pay rent to owner
            if tile.owner_id != player.player_id and not player.is_bankrupt:
                land_config = board.get_land_config(tile.opt)
                if land_config is None:
                    return events

                # Rent = toll_value * BASE_UNIT
                building = land_config.get("building", {})
                level_key = str(tile.building_level) if tile.building_level > 0 else "1"
                level_data = building.get(level_key, {})
                rent = level_data.get("toll", 0) * BASE_UNIT

                # Deduct from payer (even if negative - bankruptcy handler will resolve)
                player.cash -= rent

                # Transfer rent to owner
                if players:
                    owner = next((p for p in players if p.player_id == tile.owner_id), None)
                    if owner:
                        owner.receive(rent)

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

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a city tile.

        City tiles have no pass-through effect.

        Returns:
            Empty list (no events).
        """
        return []
