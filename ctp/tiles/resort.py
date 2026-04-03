"""ResortStrategy - resort property logic."""

from ctp.tiles.base import TileStrategy
from ctp.tiles._toll_modifiers import apply_toll_modifiers
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
    - Toll modifier checks: virus/double_toll/angel/discount (Phase 02.1)
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
            # Tile is owned - tăng visit_count cho bất kỳ ai nhảy vào (kể cả chủ)
            tile.visit_count += 1

            # Pay rent to owner (chỉ khi người khác nhảy vào)
            if tile.owner_id != player.player_id and not player.is_bankrupt:
                resort_config = board.get_resort_config()
                if resort_config is None:
                    return events

                # toll = int(tollCost * increaseRate^level) * BASE_UNIT
                toll_cost = resort_config.get("tollCost", 0)
                increase_rate = resort_config.get("increaseRate", 1)
                level = tile.building_level if tile.building_level > 0 else 1

                rent = int(toll_cost * (increase_rate ** level)) * BASE_UNIT

                # Multiplier: nếu chỉ có 1 resort với opt này → dùng visit_count
                # Nếu có nhiều resort cùng opt → dùng số resort owner sở hữu
                resort_positions = board.get_resort_group_positions(tile.opt)
                if len(resort_positions) == 1:
                    count = tile.visit_count
                else:
                    count = sum(
                        1 for pos in resort_positions
                        if board.get_tile(pos).owner_id == tile.owner_id
                    )
                if count >= 3:
                    rent *= 4
                elif count == 2:
                    rent *= 2

                if tile.is_golden:
                    rent *= 2

                # Toll modifier checks (Phase 02.1, per D-44)
                owner = next((p for p in (players or []) if p.player_id == tile.owner_id), None)
                rent, skip = apply_toll_modifiers(player, owner, rent, event_bus)
                if skip:
                    return events

                if player.cash >= rent:
                    # Đủ tiền: trả ngay
                    player.cash -= rent
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
                else:
                    # Không đủ tiền: ghi nợ, để bankruptcy handler thanh toán thực tế
                    player.cash -= rent
                    events.append(GameEvent(
                        event_type=EventType.RENT_OWED,
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

                # Festival bonus: ô đang có lễ hội → trả thêm theo festival_level (X2/X3/X4)
                if board.festival_tile_position == tile.position:
                    extra_multiplier = min(tile.festival_level, 3)
                    extra_rent = rent * extra_multiplier
                    if extra_rent > 0:
                        player.cash -= extra_rent
                        if players:
                            owner = next((p for p in players if p.player_id == tile.owner_id), None)
                            if owner:
                                owner.receive(extra_rent)
                        events.append(GameEvent(
                            event_type=EventType.FESTIVAL_FEE_PAID,
                            player_id=player.player_id,
                            data={"position": tile.position, "fee": extra_rent, "recipient": tile.owner_id,
                                  "festival_level": tile.festival_level}
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
