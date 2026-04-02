"""FestivalStrategy - player chọn ô để tổ chức lễ hội."""

import random
from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import STARTING_CASH


class FestivalStrategy(TileStrategy):
    """Strategy for Festival tile (spaceId=1).

    Khi player dừng ở ô lễ hội:
    - Chọn 1 ô CITY hoặc RESORT trên map để tổ chức lễ hội
    - Ô được chọn trở thành "festival tile" — chỉ có 1 ô festival trên map
    - Các player đứng vào ô festival trả phí = holdCostRate × STARTING_CASH cho hệ thống

    Config (Board.json FestivalSpace):
        holdCostRate: 0.02  — tỷ lệ phí lễ hội (phí = rate × STARTING_CASH)
        maxFestival: 1      — chỉ 1 ô festival trên map tại 1 thời điểm
    """

    DEFAULT_HOLD_COST_RATE = 0.02

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Player chọn 1 ô CITY/RESORT để đặt lễ hội.

        Stub AI: chọn ngẫu nhiên trong các ô CITY/RESORT trên board.

        Args:
            player: Player vừa dừng ở ô lễ hội.
            tile: Festival tile.
            board: Game board.
            event_bus: Event bus.
            players: All players (unused).

        Returns:
            List với 1 FESTIVAL_UPDATED event.
        """
        events = []

        festival_config = board.get_festival_config() or {}
        hold_cost_rate = festival_config.get("holdCostRate", self.DEFAULT_HOLD_COST_RATE)

        # Tìm tất cả ô CITY và RESORT
        candidates = [
            t for t in board.board
            if t.space_id in (SpaceId.CITY, SpaceId.RESORT)
        ]
        if not candidates:
            return events

        # Stub AI: chọn ngẫu nhiên
        chosen = random.choice(candidates)

        # Xóa festival cũ (maxFestival = 1)
        board.festival_tile_position = chosen.position

        events.append(GameEvent(
            event_type=EventType.FESTIVAL_UPDATED,
            player_id=player.player_id,
            data={
                "festival_position": chosen.position,
                "hold_cost_rate": hold_cost_rate,
                "fee": int(hold_cost_rate * STARTING_CASH),
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        return []
