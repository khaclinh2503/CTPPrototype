"""GodStrategy - Ô God (spaceId=10), chỉ xuất hiện trên Map 2.

Luật:
- Lượt đầu tiên của player (turns_taken == 0):
    Chọn 1 CITY chưa có chủ → mua + xây level 1 (phí bình thường).
- Từ lượt 2 trở đi:
    Chọn giữa "xây nhà" (nâng cấp 1 CITY đang sở hữu lên 1 level)
    hoặc "nâng ô" (đánh dấu 1 ô bất kì trên map, toàn map chỉ 1 ô nâng tại 1 lúc).

Khi player di chuyển gặp ô đang nâng:
    → Dừng tại ô đó, ô hạ xuống, resolve effect bình thường, huỷ đổ đôi.

Headless AI:
- Turn 1: mua CITY rẻ nhất có thể afford.
- Turn 2+: ưu tiên nâng ô nếu chưa có ô nâng; fallback nâng cấp đất nếu đủ tiền.
"""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent, EventType
from ctp.core.constants import BASE_UNIT


class GodStrategy(TileStrategy):
    """Strategy for God tile (spaceId=10). Map 2 only."""

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a God tile."""
        if player.turns_taken == 0:
            return self._do_buy(player, board, event_bus)
        else:
            # Prefer elevate; fallback to upgrade
            if self._can_elevate(board):
                return self._do_elevate(player, board, event_bus)
            return self._do_upgrade(player, board, event_bus)

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        return []

    # ------------------------------------------------------------------
    # Turn 1: buy unowned CITY
    # ------------------------------------------------------------------

    def _do_buy(self, player: Player, board: Board, event_bus) -> list[GameEvent]:
        """Mua 1 CITY chua co chu re nhat co the afford."""
        candidates = [
            t for t in board.board
            if t.space_id == SpaceId.CITY and t.owner_id is None
        ]
        if not candidates:
            return []

        def buy_price(t: Tile) -> int:
            cfg = board.get_land_config(t.opt)
            if not cfg:
                return 999_999_999
            return cfg.get("building", {}).get("1", {}).get("build", 0) * BASE_UNIT

        candidates.sort(key=buy_price)

        for t in candidates:
            price = buy_price(t)
            if not player.can_afford(price):
                continue

            player.cash -= price
            player.add_property(t.position)
            t.owner_id = player.player_id
            t.building_level = 1

            event = GameEvent(
                event_type=EventType.GOD_BUILD,
                player_id=player.player_id,
                data={
                    "action": "buy",
                    "position": t.position,
                    "price": price,
                    "new_level": 1,
                }
            )
            event_bus.publish(event)
            return [event]

        return []

    # ------------------------------------------------------------------
    # Turn 2+: upgrade owned CITY
    # ------------------------------------------------------------------

    def _do_upgrade(self, player: Player, board: Board, event_bus) -> list[GameEvent]:
        """Nang cap 1 CITY dang so huu len 1 level."""
        for pos in player.owned_properties:
            t = board.get_tile(pos)
            if t.space_id != SpaceId.CITY:
                continue
            if t.building_level >= 5:
                continue

            cfg = board.get_land_config(t.opt)
            if not cfg:
                continue

            next_level = t.building_level + 1
            cost = cfg.get("building", {}).get(str(next_level), {}).get("build", 0) * BASE_UNIT

            if not player.can_afford(cost):
                continue

            player.cash -= cost
            t.building_level = next_level

            event = GameEvent(
                event_type=EventType.GOD_BUILD,
                player_id=player.player_id,
                data={
                    "action": "upgrade",
                    "position": pos,
                    "price": cost,
                    "new_level": next_level,
                }
            )
            event_bus.publish(event)
            return [event]

        return []

    # ------------------------------------------------------------------
    # Turn 2+: elevate a tile
    # ------------------------------------------------------------------

    def _can_elevate(self, board: Board) -> bool:
        """Kiem tra toan map chua co o nang nao khong."""
        return board.elevated_tile is None

    def _do_elevate(self, player: Player, board: Board, event_bus) -> list[GameEvent]:
        """Nang 1 o bat ki tren map (AI: chon o dau tien khac vi tri hien tai)."""
        if board.elevated_tile is not None:
            return []
        for t in board.board:
            if t.position == player.position:
                continue
            board.elevated_tile = t.position
            event = GameEvent(
                event_type=EventType.TILE_ELEVATED,
                player_id=player.player_id,
                data={"position": t.position}
            )
            event_bus.publish(event)
            return [event]
        return []
