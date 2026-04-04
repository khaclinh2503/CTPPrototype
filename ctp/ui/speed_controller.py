"""SpeedController — background daemon thread for game loop.

Runs GameController.step() with configurable delays.
Speed levels: PAUSED / 1x (800ms).

Threading design: This class owns the background thread. GameView owns
the threading.Lock for shared UI state. SpeedController receives the
lock only so it can notify GameView of game-over (if needed in future).
"""
from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctp.controller import GameController


# Delay in seconds between step() calls per speed level.
# None = PAUSED (thread blocks on _pause_event.wait()).
_DELAYS: dict[str, float | None] = {
    "pause": None,
    "1x":   0.8,
}

# Display strings for UI speed indicator (per UI-SPEC Copywriting Contract).
SPEED_LABELS: dict[str, str] = {
    "pause": "[PAUSED]",
    "1x":    "[1x]",
}


class SpeedController:
    """Manages the background game thread and speed settings.

    Usage:
        sc = SpeedController(controller)
        sc.start()           # must be called after EventBus subscriptions
        sc.toggle_pause()    # Space key
        sc.set_speed("5x")  # 2 key
        sc.is_running()      # False when game is over
    """

    def __init__(self, controller: "GameController") -> None:
        self._controller = controller
        self._speed: str = "1x"          # default speed on start
        self._prev_speed: str = "1x"     # for Space toggle: resume to this speed
        self._pause_event = threading.Event()
        self._pause_event.set()          # start unpaused
        self._dice_barrier = threading.Event()
        self._dice_barrier.set()         # not blocking by default
        self._thread = threading.Thread(target=self._run, daemon=True, name="GameThread")
        self._game_over = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background game thread. Call AFTER EventBus subscriptions."""
        self._thread.start()

    def toggle_pause(self) -> None:
        """Toggle between PAUSED and the previous active speed (Space key).

        If currently running -> PAUSED.
        If currently PAUSED -> resume at _prev_speed (default 1x).
        """
        if self._speed == "pause":
            # Resume
            self._speed = self._prev_speed
            self._pause_event.set()
        else:
            # Pause
            self._prev_speed = self._speed
            self._speed = "pause"
            self._pause_event.clear()

    def set_speed(self, speed: str) -> None:
        """Set speed to one of: '1x', '5x', 'max'.

        Also clears the pause state if currently paused.

        Args:
            speed: Speed level key — must be in _DELAYS.
        """
        if speed not in _DELAYS:
            raise ValueError(f"Unknown speed level: {speed!r}. Valid: {list(_DELAYS)}")
        self._speed = speed
        self._prev_speed = speed
        self._pause_event.set()   # resume if paused

    @property
    def speed(self) -> str:
        """Current speed level key (e.g. 'pause', '1x', '5x', 'max')."""
        return self._speed

    @property
    def speed_label(self) -> str:
        """Display string for speed indicator (e.g. '[PAUSED]', '[1x]')."""
        return SPEED_LABELS.get(self._speed, self._speed)

    def wait_for_dice_anim(self) -> None:
        """Block the game loop until resume_after_dice() is called.

        Called from the event handler (background thread) when a DICE_ROLL fires.
        Blocks AFTER the current step() completes, before the next step().
        """
        self._dice_barrier.clear()

    def resume_after_dice(self) -> None:
        """Release the dice animation barrier. Called from the render loop (main thread)."""
        self._dice_barrier.set()

    def is_running(self) -> bool:
        """True if background thread is alive and game not over."""
        return self._thread.is_alive() and not self._game_over

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Background thread: loop until game over."""
        while not self._controller.is_game_over():
            self._pause_event.wait()          # blocks indefinitely when paused
            self._dice_barrier.wait()         # blocks during dice animation
            if self._controller.is_game_over():
                break
            self._controller.step()
            delay = _DELAYS.get(self._speed)
            if delay is not None and delay > 0.0:
                time.sleep(delay)
        self._game_over = True
