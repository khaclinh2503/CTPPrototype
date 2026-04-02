"""ResortStrategy - resort property logic."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import BASE_UNIT, STARTING_CASH


class ResortStrategy(TileStrategy):
    """Strategy for Resort property tiles (spaceId=6).

    Resort tiles:
    - maxUpgrade = 3 (vs 5 for city)
    - toll = tollCost * (increaseRate ^ level) * BASE_UNIT
    - Prices scaled by BASE_UNIT
    - Rent transfers to owner
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a resort tile.

        Args:
            player: The player who landed.
            tile: The resort tile.
            board: The game board.
            event_bus: Event bus for publishing events.
            players: All players (for rent transfer to owner).

        Returns:
            List of events from this tile resolution.
        """
        events = []

        if tile.owner_id is None:
            # Auto-buy unowned resort
            resort_config = board.get_resort_config()
            if resort_config is None:
                return events

            # Price = initCost * BASE_UNIT
            price = resort_config.get("initCost", 0) * BASE_UNIT

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
                        "property": "Resort",
                        "price": price,
                    }
                ))
                event_bus.publish(events[-1])

        else:
            # Tile is owned - pay rent to owner
            if tile.owner_id != player.player_id and not player.is_bankrupt:
                resort_config = board.get_resort_config()
                if resort_config is None:
                    return events

                # toll = int(tollCost * increaseRate^level) * BASE_UNIT
                toll_cost = resort_config.get("tollCost", 0)
                increase_rate = resort_config.get("increaseRate", 1)
                level = tile.building_level if tile.building_level > 0 else 1

                rent = int(toll_cost * (increase_rate ** level)) * BASE_UNIT

                if tile.is_golden:
                    rent *= 2

                # Deduct from payer (even if negative)
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
                        "level": tile.building_level,
                        "is_golden": tile.is_golden,
                    }
                ))
                event_bus.publish(events[-1])

        # Phí lễ hội: nếu ô này đang tổ chức lễ hội → trả phí cho hệ thống
        if board.festival_tile_position == tile.position and not player.is_bankrupt:
            festival_config = board.get_festival_config() or {}
            hold_cost_rate = festival_config.get("holdCostRate", 0.02)
            festival_fee = int(hold_cost_rate * STARTING_CASH)
            player.cash -= festival_fee
            events.append(GameEvent(
                event_type=EventType.FESTIVAL_FEE_PAID,
                player_id=player.player_id,
                data={"position": tile.position, "fee": festival_fee}
            ))
            event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a resort tile.

        Resort tiles have no pass-through effect.

        Returns:
            Empty list (no events).
        """
        return []
