"""GameController FSM for CTP game."""

from enum import Enum, auto
from typing import Callable
import random
from ctp.core.models import Player
from ctp.core.board import Board, SpaceId, Tile
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.constants import BASE_UNIT
from ctp.tiles.registry import TileRegistry


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

    def _do_roll(self) -> list[GameEvent]:
        """Roll dice and transition to MOVE.

        Returns:
            Empty list (dice event is published).
        """
        if self.current_player.pending_travel:
            self._resolve_travel_attempt()
            self.phase = TurnPhase.END_TURN
            return []

        if self.current_player.prison_turns_remaining > 0:
            result = self._resolve_prison_attempt()
            if result == 'skip':
                return []   # bỏ lượt, phase đã set END_TURN trong helper
            if result == 'endturn':
                # Đổ ra đôi trong tù → thoát nhưng không di chuyển lượt này
                self.phase = TurnPhase.END_TURN
                return []
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

        dice = self.roll_dice()
        self._rolled_doubles = (dice[0] == dice[1])

        if self._rolled_doubles:
            self._doubles_streak += 1
        else:
            self._doubles_streak = 0

        self.event_bus.publish(GameEvent(
            event_type=EventType.DICE_ROLL,
            player_id=self.current_player.player_id,
            data={"dice": dice, "total": sum(dice), "doubles": self._rolled_doubles,
                  "doubles_streak": self._doubles_streak}
        ))

        # Đổ đôi 3 lần liên tiếp → vào tù ngay, bỏ lượt
        if self._doubles_streak >= 3:
            self._doubles_streak = 0
            self._rolled_doubles = False
            self.current_player.move_to(9)  # ô tù = position 9
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

    def _resolve_prison_attempt(self) -> str:
        """Xử lý lượt của người chơi đang ở trong tù.

        2 lựa chọn (headless: trả tiền nếu đủ, không đủ thì đổ xúc xắc):
          A. Trả phí → ra tù, roll mới để đi bình thường  → return 'play'
          B. Đổ xúc xắc:
             - Ra đôi → ra tù, kết thúc lượt (không di chuyển) → return 'endturn'
             - Không ra đôi → ngồi tiếp (decrement), hoặc hết hạn thì ra + play → return 'skip' / 'play'

        Return values:
          'play'    – đã ra tù, _current_dice đã set, tiếp tục chơi bình thường
          'endturn' – đổ ra đôi, thoát tù nhưng kết thúc lượt ngay (không di chuyển)
          'skip'    – không ra đôi, vẫn trong tù, bỏ lượt
        """
        prison_cfg = self.board.get_prison_config() or {}
        escape_fee = int(prison_cfg.get("escapeCostRate", 0.1) * self._starting_cash)
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
        dice = self.roll_dice()
        is_doubles = (dice[0] == dice[1])
        self.event_bus.publish(GameEvent(
            event_type=EventType.DICE_ROLL,
            player_id=pid,
            data={"dice": dice, "total": sum(dice), "doubles": is_doubles, "prison_roll": True}
        ))

        if is_doubles:
            # Ra đôi → thoát tù, nhưng kết thúc lượt ngay (không đi)
            self.current_player.exit_prison()
            self.event_bus.publish(GameEvent(
                event_type=EventType.PRISON_EXITED,
                player_id=pid,
                data={"reason": "doubles"}
            ))
            self._rolled_doubles = False
            self._doubles_streak = 0
            return 'endturn'

        # Không ra đôi → ngồi tiếp
        self.current_player.decrement_prison_turn()
        if self.current_player.prison_turns_remaining == 0:
            # Hết hạn tù → tự động ra, roll để di chuyển
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

        Stub AI: chấp nhận đi nếu đủ tiền trả phí.
        - Chấp nhận + đủ tiền: trả phí, teleport tới đích ngẫu nhiên (CITY/RESORT).
        - Từ chối hoặc không đủ tiền: không di chuyển.
        - Cả 2 trường hợp: xóa pending_travel, kết thúc lượt.
        """
        import random
        from ctp.core.constants import STARTING_CASH
        from ctp.core.board import SpaceId

        player = self.current_player
        player.pending_travel = False

        travel_cfg = {}
        board_cfg = getattr(self.board, '_raw_travel_config', None)
        travel_cost_rate = travel_cfg.get("travelCostRate", 0.02) if travel_cfg else 0.02
        travel_fee = int(travel_cost_rate * STARTING_CASH)

        # Chọn đích ngẫu nhiên trong CITY và RESORT
        candidates = [
            t for t in self.board.board
            if t.space_id in (SpaceId.CITY, SpaceId.RESORT)
            and t.position != player.position
        ]
        if not candidates:
            return

        destination = random.choice(candidates)

        # Stub AI: đi nếu đủ tiền
        should_go = player.can_afford(travel_fee)

        if should_go:
            player.cash -= travel_fee
            old_pos = player.position
            player.position = destination.position
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_MOVE,
                player_id=player.player_id,
                data={
                    "old_pos": old_pos,
                    "new_pos": destination.position,
                    "travel_fee": travel_fee,
                    "reason": "travel_accepted",
                }
            ))
        else:
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_MOVE,
                player_id=player.player_id,
                data={"reason": "travel_declined", "travel_fee": travel_fee}
            ))

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
                data={position: elevated_pos}
            ))
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_MOVE,
                player_id=self.current_player.player_id,
                data={
                    old_pos: old_pos,
                    new_pos: elevated_pos,
                    passed_start: self._passed_start,
                    blocked_by_elevated: True,
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
                "passed_start": self._passed_start
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

        strategy = TileRegistry.resolve(tile.space_id)
        events = strategy.on_land(
            self.current_player, tile, self.board, self.event_bus,
            players=self.players
        )

        if was_unowned:
            # Lan dau: mua + xay ngay (khong tao upgrade eligible -> khong co [Nang cap])
            buy_events = self._try_buy_property(self.current_player, tile)
            events.extend(buy_events)
        elif is_own:
            # Lan 2+: da co nha san, moi duoc nang cap
            max_lv = 5 if tile.building_level >= 4 else 4
            self._upgrade_eligible.setdefault(tile.position, max_lv)

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
            events = resolve_bankruptcy(
                self.current_player,
                self.board,
                self.event_bus
            )

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
        1. Only 1 player còn tiền (non-bankrupt) → reason="last_player_standing"
        2. Reached max_turns (25) → reason="max_turns"

        Returns:
            Empty list (game ended events are published separately).
        """
        self.current_player.turns_taken += 1  # hoàn thành 1 lượt

        self.event_bus.publish(GameEvent(
            event_type=EventType.TURN_ENDED,
            player_id=self.current_player.player_id,
            data={"turn": self.current_turn}
        ))

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

    def _get_winner(self) -> str | None:
        """Get player_id of winner (highest cash among non-bankrupt).

        Returns:
            Player ID of winner, or None if no active players.
        """
        active = [p for p in self.players if not p.is_bankrupt]
        if not active:
            return None
        return max(active, key=lambda p: p.cash).player_id

    @property
    def winner(self) -> str | None:
        """Get the winner (only valid after game over)."""
        return self._winner