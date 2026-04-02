"""GameController FSM for CTP game."""

from enum import Enum, auto
import random
from ctp.core.models import Player
from ctp.core.board import Board, SpaceId
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.tiles.registry import TileRegistry


class TurnPhase(Enum):
    """FSM states for each turn.

    The game flows through these phases in order:
    1. ROLL - Roll dice (2d6)
    2. MOVE - Move player based on dice roll
    3. RESOLVE_TILE - Apply tile effect
    4. CHECK_BANKRUPTCY - Check if player is bankrupt
    5. END_TURN - Advance to next player
    """

    ROLL = auto()
    MOVE = auto()
    RESOLVE_TILE = auto()
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
    ):
        """Initialize the game controller.

        Args:
            board: The game board.
            players: List of players (2-4).
            max_turns: Maximum number of turns before game ends.
            event_bus: Event bus for publishing game events.
        """
        self.board = board
        self.players = players
        self.max_turns = max_turns
        self.event_bus = event_bus
        self.phase = TurnPhase.ROLL
        self.current_player_index = 0
        self.current_turn = 1
        self._current_dice: tuple[int, int] = (0, 0)
        self._passed_start = False
        self._game_over = False
        self._winner: str | None = None

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
            case TurnPhase.CHECK_BANKRUPTCY:
                return self._do_check_bankruptcy()
            case TurnPhase.END_TURN:
                return self._do_end_turn()

    def _do_roll(self) -> list[GameEvent]:
        """Roll dice and transition to MOVE.

        Returns:
            Empty list (dice event is published).
        """
        if self.current_player.prison_turns_remaining > 0:
            # In prison - skip roll, move to END_TURN
            self.event_bus.publish(GameEvent(
                event_type=EventType.TURN_STARTED,
                player_id=self.current_player.player_id,
                data={"turn": self.current_turn, "reason": "in_prison"}
            ))
            self.phase = TurnPhase.END_TURN
            return []

        dice = self.roll_dice()
        self.event_bus.publish(GameEvent(
            event_type=EventType.DICE_ROLL,
            player_id=self.current_player.player_id,
            data={"dice": dice, "total": sum(dice)}
        ))

        self.event_bus.publish(GameEvent(
            event_type=EventType.TURN_STARTED,
            player_id=self.current_player.player_id,
            data={"turn": self.current_turn}
        ))

        self.phase = TurnPhase.MOVE
        return []

    def _do_move(self) -> list[GameEvent]:
        """Move player and check for passing Start. Transition to RESOLVE_TILE.

        Returns:
            List of events from moving (including passing Start bonus).
        """
        dice_total = sum(self._current_dice)
        old_pos = self.current_player.position
        new_pos = old_pos + dice_total

        # Check if passing Start (position wraps from >32 to <=32)
        self._passed_start = new_pos > 32

        # Apply passing bonus via StartStrategy on_pass
        start_tile = self.board.get_tile(1)
        strategy = TileRegistry.resolve(SpaceId.START)
        events = []

        if self._passed_start:
            events = strategy.on_pass(self.current_player, start_tile, self.board, self.event_bus)

        # Update position with wrapping (1-indexed)
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

        # Decrement prison turns if player was in prison
        if self.current_player.prison_turns_remaining > 0:
            self.current_player.prison_turns_remaining -= 1
            if self.current_player.prison_turns_remaining == 0:
                self.event_bus.publish(GameEvent(
                    event_type=EventType.PRISON_EXITED,
                    player_id=self.current_player.player_id,
                    data={}
                ))

        self.phase = TurnPhase.RESOLVE_TILE
        return events

    def _do_resolve_tile(self) -> list[GameEvent]:
        """Apply tile effect. Transition to CHECK_BANKRUPTCY.

        Returns:
            List of events from tile resolution.
        """
        tile = self.board.get_tile(self.current_player.position)
        strategy = TileRegistry.resolve(tile.space_id)
        events = strategy.on_land(self.current_player, tile, self.board, self.event_bus)

        self.event_bus.publish(GameEvent(
            event_type=EventType.TILE_LANDED,
            player_id=self.current_player.player_id,
            data={
                "position": tile.position,
                "tile_type": tile.space_id.name,
                "tile_id": tile.space_id
            }
        ))

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

        self.phase = TurnPhase.END_TURN
        return events

    def _do_end_turn(self) -> list[GameEvent]:
        """Advance to next non-bankrupt player. Check terminal conditions.

        Returns:
            Empty list (game ended events are published separately).
        """
        self.event_bus.publish(GameEvent(
            event_type=EventType.TURN_ENDED,
            player_id=self.current_player.player_id,
            data={"turn": self.current_turn}
        ))

        # Check terminal conditions
        if self.is_game_over():
            self._game_over = True
            self._winner = self._get_winner()
            self.event_bus.publish(GameEvent(
                event_type=EventType.GAME_ENDED,
                data={
                    "winner": self._winner,
                    "turns": self.current_turn,
                    "reason": "terminal_condition"
                }
            ))
            return []

        # Move to next non-bankrupt player
        self._advance_to_next_player()

        # Check if we've reached max_turns
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
        - Only 1 non-bankrupt player remains
        - Current turn >= max_turns

        Returns:
            True if game is over, False otherwise.
        """
        # Check if only 1 non-bankrupt player remains
        active_players = [p for p in self.players if not p.is_bankrupt]
        if len(active_players) <= 1:
            return True

        # Check max_turns
        if self.current_turn >= self.max_turns:
            return True

        return False

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