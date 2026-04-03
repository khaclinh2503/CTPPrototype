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
        """Player chọn 1 ô CITY/RESORT để đặt lễ hội (nếu đủ tiền).

        - Phải đủ tiền (>= holdCostRate × STARTING_CASH) mới được chọn.
        - Trừ phí tổ chức vào hệ thống.
        - Xóa festival cũ, đặt festival mới tại ô được chọn.

        Stub AI: chọn ngẫu nhiên trong các ô CITY/RESORT trên board.
        """
        events = []

        festival_config = board.get_festival_config() or {}
        hold_cost_rate = festival_config.get("holdCostRate", self.DEFAULT_HOLD_COST_RATE)
        organize_cost = int(hold_cost_rate * STARTING_CASH)

        # Tìm các ô CITY và RESORT của chính player
        candidates = [
            t for t in board.board
            if t.space_id in (SpaceId.CITY, SpaceId.RESORT)
            and t.owner_id == player.player_id
        ]
        if not candidates:
            return events

        # Chỉ tổ chức nếu đủ tiền
        if player.cash < organize_cost:
            return events

        # Trừ phí tổ chức (vào hệ thống)
        player.cash -= organize_cost

        # Stub AI: chọn ngẫu nhiên
        chosen = random.choice(candidates)

        # Tăng festival_level cho ô được chọn, đặt festival mới (maxFestival = 1)
        chosen.festival_level += 1
        board.festival_tile_position = chosen.position

        festival_fee = int(hold_cost_rate * STARTING_CASH)
        events.append(GameEvent(
            event_type=EventType.FESTIVAL_UPDATED,
            player_id=player.player_id,
            data={
                "festival_position": chosen.position,
                "organize_cost": organize_cost,
                "hold_cost_rate": hold_cost_rate,
                "fee": festival_fee,
            }
        ))
        event_bus.publish(events[-1])

        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        return []
