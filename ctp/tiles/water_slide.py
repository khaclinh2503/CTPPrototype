"""WaterSlideStrategy - Ô Water Slide (spaceId=40), chỉ xuất hiện trên Map 3.

Luật:
- Khi player đáp vào ô Water Slide:
    1. Sóng cũ bị xóa (nếu có).
    2. Player chọn 1 ô đích trong cùng hàng (không tính ô góc).
    3. Sóng mới được tạo từ ô Water Slide → ô đích.
    4. Player trượt ngay đến ô đích và resolve effect bình thường.

- Khi player khác di chuyển qua vùng sóng (source+1 → dest theo chiều tiến):
    → Player bị đẩy ngay đến dest, resolve effect bình thường.
    → Sóng KHÔNG bị tiêu sau khi đẩy.

- Sóng tồn tại mãi cho đến khi có người đáp vào ô Water Slide tiếp theo.
  Người đó tạo sóng mới hay không → sóng cũ đều bị xóa.

- Toàn bàn chỉ tồn tại 1 sóng tại 1 thời điểm.

Logic chính nằm trong GameController (fsm.py) để dùng được water_slide_decision_fn.
Strategy chỉ giữ phần AI helper.
"""

from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board, SpaceId
from ctp.core.events import GameEvent


class WaterSlideStrategy(TileStrategy):
    """Strategy for Water Slide tile (spaceId=40). Map 3 only.

    on_land/on_pass trả về [] vì GameController xử lý toàn bộ logic Water Slide.
    """

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Stub — FSM handles water slide logic directly."""
        return []

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        return []

    @staticmethod
    def pick_dest_ai(player: Player, candidates: list[Tile], board: Board) -> Tile:
        """Chọn ô đích có lợi nhất cho player (headless AI).

        Thứ tự ưu tiên:
        1. Ô CITY chưa có chủ → mua được (ưu tiên ô đắt nhất = giá trị cao nhất).
        2. Ô RESORT chưa có chủ.
        3. Ô đang sở hữu (không tốn tiền).
        4. Ô không phải property (START, FESTIVAL, GAME, CHANCE, TAX, TRAVEL).
        5. Ô của đối thủ có tiền thuê thấp nhất.

        Args:
            player: Player đang chọn.
            candidates: Danh sách ô hợp lệ (cùng hàng, không phải góc, không phải ô WS).
            board: Board hiện tại.

        Returns:
            Tile được chọn (luôn có giá trị do candidates không rỗng).
        """
        # Priority 1: unowned CITY — prefer highest buy value
        unowned_city = [
            t for t in candidates
            if t.space_id == SpaceId.CITY and t.owner_id is None
        ]
        if unowned_city:
            def city_value(t: Tile) -> int:
                cfg = board.get_land_config(t.opt)
                if not cfg:
                    return 0
                return cfg.get("building", {}).get("1", {}).get("build", 0)
            return max(unowned_city, key=city_value)

        # Priority 2: unowned RESORT
        unowned_resort = [
            t for t in candidates
            if t.space_id == SpaceId.RESORT and t.owner_id is None
        ]
        if unowned_resort:
            return unowned_resort[0]

        # Priority 3: own tile (free)
        own = [t for t in candidates if t.owner_id == player.player_id]
        if own:
            return own[0]

        # Priority 4: non-property tiles (no rent)
        non_property = [
            t for t in candidates
            if t.space_id not in (SpaceId.CITY, SpaceId.RESORT)
        ]
        if non_property:
            return non_property[0]

        # Priority 5: opponent tile with lowest rent
        def rent_cost(t: Tile) -> int:
            if t.space_id == SpaceId.CITY:
                cfg = board.get_land_config(t.opt)
                if cfg:
                    lv = str(t.building_level)
                    return cfg.get("building", {}).get(lv, {}).get("toll", 0)
            if t.space_id == SpaceId.RESORT:
                resort_cfg = board.get_resort_config() or {}
                return resort_cfg.get("tollCost", 0) * (t.visit_count + 1)
            return 0

        return min(candidates, key=rent_cost)
