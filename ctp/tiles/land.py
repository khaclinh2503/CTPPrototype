"""LandStrategy - property purchase and rent logic for City (CITY) tiles."""

from ctp.tiles.base import TileStrategy
from ctp.tiles._toll_modifiers import apply_toll_modifiers
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import BASE_UNIT, STARTING_CASH, calc_invested_build_cost


class LandStrategy(TileStrategy):
    """Strategy for CITY property tiles (spaceId=3).

    Handles:
    - Rent payment when landing on opponent-owned land
    - Rent transfer to owner
    - BASE_UNIT scaled prices
    - Toll modifier checks: virus/double_toll/angel/discount (Phase 02.1)

    Mua đất: quyết định mua/không mua được xử lý bởi GameController
    (buy_decision_fn), không auto-mua tại đây.
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
            # Đất trống: quyết định mua do GameController xử lý, không làm gì ở đây
            pass

        elif tile.owner_id == player.player_id:
            # Chủ đất tự ghé: clear virus nếu có (RISK-03)
            if owner := next((p for p in (players or []) if p.player_id == tile.owner_id), None):
                if owner.virus_turns > 0:
                    owner.virus_turns = 0

        elif not player.is_bankrupt:
            # Đất người khác: thu tiền thuê
            land_config = board.get_land_config(tile.opt)
            if land_config is None:
                return events

            building = land_config.get("building", {})
            # Rent = sum(toll[1..level]) × BASE_UNIT (cộng dồn tất cả cấp đã xây)
            rent = sum(
                building.get(str(lvl), {}).get("toll", 0)
                for lvl in range(1, tile.building_level + 1)
            ) * BASE_UNIT

            # Multiplier cộng dồn: base=1, mỗi effect +1
            multiplier = 1
            if tile.is_golden:
                multiplier += 1
            color_positions = board.get_color_group_positions(tile.opt)
            if color_positions and all(
                board.get_tile(pos).owner_id == tile.owner_id
                for pos in color_positions
            ):
                multiplier += 1
            rent *= multiplier

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
                extra_multiplier = min(tile.festival_level, 3)  # level1→+1x, level2→+2x, level3+→+3x
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
        """Handle player passing a city tile (no effect)."""
        return []
