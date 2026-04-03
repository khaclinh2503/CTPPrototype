"""StartStrategy - start tile with fixed passing bonus and upgrade action."""

import random
from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import STARTING_CASH, BASE_UNIT


class StartStrategy(TileStrategy):
    """Strategy for Start tile (spaceId=7).

    - On land: No effect
    - On pass: Gives fixed bonus = passingBonusRate * STARTING_CASH (not % of current cash)
    """

    # Default passing bonus rate
    DEFAULT_PASSING_BONUS_RATE = 0.15

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on the start tile.

        Player được chọn 1 ô CITY đang sở hữu chưa max (< L5) để nâng cấp lên 1 level.
        Stub AI: chọn ngẫu nhiên, nâng cấp nếu đủ tiền.

        Returns:
            List of events (PROPERTY_UPGRADED nếu nâng cấp thành công).
        """
        # Tìm các ô CITY của player chưa đạt max level
        eligible = [
            board.get_tile(pos)
            for pos in player.owned_properties
            if board.get_tile(pos).space_id == SpaceId.CITY
            and board.get_tile(pos).building_level < 5
        ]
        if not eligible:
            return []

        # Stub AI: chọn ngẫu nhiên
        chosen = random.choice(eligible)
        next_level = chosen.building_level + 1
        land_cfg = board.get_land_config(chosen.opt)
        if not land_cfg:
            return []

        upgrade_cost = land_cfg.get("building", {}).get(str(next_level), {}).get("build", 0) * BASE_UNIT
        if not player.can_afford(upgrade_cost):
            return []

        player.cash -= upgrade_cost
        chosen.building_level = next_level

        event = GameEvent(
            event_type=EventType.PROPERTY_UPGRADED,
            player_id=player.player_id,
            data={
                "position": chosen.position,
                "new_level": next_level,
                "cost": upgrade_cost,
                "reason": "start_tile",
            }
        )
        event_bus.publish(event)
        return [event]

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing the start tile.

        Gives fixed passing bonus = DEFAULT_PASSING_BONUS_RATE * STARTING_CASH.
        Bonus is always 150,000 regardless of player's current cash.

        Args:
            player: The player who passed.
            tile: The start tile.
            board: The game board.
            event_bus: Event bus for publishing events.
            players: All players (unused, for interface consistency).

        Returns:
            List of events from passing Start.
        """
        events = []

        # Fixed bonus based on STARTING_CASH, not player's current cash
        bonus_rate = self.DEFAULT_PASSING_BONUS_RATE
        bonus = int(STARTING_CASH * bonus_rate)  # Always 150,000

        player.cash += bonus

        events.append(GameEvent(
            event_type=EventType.BONUS_RECEIVED,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "amount": bonus,
                "rate": bonus_rate,
                "reason": "passing_start"
            }
        ))
        event_bus.publish(events[-1])

        return events
