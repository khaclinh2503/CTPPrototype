"""Tests cho GameStrategy MiniGame 3-round đỏ đen."""

import random
import pytest
from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.constants import STARTING_CASH


@pytest.fixture
def space_positions():
    """Board với GAME tile tại position 3."""
    positions = {}
    for i in range(1, 33):
        if i == 1:
            positions[str(i)] = {"spaceId": 7, "opt": 0}  # START
        elif i == 3:
            positions[str(i)] = {"spaceId": 4, "opt": 0}  # GAME
        else:
            positions[str(i)] = {"spaceId": 3, "opt": i - 1}  # CITY
    return positions


@pytest.fixture
def board(space_positions):
    return Board(
        space_positions=space_positions,
        land_config={"1": {}},
        resort_config=None,
        festival_config=None,
    )


@pytest.fixture
def event_bus():
    return EventBus()


class TestMiniGame:
    """Tests cho GameStrategy MiniGame."""

    def test_minigame_win_round1(self, board, event_bus):
        """Seed random để thắng round 1 -> player nhận x2 bet, stub dừng sau round 1."""
        from ctp.tiles.game import GameStrategy

        strategy = GameStrategy()
        player = Player(player_id="P", cash=STARTING_CASH)
        tile = board.get_tile(3)

        initial_cash = player.cash
        # bet = costOptions[0] * STARTING_CASH = 0.05 * 1_000_000 = 50_000
        bet = int(0.05 * STARTING_CASH)

        # Seed để random.random() < 0.5 (win)
        random.seed(0)  # seed 0: random.random() = 0.844... > 0.5 -> LOSE
        # Cần tìm seed thắng
        # Thử seed 1: random.random() với seed 1
        random.seed(1)
        first_val = random.random()
        win_seed = 1 if first_val < 0.5 else None

        # Tìm seed cho win
        for seed in range(100):
            random.seed(seed)
            val = random.random()
            if val < 0.5:
                win_seed = seed
                break

        assert win_seed is not None, "Không tìm được win seed"

        random.seed(win_seed)
        player2 = Player(player_id="P2", cash=STARTING_CASH)
        events = strategy.on_land(player2, tile, board, event_bus)

        # Thắng round 1: nhận x2 bet
        assert player2.cash == STARTING_CASH - bet + 2 * bet  # = STARTING_CASH + bet
        assert len(events) == 1
        assert events[0].event_type == EventType.MINIGAME_RESULT
        assert events[0].data["won"] is True
        assert events[0].data["result"] == 2 * bet  # winnings = bet * 2^1

    def test_minigame_lose_round1(self, board, event_bus):
        """Seed random để thua round 1 -> player mất bet."""
        from ctp.tiles.game import GameStrategy

        strategy = GameStrategy()
        player = Player(player_id="P", cash=STARTING_CASH)
        tile = board.get_tile(3)

        bet = int(0.05 * STARTING_CASH)

        # Tìm seed thua (random.random() >= 0.5)
        lose_seed = None
        for seed in range(100):
            random.seed(seed)
            val = random.random()
            if val >= 0.5:
                lose_seed = seed
                break

        assert lose_seed is not None, "Không tìm được lose seed"

        random.seed(lose_seed)
        events = strategy.on_land(player, tile, board, event_bus)

        assert player.cash == STARTING_CASH - bet  # mất bet
        assert len(events) == 1
        assert events[0].event_type == EventType.MINIGAME_RESULT
        assert events[0].data["won"] is False
        assert events[0].data["result"] == -bet

    def test_minigame_bet_equals_min_cost_option(self, board, event_bus):
        """Bet = costOptions[0] * STARTING_CASH = 50_000."""
        from ctp.tiles.game import GameStrategy

        strategy = GameStrategy()
        player = Player(player_id="P", cash=STARTING_CASH)
        tile = board.get_tile(3)

        initial_cash = player.cash
        expected_bet = int(0.05 * STARTING_CASH)  # 50_000

        random.seed(42)
        events = strategy.on_land(player, tile, board, event_bus)

        assert len(events) == 1
        assert events[0].data["bet"] == expected_bet

    def test_minigame_event_contains_rounds_and_result(self, board, event_bus):
        """Event MINIGAME_RESULT chứa rounds_played, bet, result, won."""
        from ctp.tiles.game import GameStrategy

        strategy = GameStrategy()
        player = Player(player_id="P", cash=STARTING_CASH)
        tile = board.get_tile(3)

        random.seed(42)
        events = strategy.on_land(player, tile, board, event_bus)

        assert len(events) == 1
        data = events[0].data
        assert "rounds_played" in data
        assert "bet" in data
        assert "result" in data
        assert "won" in data
        assert data["rounds_played"] == 1  # stub: dừng sau round 1

    def test_minigame_event_published_to_bus(self, board, event_bus):
        """MINIGAME_RESULT event được publish lên event_bus."""
        from ctp.tiles.game import GameStrategy

        strategy = GameStrategy()
        player = Player(player_id="P", cash=STARTING_CASH)
        tile = board.get_tile(3)

        random.seed(42)
        strategy.on_land(player, tile, board, event_bus)

        mg_events = event_bus.get_events(EventType.MINIGAME_RESULT)
        assert len(mg_events) == 1
