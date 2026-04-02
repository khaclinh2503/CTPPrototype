"""TravelStrategy - đặt pending_travel flag, xử lý thực tế ở FSM lượt sau."""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType


class TravelStrategy(TileStrategy):
    """Strategy for Travel tiles (spaceId=9).

    Khi player dừng ở ô Travel:
    - Set pending_travel = True, kết thúc lượt ngay.
    - Đầu lượt SAU: FSM chọn ngẫu nhiên 1 CITY/RESORT làm đích,
      hỏi player có muốn đi không (stub AI: đi nếu đủ tiền).
    - Phí = travelCostRate × STARTING_CASH = 20,000.
    - Chấp nhận: trả phí + teleport + kết thúc lượt.
    - Từ chối hoặc không đủ tiền: kết thúc lượt (không di chuyển).
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Đặt pending_travel = True. Teleport thực tế ở _do_roll lượt sau."""
        player.pending_travel = True

        event = GameEvent(
            event_type=EventType.TILE_LANDED,
            player_id=player.player_id,
            data={"position": tile.position, "tile_type": "TRAVEL", "pending": True}
        )
        event_bus.publish(event)
        return [event]

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        return []
