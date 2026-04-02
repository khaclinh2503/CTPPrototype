"""GameStrategy — MiniGame 3-round đỏ đen."""

import random
from ctp.tiles.base import TileStrategy
from ctp.core.models import Player
from ctp.core.board import Tile, Board
from ctp.core.constants import STARTING_CASH
from ctp.core.events import GameEvent, EventType


class GameStrategy(TileStrategy):
    """MiniGame 3-round đỏ đen (per D-09 -> D-12).

    Config từ Board.json MiniGame:
    - costOptions: [0.05, 0.1, 0.15] — tỷ lệ cược
    - maxChance: 3 — số round tối đa
    - increaseRate: 2 — hệ số nhân mỗi round

    Stub AI (per D-12): luôn chọn mức cược tối thiểu (costOptions[0]),
    dừng sau round 1 nếu thắng.
    """

    DEFAULT_COST_OPTIONS = [0.05, 0.1, 0.15]
    DEFAULT_MAX_CHANCE = 3
    DEFAULT_INCREASE_RATE = 2

    def on_land(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player landing on a mini-game tile.

        Flow (per D-09, D-10, D-11):
        - Round 1 bắt buộc: trả bet, tung coin (50/50)
        - Thắng: nhận bet * increase_rate^round_num
        - Thua: mất bet, dừng
        - Stub AI: dừng sau round 1 (không tiếp tục nếu thắng)

        Args:
            player: Player đang chơi minigame.
            tile: GAME tile.
            board: Game board.
            event_bus: Event bus.
            players: All players (not used for minigame).

        Returns:
            List with one MINIGAME_RESULT event.
        """
        events = []

        cost_options = self.DEFAULT_COST_OPTIONS
        increase_rate = self.DEFAULT_INCREASE_RATE

        # Stub AI: luôn chọn mức cược tối thiểu (per D-12)
        bet_index = 0
        current_bet = int(cost_options[bet_index] * STARTING_CASH)  # 50_000

        # Round 1 bắt buộc (per D-09)
        player.cash -= current_bet
        rounds_played = 1

        # 50% win (per D-10)
        won = random.random() < 0.5
        if won:
            # Thắng: x(increase_rate^round_num) = x2 ở round 1
            multiplier = increase_rate ** 1  # round 1 = x2
            winnings = current_bet * multiplier
            player.cash += winnings
            total_result = winnings
        else:
            # Thua: mất cược
            total_result = -current_bet

        # Stub: dừng sau round 1 (per D-12)
        # (Nếu không stub, có thể tiếp tục round 2, 3)

        events.append(GameEvent(
            event_type=EventType.MINIGAME_RESULT,
            player_id=player.player_id,
            data={
                "position": tile.position,
                "rounds_played": rounds_played,
                "bet": current_bet,
                "result": total_result,
                "won": won,
            }
        ))
        event_bus.publish(events[-1])
        return events

    def on_pass(self, player: Player, tile: Tile, board: Board, event_bus,
                players: list | None = None) -> list[GameEvent]:
        """Handle player passing a mini-game tile.

        Returns:
            Empty list (no pass effect).
        """
        return []
