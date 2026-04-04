"""GameController FSM for CTP game."""

from enum import Enum, auto
from typing import Callable
import random
from ctp.core.models import Player
from ctp.core.board import Board, SpaceId, Tile
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.constants import BASE_UNIT
from ctp.tiles.registry import TileRegistry


# Căn lực: 4 khoảng xúc xắc (D-37)
_CAN_LUC_RANGES = [
    (2, 4),    # Khoảng 0: low
    (5, 7),    # Khoảng 1: mid-low (default fallback)
    (7, 9),    # Khoảng 2: mid-high (7 overlap với khoảng 1 — by design)
    (10, 12),  # Khoảng 3: high
]


class TurnPhase(Enum):
    """FSM states for each turn.

    The game flows through these phases in order:
    1. ROLL - Roll dice (2d6)
    2. MOVE - Move player based on dice roll
    3. RESOLVE_TILE - Apply tile effect
    4. ACQUIRE - Forced acquisition (player buys opponent's land if able)
    5. UPGRADE - Upgrade all owned properties if affordable
    6. CHECK_BANKRUPTCY - Check if player is bankrupt
    7. END_TURN - Advance to next player
    """

    ROLL = auto()
    MOVE = auto()
    RESOLVE_TILE = auto()
    ACQUIRE = auto()
    UPGRADE = auto()
    CHECK_BANKRUPTCY = auto()
    END_TURN = auto()


