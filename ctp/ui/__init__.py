"""CTP Pygame UI package.

Entry point: run_pygame(config_loader, num_players, max_turns)
"""
from __future__ import annotations


def run_pygame(config_loader, num_players: int = 4, max_turns: int | None = None) -> None:
    """Launch the Pygame window and run the game loop.

    Imports GameView here (not at module level) to keep pygame import
    isolated — headless mode never touches pygame at all.

    Args:
        config_loader: Loaded ConfigLoader instance.
        num_players: Number of players (2-4).
        max_turns: Override max turns (uses config default if None).
    """
    from ctp.ui.game_view import GameView
    view = GameView(config_loader, num_players, max_turns)
    view.run()