class GameController:
    """Manages game flow through FSM states.

    This controller orchestrates the game loop, handling dice rolls,
    player movement, tile resolution, bankruptcy checks, and turn
    transitions.
    """

    def __init__(
        self,
        board: Board,
        players: list[Player],
        max_turns: int,
        event_bus: EventBus,
        buy_decision_fn: Callable[["GameController", Player, Tile, float], bool] | None = None,
        starting_cash: float = 1_000_000,
    ):
        """Initialize the game controller.

        Args:
            board: The game board.
            players: List of players (2-4).
            max_turns: Maximum number of turns before game ends.
            event_bus: Event bus for publishing game events.
            buy_decision_fn: Callback quyết định player có mua đất không.
                Signature: (controller, player, tile, price) -> bool.
                Mặc định None = luôn mua nếu đủ tiền (headless auto-buy).
        """
        self.board = board
        self.players = players
        self.max_turns = max_turns
        self.event_bus = event_bus
        self.buy_decision_fn = buy_decision_fn  # None = always buy if affordable
        self.travel_decision_fn = None  # set bên ngoài nếu cần UI/interactive
        self.water_slide_decision_fn = None  # (controller, player, candidates) -> Tile | None
        self._starting_cash = starting_cash
        self.phase = TurnPhase.ROLL
        self.current_player_index = 0
        self.current_turn = 1
        self._current_dice: tuple[int, int] = (0, 0)
        self._passed_start = False
        self._game_over = False
        self._winner: str | None = None
        # {tile_position: max_level} — set khi mua/cuop dat, cleared sau upgrade
        self._upgrade_eligible: dict[int, int] = {}
        self._rolled_doubles: bool = False  # đổ đôi → được đổ lại
        self._doubles_streak: int = 0       # đổ đôi liên tiếp; 3 lần → vào tù
        self._elevated_tile_to_resolve: int | None = None  # vị trí ô nâng cần resolve
        self._pending_debt: int = 0  # nợ thuê chưa trả (khi không đủ tiền trả ngay)

    @property
    def current_player(self) -> Player:
        """Get the current player."""
        return self.players[self.current_player_index]

    def roll_dice(self) -> tuple[int, int]:
        """Roll 2d6 dice.

        Returns:
            Tuple of (die1, die2), each 1-6.
        """
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        self._current_dice = (die1, die2)
        return self._current_dice

    def step(self) -> list[GameEvent]:
        """Advance FSM one step.

        Returns:
            List of GameEvents produced in this step.
        """
        if self._game_over:
            return []

        match self.phase:
            case TurnPhase.ROLL:
                return self._do_roll()
            case TurnPhase.MOVE:
                return self._do_move()
            case TurnPhase.RESOLVE_TILE:
                return self._do_resolve_tile()
            case TurnPhase.ACQUIRE:
                return self._do_acquire()
            case TurnPhase.UPGRADE:
                return self._do_upgrade()
            case TurnPhase.CHECK_BANKRUPTCY:
                return self._do_check_bankruptcy()
            case TurnPhase.END_TURN:
                return self._do_end_turn()

    def _choose_range_ai(self) -> int:
        """Chọn khoảng lực tối ưu dựa trên vị trí đích (stub AI per D-39).

        Strategy:
        1. Tìm unowned CITY/RESORT gần nhất (ưu tiên opt cao hơn).
        2. Nếu steps nằm trong khoảng nào đó → ưu tiên khoảng đó.
        3. Nếu khoảng ưu tiên trùng với đất đối thủ → giảm ưu tiên.
        4. Trong các khoảng còn lại → ưu tiên khoảng chứa doubles values.
        5. Fallback: khoảng 1 [5-7].

        Returns:
            Index của khoảng (0-3).
        """
        player = self.current_player
        board = self.board
        # Tìm unowned CITY/RESORT gần nhất (trong 12 bước)
        best_step = None
        for steps in range(1, 13):
            target_pos = ((player.position - 1 + steps) % 32) + 1
            tile = board.get_tile(target_pos)
            if tile.space_id in (SpaceId.CITY, SpaceId.RESORT) and tile.owner_id is None:
                best_step = steps
                break  # first unowned, stop

        if best_step is None:
            return 1  # Fallback

        # Tìm khoảng khớp
        for i, (lo, hi) in enumerate(_CAN_LUC_RANGES):
            if lo <= best_step <= hi:
                # Kiểm tra target có phải đất đối thủ không
                target_pos = ((player.position - 1 + best_step) % 32) + 1
                tile = board.get_tile(target_pos)
                if tile.owner_id and tile.owner_id != player.player_id:
                    continue  # bỏ qua khoảng này
                return i

        # Fallback: khoảng có doubles (6 và 8 là doubles values trong các khoảng)
        for i, (lo, hi) in enumerate(_CAN_LUC_RANGES):
            doubles_in_range = [v for v in range(lo, hi + 1) if v % 2 == 0 and 2 <= v <= 12]
            if doubles_in_range:
                return i
        return 1

    def _resolve_can_luc(self, chosen_range: int) -> tuple[int, int]:
        """Precision dice roll cho căn lực (D-38).

        15% cơ hội hit khoảng đã chọn (player.accuracy_rate).
        Nếu hit: random T trong [lo, hi], split theo D-40.
        Nếu miss: normal 2d6.

        Args:
            chosen_range: Index khoảng lực (0-3).

        Returns:
            (d1, d2) dice pair.
        """
        lo, hi = _CAN_LUC_RANGES[chosen_range]
        precision_check = random.randint(1, 100)
        if precision_check <= self.current_player.accuracy_rate:
            # Hit: random T trong khoảng, split thành (d1, d2) per D-40
            T = random.randint(lo, hi)
            d1_lo = max(1, T - 6)
            d1_hi = min(6, T - 1)
            d1 = random.randint(d1_lo, d1_hi)
            d2 = T - d1
            return (d1, d2)
        else:
            # Miss: normal 2d6
            return (random.randint(1, 6), random.randint(1, 6))

    def _do_roll(self) -> list[GameEvent]:
        """Roll dice and transition to MOVE.

        Returns:
            Empty list (dice event is published).
        """
        if self.current_player.pending_travel:
            self._resolve_travel_attempt()
            self.phase = TurnPhase.END_TURN
            return []

        # [NEW D-42 Step A] EF_19 Escape card — auto-use khi ở tù (D-16)
        if (self.current_player.prison_turns_remaining > 0
                and self.current_player.held_card is not None):
            from ctp.tiles.fortune import _load_raw_card_data
            raw = _load_raw_card_data()
            held_effect = raw.get(self.current_player.held_card, {}).get("effect", "")
            if held_effect == "EF_19":
                self.current_player.held_card = None  # consume (D-08)
                self.current_player.exit_prison()     # prison_turns = 0
                self.event_bus.publish(GameEvent(
                    event_type=EventType.CARD_EFFECT_ESCAPE_USED,
                    player_id=self.current_player.player_id,
                    data={}
                ))
                # Tiếp tục roll bình thường (không return, fall through)

        # [NEW D-42 Step B] Decrement double_toll_turns ở đầu ROLL phase
        if self.current_player.double_toll_turns > 0:
            self.current_player.double_toll_turns -= 1

        if self.current_player.prison_turns_remaining > 0:
            result = self._resolve_prison_attempt()
            if result == 'skip':
                return []   # bỏ lượt, phase đã set END_TURN trong helper
            # result == 'play': ra tù, _current_dice đã set, chơi bình thường
            if self._doubles_streak >= 3:
                self._doubles_streak = 0
                self._rolled_doubles = False
                self.current_player.move_to(9)
                self.current_player.enter_prison()
                self.event_bus.publish(GameEvent(
                    event_type=EventType.PRISON_ENTERED,
                    player_id=self.current_player.player_id,
                    data={"turns": self.current_player.prison_turns_remaining, "reason": "triple_doubles"}
                ))
                self.phase = TurnPhase.END_TURN
                return []
            self.event_bus.publish(GameEvent(
                event_type=EventType.TURN_STARTED,
                player_id=self.current_player.player_id,
                data={"turn": self.current_turn}
            ))
            self.phase = TurnPhase.MOVE
            return []

        # [NEW D-42 Step C] AI chọn khoảng lực
        chosen_range = self._choose_range_ai()
        # [NEW D-42 Step D] Precision roll
        precision_dice = self._resolve_can_luc(chosen_range)
        precision_hit = False
        # Xác định hit: sum trong khoảng đã chọn
        lo, hi = _CAN_LUC_RANGES[chosen_range]
        if lo <= sum(precision_dice) <= hi:
            precision_hit = True

        # Set dice result
        self._current_dice = precision_dice
        dice = precision_dice
        self._rolled_doubles = (dice[0] == dice[1])

        if self._rolled_doubles:
            self._doubles_streak += 1
        else:
            self._doubles_streak = 0

        # Đổ đôi 3 lần liên tiếp → vào tù ngay, bỏ lượt (publish dice trước khi vào tù)
        if self._doubles_streak >= 3:
            self._doubles_streak = 0
            self._rolled_doubles = False
            self.event_bus.publish(GameEvent(
                event_type=EventType.DICE_ROLL,
                player_id=self.current_player.player_id,
                data={
                    "dice": dice,
                    "total": sum(dice),
                    "doubles": self._rolled_doubles,
                    "doubles_streak": self._doubles_streak,
                    "chosen_range": chosen_range,
                    "precision_hit": precision_hit,
                }
            ))
            self.current_player.move_to(9)  # ô tù = position 9
            self.current_player.enter_prison()
            self.event_bus.publish(GameEvent(
                event_type=EventType.PRISON_ENTERED,
                player_id=self.current_player.player_id,
                data={"turns": self.current_player.prison_turns_remaining, "reason": "triple_doubles"}
            ))
            self.phase = TurnPhase.END_TURN
            return []

        # Normal: TURN_STARTED trước, sau đó mới DICE_ROLL
        self.event_bus.publish(GameEvent(
            event_type=EventType.TURN_STARTED,
            player_id=self.current_player.player_id,
            data={"turn": self.current_turn}
        ))

        self.event_bus.publish(GameEvent(
            event_type=EventType.DICE_ROLL,
            player_id=self.current_player.player_id,
            data={
                "dice": dice,
                "total": sum(dice),
                "doubles": self._rolled_doubles,
                "doubles_streak": self._doubles_streak,
                "chosen_range": chosen_range,
                "precision_hit": precision_hit,
            }
        ))

        self.phase = TurnPhase.MOVE
        return []

    def _resolve_prison_attempt(self) -> str:
        """Xử lý lượt của người chơi đang ở trong tù.

        2 lựa chọn (headless: trả tiền nếu đủ, không đủ thì đổ xúc xắc):
          A. Trả phí → ra tù, roll mới để đi bình thường  → return 'play'
          B. Đổ xúc xắc:
             - Ra đôi → ra tù, di chuyển bình thường, cuối lượt được đổ thêm → return 'play'
             - Không ra đôi → ngồi tiếp (decrement), hoặc hết hạn thì ra + play → return 'skip' / 'play'

        Return values:
          'play'    – đã ra tù, _current_dice đã set, tiếp tục chơi bình thường
          'skip'    – không ra đôi, vẫn trong tù, bỏ lượt
        """
        prison_cfg = self.board.get_prison_config() or {}
        escape_fee = int(prison_cfg.get("escapeCostRate", 0.05) * self._starting_cash)
        pid = self.current_player.player_id

        if self.current_player.can_afford(escape_fee):
            # --- Lựa chọn A: Trả phí ---
            self.current_player.cash -= escape_fee
            self.current_player.exit_prison()
            self.event_bus.publish(GameEvent(
                event_type=EventType.TAX_PAID,
                player_id=pid,
                data={"amount": escape_fee, "reason": "prison_escape"}
            ))
            self.event_bus.publish(GameEvent(
                event_type=EventType.PRISON_EXITED,
                player_id=pid,
                data={"reason": "paid"}
            ))
            # Roll mới để di chuyển
            dice = self.roll_dice()
            self._rolled_doubles = (dice[0] == dice[1])
            self._doubles_streak = 1 if self._rolled_doubles else 0
            self.event_bus.publish(GameEvent(
                event_type=EventType.DICE_ROLL,
                player_id=pid,
                data={"dice": dice, "total": sum(dice), "doubles": self._rolled_doubles,
                      "doubles_streak": self._doubles_streak}
            ))
            return 'play'

        # --- Lựa chọn B: Đổ xúc xắc (bắt buộc nếu không đủ tiền) ---

        # Nếu đây là lượt cuối trong tù → mãn hạn, ra luôn, không cần thử đôi
        if self.current_player.prison_turns_remaining <= 1:
            self.current_player.decrement_prison_turn()
            self.current_player.exit_prison()
            self.event_bus.publish(GameEvent(
                event_type=EventType.PRISON_EXITED,
                player_id=pid,
                data={"reason": "served"}
            ))
            dice = self.roll_dice()
            self._rolled_doubles = (dice[0] == dice[1])
            self._doubles_streak = 1 if self._rolled_doubles else 0
            self.event_bus.publish(GameEvent(
                event_type=EventType.DICE_ROLL,
                player_id=pid,
                data={"dice": dice, "total": sum(dice), "doubles": self._rolled_doubles,
                      "doubles_streak": self._doubles_streak}
            ))
            return 'play'

        # Còn lượt → thử đổ đôi để thoát sớm
        dice = self.roll_dice()
        is_doubles = (dice[0] == dice[1])
        self.event_bus.publish(GameEvent(
            event_type=EventType.DICE_ROLL,
            player_id=pid,
            data={"dice": dice, "total": sum(dice), "doubles": is_doubles, "prison_roll": True}
        ))

        if is_doubles:
            # Ra đôi → thoát tù, di chuyển bình thường, được đổ thêm cuối lượt
            self.current_player.exit_prison()
            self.event_bus.publish(GameEvent(
                event_type=EventType.PRISON_EXITED,
                player_id=pid,
                data={"reason": "doubles"}
            ))
            self._rolled_doubles = True
            self._doubles_streak = 1
            return 'play'

        # Không ra đôi, còn lượt → ngồi tiếp
        self.current_player.decrement_prison_turn()
        # prison_turns_remaining still > 0 here (last-turn case handled above)
        if self.current_player.prison_turns_remaining == 0:
            # fallback (should not happen normally)
            self.current_player.exit_prison()
            self.event_bus.publish(GameEvent(
                event_type=EventType.PRISON_EXITED,
                player_id=pid,
                data={"reason": "served"}
            ))
            dice = self.roll_dice()
            self._rolled_doubles = (dice[0] == dice[1])
            self._doubles_streak = 1 if self._rolled_doubles else 0
            self.event_bus.publish(GameEvent(
                event_type=EventType.DICE_ROLL,
                player_id=pid,
                data={"dice": dice, "total": sum(dice), "doubles": self._rolled_doubles,
                      "doubles_streak": self._doubles_streak}
            ))
            return 'play'

        # Vẫn trong tù, bỏ lượt
        self.event_bus.publish(GameEvent(
            event_type=EventType.TURN_STARTED,
            player_id=pid,
            data={"turn": self.current_turn, "reason": "in_prison"}
        ))
        self.phase = TurnPhase.END_TURN
        return 'skip'

    def _resolve_travel_attempt(self) -> None:
        """Xử lý travel đã pending từ lượt trước.

        Luật:
        - Không đủ tiền trả phí → hết lượt, không đi.
        - Đủ tiền → player chọn 1 ô bất kỳ trên map (không phải ô du lịch).
        - Player có quyền từ chối đi → hết lượt, không tốn tiền.
        - Chấp nhận → trả phí, teleport đến ô đã chọn.
        - Cả 2 trường hợp: xóa pending_travel, kết thúc lượt.

        travel_decision_fn(controller, player, candidates) -> Tile | None
            Trả về ô muốn đến, hoặc None để từ chối.
            Nếu không set (headless): chọn ngẫu nhiên 1 ô.
        """
        import random
        from ctp.core.constants import STARTING_CASH
        from ctp.core.board import SpaceId

        player = self.current_player
        player.pending_travel = False

        travel_cfg = self.board.get_travel_config() or {}
        travel_cost_rate = travel_cfg.get("travelCostRate", 0.02)
        travel_fee = int(travel_cost_rate * STARTING_CASH)

        # Không đủ tiền → hết lượt ngay
        if not player.can_afford(travel_fee):
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_MOVE,
                player_id=player.player_id,
                data={"reason": "travel_no_funds", "travel_fee": travel_fee}
            ))
            return

        # Đủ tiền → cho chọn bất kỳ ô nào không phải ô du lịch
        candidates = [
            t for t in self.board.board
            if t.space_id != SpaceId.TRAVEL
            and t.position != player.position
        ]
        if not candidates:
            return

        # Gọi callback để player chọn đích (hoặc từ chối)
        if self.travel_decision_fn is not None:
            destination = self.travel_decision_fn(self, player, candidates)
        else:
            # Headless default: chọn ngẫu nhiên
            destination = random.choice(candidates)

        # Player từ chối → hết lượt, không tốn tiền
        if destination is None:
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_MOVE,
                player_id=player.player_id,
                data={"reason": "travel_declined", "travel_fee": travel_fee}
            ))
            return

        # Chấp nhận → trả phí, di chuyển đặc biệt
        player.cash -= travel_fee
        old_pos = player.position

        # Kiểm tra có đi qua Start không (di chuyển vòng quanh board)
        passed_start = destination.position < old_pos

        player.position = destination.position

        self.event_bus.publish(GameEvent(
            event_type=EventType.PLAYER_MOVE,
            player_id=player.player_id,
            data={
                "old_pos": old_pos,
                "new_pos": destination.position,
                "travel_fee": travel_fee,
                "reason": "travel_accepted",
                "passed_start": passed_start,
                "move_type": 2,   # teleport
            }
        ))

        # Nếu đi qua Start → nhận thưởng bình thường
        if passed_start:
            start_tile = self.board.get_tile(1)
            start_strategy = TileRegistry.resolve(SpaceId.START)
            start_strategy.on_pass(player, start_tile, self.board, self.event_bus)

    def _do_move(self) -> list[GameEvent]:
        """Move player and check for passing Start. Transition to RESOLVE_TILE.

        Nếu có ô nâng trong đường đi, player dừng tại ô đó,
        tile hạ xuống, doubles bị huỷ.

        Returns:
            List of events from moving (including passing Start bonus).
        """
        dice_total = sum(self._current_dice)
        old_pos = self.current_player.position
        events = []

        # Check for elevated tile in path
        elevated_pos = self.board.find_elevated_in_path(old_pos, dice_total)

        # [NEW D-43] EF_22 Pinwheel bypass — bỏ qua elevated tile nếu player giữ Pinwheel card
        if elevated_pos is not None and self.current_player.held_card is not None:
            from ctp.tiles.fortune import _load_raw_card_data
            raw = _load_raw_card_data()
            held_effect = raw.get(self.current_player.held_card, {}).get("effect", "")
            if held_effect == "EF_22":
                self.current_player.held_card = None   # consume (D-08)
                self.board.elevated_tile = None         # clear elevated state
                elevated_pos = None                     # skip elevated block
                self.event_bus.publish(GameEvent(
                    event_type=EventType.CARD_EFFECT_PINWHEEL_BYPASS,
                    player_id=self.current_player.player_id,
                    data={}
                ))

        if elevated_pos is not None:
            # Tính xem có qua Start không (so với ô nâng, không phải đích ban đầu)
            steps_to_elevated = 0
            for i in range(1, dice_total + 1):
                if ((old_pos - 1 + i) % 32) + 1 == elevated_pos:
                    steps_to_elevated = i
                    break
            self._passed_start = (old_pos + steps_to_elevated) > 32

            start_tile = self.board.get_tile(1)
            start_strategy = TileRegistry.resolve(SpaceId.START)
            if self._passed_start:
                events = start_strategy.on_pass(
                    self.current_player, start_tile, self.board, self.event_bus
                )

            # Di chuyển đến ô nâng
            self.current_player.position = elevated_pos
            # Hạ ô nâng xuống
            self.board.lower_tile(elevated_pos)
            self._elevated_tile_to_resolve = elevated_pos
            # Huỷ đổ đôi
            self._rolled_doubles = False

            self.event_bus.publish(GameEvent(
                event_type=EventType.TILE_LOWERED,
                player_id=self.current_player.player_id,
                data={"position": elevated_pos}
            ))
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_MOVE,
                player_id=self.current_player.player_id,
                data={
                    "old_pos": old_pos,
                    "new_pos": elevated_pos,
                    "passed_start": self._passed_start,
                    "blocked_by_elevated": True,
                    "move_type": 1,   # walk (player moves tile-by-tile to elevated pos)
                }
            ))
            self.phase = TurnPhase.RESOLVE_TILE
            return events

        # --- Kiểm tra vùng sóng Water Slide ---
        if self.board.water_wave is not None:
            zone = self.board.get_wave_zone()
            intercept_step = None
            for i in range(1, dice_total + 1):
                if ((old_pos - 1 + i) % 32) + 1 in zone:
                    intercept_step = i
                    break

            if intercept_step is not None:
                _, wave_dest = self.board.water_wave
                self._passed_start = (old_pos + intercept_step) > 32

                start_tile = self.board.get_tile(1)
                start_strategy = TileRegistry.resolve(SpaceId.START)
                if self._passed_start:
                    events = start_strategy.on_pass(
                        self.current_player, start_tile, self.board, self.event_bus
                    )

                self.current_player.position = wave_dest

                self.event_bus.publish(GameEvent(
                    event_type=EventType.WATER_SLIDE_PUSHED,
                    player_id=self.current_player.player_id,
                    data={
                        "old_pos": old_pos,
                        "new_pos": wave_dest,
                        "passed_start": self._passed_start,
                    }
                ))
                self.event_bus.publish(GameEvent(
                    event_type=EventType.PLAYER_MOVE,
                    player_id=self.current_player.player_id,
                    data={
                        "old_pos": old_pos,
                        "new_pos": wave_dest,
                        "passed_start": self._passed_start,
                        "reason": "wave_push",
                        "move_type": 2,   # teleport (water slide)
                    }
                ))
                self.phase = TurnPhase.RESOLVE_TILE
                return events

        # --- Di chuyển bình thường ---
        new_pos = old_pos + dice_total
        self._passed_start = new_pos > 32

        start_tile = self.board.get_tile(1)
        strategy = TileRegistry.resolve(SpaceId.START)

        if self._passed_start:
            events = strategy.on_pass(self.current_player, start_tile, self.board, self.event_bus)

        self.current_player.position = ((new_pos - 1) % 32) + 1

        self.event_bus.publish(GameEvent(
            event_type=EventType.PLAYER_MOVE,
            player_id=self.current_player.player_id,
            data={
                "old_pos": old_pos,
                "new_pos": self.current_player.position,
                "passed_start": self._passed_start,
                "move_type": 1,   # walk tile-by-tile
            }
        ))

        self.phase = TurnPhase.RESOLVE_TILE
        return events

    def _do_resolve_tile(self) -> list[GameEvent]:
        """Apply tile effect. Transition to ACQUIRE.

        Returns:
            List of events from tile resolution.
        """
        tile = self.board.get_tile(self.current_player.position)
        was_unowned = (tile.space_id == SpaceId.CITY and tile.owner_id is None)
        is_own = (tile.space_id == SpaceId.CITY and tile.owner_id == self.current_player.player_id)

        # Publish TILE_LANDED truoc: Dung o -> Mua dat / Nang cap
        self.event_bus.publish(GameEvent(
            event_type=EventType.TILE_LANDED,
            player_id=self.current_player.player_id,
            data={
                "position": tile.position,
                "tile_type": tile.space_id.name,
                "tile_id": tile.space_id
            }
        ))

        self._elevated_tile_to_resolve = None  # clear flag setelah resolve
        cash_before_resolve = self.current_player.cash

        strategy = TileRegistry.resolve(tile.space_id)
        events = strategy.on_land(
            self.current_player, tile, self.board, self.event_bus,
            players=self.players
        )

        # Water Slide: di chuyển player đến dest, sau đó resolve ô đích
        if tile.space_id == SpaceId.WATER_SLIDE:
            slide_events = self._handle_water_slide_land(tile)
            events.extend(slide_events)
            # Player đã được move đến dest bên trong _handle_water_slide_land
            tile = self.board.get_tile(self.current_player.position)
            was_unowned = (tile.space_id == SpaceId.CITY and tile.owner_id is None)
            is_own = (tile.space_id == SpaceId.CITY
                      and tile.owner_id == self.current_player.player_id)
            dest_strategy = TileRegistry.resolve(tile.space_id)
            dest_events = dest_strategy.on_land(
                self.current_player, tile, self.board, self.event_bus,
                players=self.players
            )
            events.extend(dest_events)

        if was_unowned:
            # Lan dau: mua + xay ngay (khong tao upgrade eligible -> khong co [Nang cap])
            buy_events = self._try_buy_property(self.current_player, tile)
            events.extend(buy_events)
        elif is_own:
            # Lan 2+: da co nha san, moi duoc nang cap
            max_lv = 5 if tile.building_level >= 4 else 4
            self._upgrade_eligible.setdefault(tile.position, max_lv)

        # Rẽ nhánh sớm: nếu player phá sản sau khi trả tiền thuê → bỏ qua ACQUIRE/UPGRADE
        if self.current_player.cash < 0:
            self._pending_debt = cash_before_resolve - self.current_player.cash
            self.phase = TurnPhase.CHECK_BANKRUPTCY
        else:
            self.phase = TurnPhase.ACQUIRE
        return events

    def _do_acquire(self) -> list[GameEvent]:
        """Attempt forced acquisition of tile from opponent. Transition to UPGRADE.

        Returns:
            List of events from acquisition (PROPERTY_ACQUIRED if bought).
        """
        from ctp.controller.acquisition import resolve_acquisition

        tile = self.board.get_tile(self.current_player.position)
        acquire_rate = 1.0  # From Board.json General.acquireRate
        events = resolve_acquisition(
            self.current_player, tile, self.board,
            self.players, self.event_bus, acquire_rate
        )

        # Rule: cuop dat doi thu (PROPERTY_ACQUIRED) -> eligible nang cap len toi da L3
        for e in events:
            if (e.event_type == EventType.PROPERTY_ACQUIRED
                    and e.player_id == self.current_player.player_id):
                pos = e.data.get("position")
                self._upgrade_eligible[pos] = 4  # toi da L3; Landmark co dieu kien rieng

        self.phase = TurnPhase.UPGRADE
        return events

    def _do_upgrade(self) -> list[GameEvent]:
        """Upgrade all owned properties if affordable. Transition to CHECK_BANKRUPTCY.

        Returns:
            List of events from upgrades (PROPERTY_UPGRADED for each upgrade).
        """
        from ctp.controller.upgrade import resolve_upgrades

        events = resolve_upgrades(
            self.current_player, self.board, self.event_bus,
            eligible_positions=self._upgrade_eligible,
        )
        self._upgrade_eligible.clear()
        self.phase = TurnPhase.CHECK_BANKRUPTCY
        return events

    def _do_check_bankruptcy(self) -> list[GameEvent]:
        """Check if current player is bankrupt. Transition to END_TURN.

        Returns:
            List of events from bankruptcy resolution.
        """
        from ctp.controller.bankruptcy import resolve_bankruptcy

        events = []
        if self.current_player.cash < 0:
            # Xác định creditor: chủ đất ô player đang đứng (nếu là đất người khác)
            tile = self.board.get_tile(self.current_player.position)
            creditor = None
            if tile.owner_id and tile.owner_id != self.current_player.player_id:
                creditor = next(
                    (p for p in self.players if p.player_id == tile.owner_id), None
                )
            events = resolve_bankruptcy(
                self.current_player,
                self.board,
                self.event_bus,
                creditor=creditor,
                debt=self._pending_debt,
            )
            self._pending_debt = 0

        # Đổ đôi → được đổ thêm 1 lần (trừ khi phá sản hoặc đang bị tù)
        if (self._rolled_doubles
                and not self.current_player.is_bankrupt
                and self.current_player.prison_turns_remaining == 0):
            self._rolled_doubles = False
            self.event_bus.publish(GameEvent(
                event_type=EventType.BONUS_RECEIVED,
                player_id=self.current_player.player_id,
                data={"reason": "doubles_reroll", "amount": 0}
            ))
            self.phase = TurnPhase.ROLL
        else:
            self._rolled_doubles = False
            self.phase = TurnPhase.END_TURN
        return events

    def _do_end_turn(self) -> list[GameEvent]:
        """Advance to next non-bankrupt player. Check terminal conditions.

        Terminal conditions (checked in order):
        1. Instant win: 4 resort / 3 color groups / own 1 row → reason varies
        2. Only 1 player còn tiền (non-bankrupt) → reason="last_player_standing"
        3. Reached max_turns (25) → reason="max_turns"

        Returns:
            Empty list (game ended events are published separately).
        """
        self.current_player.turns_taken += 1  # hoàn thành 1 lượt

        self.event_bus.publish(GameEvent(
            event_type=EventType.TURN_ENDED,
            player_id=self.current_player.player_id,
            data={"turn": self.current_turn}
        ))

        # Condition 0: instant win conditions
        win_reason = self._check_instant_win(self.current_player)
        if win_reason:
            self._game_over = True
            self._winner = self.current_player.player_id
            self.event_bus.publish(GameEvent(
                event_type=EventType.GAME_ENDED,
                data={
                    "winner": self._winner,
                    "turns": self.current_turn,
                    "reason": win_reason,
                }
            ))
            return []

        # Condition 1: chỉ còn 1 người còn tiền
        active_players = [p for p in self.players if not p.is_bankrupt]
        if len(active_players) <= 1:
            self._game_over = True
            self._winner = self._get_winner()
            self.event_bus.publish(GameEvent(
                event_type=EventType.GAME_ENDED,
                data={
                    "winner": self._winner,
                    "turns": self.current_turn,
                    "reason": "last_player_standing"
                }
            ))
            return []

        # [D-46] Decrement virus_turns for all debuffed players
        for p in self.players:
            if p.virus_turns > 0:
                p.virus_turns -= 1

        # [D-46] Decrement toll_debuff_turns trên tất cả tiles sau mỗi END_TURN
        for tile in self.board.board:
            if tile.toll_debuff_turns > 0:
                tile.toll_debuff_turns -= 1
                if tile.toll_debuff_turns == 0:
                    tile.toll_debuff_rate = 1.0

        # Advance turn counter
        self._advance_to_next_player()

        # Condition 2: hết 25 turn
        if self.current_turn >= self.max_turns:
            self._game_over = True
            self._winner = self._get_winner()
            self.event_bus.publish(GameEvent(
                event_type=EventType.GAME_ENDED,
                data={
                    "winner": self._winner,
                    "turns": self.current_turn,
                    "reason": "max_turns"
                }
            ))
        else:
            self.phase = TurnPhase.ROLL

        return []

    def _advance_to_next_player(self) -> None:
        """Move to next non-bankrupt player.

        Increments turn counter when wrapping back to player 0.
        """
        self._doubles_streak = 0  # reset khi đổi lượt
        next_index = (self.current_player_index + 1) % len(self.players)
        if next_index == 0:
            self.current_turn += 1

        # Skip bankrupt players
        start_index = next_index
        while self.players[next_index].is_bankrupt:
            next_index = (next_index + 1) % len(self.players)
            if next_index == start_index:
                # All players bankrupt
                break

        self.current_player_index = next_index

    def is_game_over(self) -> bool:
        """Check if game has reached terminal state.

        Terminal conditions:
        - Only 1 player còn tiền (non-bankrupt) remains
        - Current turn >= max_turns (25)

        Returns:
            True if game is over, False otherwise.
        """
        if self._game_over:
            return True
        active_players = [p for p in self.players if not p.is_bankrupt]
        if len(active_players) <= 1:
            return True
        if self.current_turn >= self.max_turns:
            return True
        return False

    def _handle_water_slide_land(self, water_tile: Tile) -> list[GameEvent]:
        """Xử lý khi player đáp vào ô Water Slide.

        Luật:
        - Sóng cũ bị xóa vô điều kiện.
        - Player chọn 1 ô đích trong cùng hàng (không phải ô góc, không phải ô WS).
        - Sóng mới được đặt (source=water_tile.position, dest=dest.position).
        - Player di chuyển đến dest ngay lập tức.
        - Nếu không có ô hợp lệ: không tạo sóng, player ở lại ô WS.

        Args:
            water_tile: Ô Water Slide mà player vừa đáp.

        Returns:
            Danh sách GameEvent (WATER_SLIDE_WAVE_SET).
        """
        from ctp.tiles.water_slide import WaterSlideStrategy

        events: list[GameEvent] = []
        player = self.current_player

        # Xóa sóng cũ
        self.board.water_wave = None

        # Lấy các ô hợp lệ trong cùng hàng
        candidate_positions = self.board.get_row_non_corner_positions(water_tile.position)
        candidates = [self.board.get_tile(p) for p in candidate_positions]

        if not candidates:
            return events

        # Chọn dest
        if self.water_slide_decision_fn is not None:
            dest_tile = self.water_slide_decision_fn(self, player, candidates)
        else:
            dest_tile = WaterSlideStrategy.pick_dest_ai(player, candidates, self.board)

        if dest_tile is None:
            return events

        # Đặt sóng mới và di chuyển player
        self.board.water_wave = (water_tile.position, dest_tile.position)
        old_pos = player.position
        player.position = dest_tile.position

        event = GameEvent(
            event_type=EventType.WATER_SLIDE_WAVE_SET,
            player_id=player.player_id,
            data={
                "source": water_tile.position,
                "dest": dest_tile.position,
                "player_moved_from": old_pos,
            }
        )
        self.event_bus.publish(event)
        events.append(event)
        return events

    def _try_buy_property(self, player: Player, tile: Tile) -> list[GameEvent]:
        """Xử lý quyết định mua đất trống.

        Gọi buy_decision_fn để hỏi player có muốn mua không.
        Nếu buy_decision_fn là None (headless), mặc định luôn mua nếu đủ tiền.

        Args:
            player: Player đang đứng trên ô.
            tile: Ô đất trống (owner_id is None).

        Returns:
            List[GameEvent] — PROPERTY_PURCHASED nếu mua, rỗng nếu không mua.
        """
        land_config = self.board.get_land_config(tile.opt)
        if not land_config:
            return []

        building = land_config.get("building", {})
        price = building.get("1", {}).get("build", 0) * BASE_UNIT

        if not player.can_afford(price):
            return []

        # Hỏi quyết định mua
        if self.buy_decision_fn is not None:
            should_buy = self.buy_decision_fn(self, player, tile, price)
        else:
            should_buy = True  # headless default: luon mua neu du tien

        if not should_buy:
            return []

        # Mua dat: cam co + xay them den L3 neu du tien
        total_cost = price
        player.cash -= price
        player.add_property(tile.position)
        tile.owner_id = player.player_id
        tile.building_level = 1
        built_levels = [1]  # Cam co

        while tile.building_level < 4:
            next_level = tile.building_level + 1
            build_cost = building.get(str(next_level), {}).get("build", 0) * BASE_UNIT
            if not player.can_afford(build_cost):
                break
            player.cash -= build_cost
            total_cost += build_cost
            tile.building_level = next_level
            built_levels.append(next_level)

        event = GameEvent(
            event_type=EventType.PROPERTY_PURCHASED,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "property": f"City_{tile.opt}",
                "price": total_cost,
                "level": tile.building_level,
                "built_levels": built_levels,
            }
        )
        self.event_bus.publish(event)
        return [event]

    def _check_instant_win(self, player: Player) -> str | None:
        """Kiểm tra điều kiện win tức thì sau lượt của player.

        Các điều kiện (theo thứ tự):
        1. Sở hữu 4+ ô Resort → reason="4_resorts"
        2. Hoàn thành 3+ nhóm màu (sở hữu toàn bộ CITY trong 3+ màu) → reason="3_color_groups"
        3. Sở hữu toàn bộ CITY trong 1 hàng (pos 1-8 / 9-16 / 17-24 / 25-32) → reason="own_row"

        Returns:
            Chuỗi reason nếu thắng, None nếu chưa.
        """
        owned = set(player.owned_properties)

        # Condition 1: Sở hữu tất cả Resort trên bàn
        total_resorts = sum(1 for t in self.board.board if t.space_id == SpaceId.RESORT)
        resort_count = sum(
            1 for pos in owned
            if self.board.get_tile(pos).space_id == SpaceId.RESORT
        )
        if total_resorts > 0 and resort_count >= total_resorts:
            return "all_resorts"

        # Condition 2: 3+ complete color groups
        map_cfg = self.board.land_config.get("1", {})
        color_to_opts: dict[int, set] = {}
        for opt_str, cfg in map_cfg.items():
            color = cfg.get("color")
            if color is not None:
                color_to_opts.setdefault(color, set()).add(int(opt_str))

        owned_city_opts = {
            self.board.get_tile(pos).opt
            for pos in owned
            if self.board.get_tile(pos).space_id == SpaceId.CITY
        }
        complete_colors = sum(
            1 for opts in color_to_opts.values()
            if opts.issubset(owned_city_opts)
        )
        if complete_colors >= 3:
            return "3_color_groups"

        # Condition 3: own all CITY + RESORT in any 1 row (rows: 1-8, 9-16, 17-24, 25-32)
        for row_start in (1, 9, 17, 25):
            row_props = [
                pos for pos in range(row_start, row_start + 8)
                if self.board.get_tile(pos).space_id in (SpaceId.CITY, SpaceId.RESORT)
            ]
            if row_props and all(pos in owned for pos in row_props):
                return "own_row"

        return None

    def _get_total_wealth(self, player: Player) -> float:
        """Tính tổng tài sản: cash + giá trị công trình đã xây.

        Dùng để xác định người thắng khi hết 25 turn.
        """
        total = player.cash
        map_cfg = self.board.land_config.get("1", {})
        resort_cfg = self.board.get_resort_config() or {}

        for pos in player.owned_properties:
            tile = self.board.get_tile(pos)
            if tile.space_id == SpaceId.CITY:
                building = map_cfg.get(str(tile.opt), {}).get("building", {})
                for lv in range(1, tile.building_level + 1):
                    total += building.get(str(lv), {}).get("build", 0) * BASE_UNIT
            elif tile.space_id == SpaceId.RESORT:
                total += resort_cfg.get("initCost", 0) * BASE_UNIT

        return total

    def _get_winner(self) -> str | None:
        """Get player_id of winner (highest total wealth among non-bankrupt).

        Tổng tài sản = cash + giá trị công trình đã xây.

        Returns:
            Player ID of winner, or None if no active players.
        """
        active = [p for p in self.players if not p.is_bankrupt]
        if not active:
            return None
        return max(active, key=lambda p: self._get_total_wealth(p)).player_id

    @property
    def winner(self) -> str | None:
        """Get the winner (only valid after game over)."""
        return self._winner