"""GameView — central coordinator for the Pygame UI.

Responsibilities:
    1. Build the game objects (Board, Players, EventBus, GameController) using
       the same factory pattern as main.run_headless().
    2. Subscribe EventBus handlers BEFORE starting the background thread.
       All handlers run in the background thread context (Pitfall 2 from RESEARCH).
       Every handler MUST acquire self._lock before writing self._ui_state.
    3. Run the Pygame render loop on the main thread at 60fps.
    4. Relay keyboard events to SpeedController.

Threading invariant:
    - Background thread: GameController.step() + EventBus handlers (write _ui_state)
    - Main thread: pygame.event.get() + render (read _ui_state snapshot under lock)
    - Lock: acquired for entire handler execution; acquired for snapshot copy in render
"""
from __future__ import annotations

import threading
import random
import time
import pygame
from collections import deque
from typing import TYPE_CHECKING

from ctp.core.events import EventBus, GameEvent, EventType
from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.controller import GameController
from ctp.ui.board_renderer import BoardRenderer
from ctp.ui.info_panel import InfoPanel, PANEL_X, LOG_Y, LOG_H
from ctp.ui.speed_controller import SpeedController

import ctp.tiles   # register tile strategies (same as main.py)

if TYPE_CHECKING:
    from ctp.config import ConfigLoader

# Window settings (per UI-SPEC Window section)
_WIN_W  = 1280
_WIN_H  = 720
_FPS    = 60
_TITLE  = "CTP \u2014 Co Ty Phu AI Simulator"
_BG     = (30, 30, 30)

# Walk animation: seconds between each tile step (70ms → max 12 tiles = 840ms < 800ms turn delay)
_ANIM_STEP_S = 0.07


def _build_walk_path(old_pos: int, new_pos: int) -> list[int]:
    """Return clockwise tile positions from old_pos (exclusive) to new_pos (inclusive)."""
    path: list[int] = []
    cur = old_pos
    while cur != new_pos:
        cur = (cur % 32) + 1
        path.append(cur)
    return path


class GameView:
    """Pygame window + EventBus subscriber + render loop coordinator."""

    def __init__(
        self,
        config_loader: "ConfigLoader",
        num_players: int = 4,
        max_turns: int | None = None,
    ) -> None:
        # -- Build game objects (same pattern as run_headless) ---
        from main import create_board, create_players
        self._board = create_board(config_loader)
        self._players = create_players(config_loader, num_players)
        self._event_bus = EventBus()

        # Random 3 golden tiles (CITY or RESORT) - same as run_headless
        property_tiles = [
            t for t in self._board.board
            if t.space_id in (SpaceId.CITY, SpaceId.RESORT)
        ]
        golden_tiles = random.sample(property_tiles, min(3, len(property_tiles)))
        for t in golden_tiles:
            t.is_golden = True

        game_max_turns = (
            max_turns if max_turns is not None else config_loader.max_turns
        )
        self._controller = GameController(
            board=self._board,
            players=self._players,
            max_turns=game_max_turns,
            event_bus=self._event_bus,
            starting_cash=config_loader.starting_cash,
        )

        # -- Shared UI state ---
        self._lock = threading.Lock()
        self._ui_state: dict = {
            p.player_id: {
                "cash":         p.cash,
                "total_assets": p.cash,   # no properties yet at start
                "position":     p.position,
                "is_bankrupt":  p.is_bankrupt,
            }
            for p in self._players
        }
        self._ui_state["board_ownership"]  = {}
        self._ui_state["event_log"]        = deque(maxlen=200)
        self._ui_state["active_player_id"] = self._players[0].player_id
        self._ui_state["speed"]            = "1x"
        self._ui_state["log_scroll"]       = 0
        self._game_over_flag               = False

        # Walk animation state (main-thread only — no lock needed)
        self._anim_step_time: dict[str, float] = {}   # pid → time of last tile advance

        # Dice roll animation state (main-thread only — no lock needed)
        self._dice_display: list[int] | None = None    # current displayed values, or None
        self._dice_update_t: float = 0.0               # last time display was randomized

        # -- Subscribe EventBus BEFORE thread starts ---
        self._setup_subscriptions()

        # -- Renderers ---
        self._board_renderer = BoardRenderer()
        self._info_panel     = InfoPanel()

        # -- Speed controller ---
        self._speed_ctrl = SpeedController(self._controller)

        # Player ID order (for panel)
        self._player_ids = [p.player_id for p in self._players]

    # ------------------------------------------------------------------
    # Public: run() is called by ctp/ui/__init__.py run_pygame()
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Initialise Pygame, publish GAME_STARTED, start background thread, run render loop."""
        pygame.init()
        screen = pygame.display.set_mode((_WIN_W, _WIN_H))
        pygame.display.set_caption(_TITLE)
        clock = pygame.time.Clock()

        # Fonts (pygame.font.SysFont - OS default, no external files)
        font_tile    = pygame.font.SysFont(None, 14)   # tile labels
        font_token   = pygame.font.SysFont(None, 16)   # player tokens
        font_body    = pygame.font.SysFont(None, 18)   # panel body
        font_heading = pygame.font.SysFont(None, 22)   # panel headings / speed
        font_overlay = pygame.font.SysFont(None, 20)   # card overlay text

        _LOG_LINE_H = 16  # must match info_panel._LOG_LINE_H
        _max_log_lines = (LOG_H - 24) // _LOG_LINE_H

        # Publish game start event (same as run_headless)
        self._event_bus.publish(GameEvent(
            event_type=EventType.GAME_STARTED,
            data={"players": [p.player_id for p in self._players]}
        ))

        # Start background thread (after subscriptions - critical ordering)
        self._speed_ctrl.start()

        # -- Render loop ---
        running = True
        while running:
            # Process Pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self._speed_ctrl.toggle_pause()
                    elif event.key == pygame.K_1:
                        self._speed_ctrl.set_speed("1x")
                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    if mx >= PANEL_X and my >= LOG_Y:
                        with self._lock:
                            log_len = len(self._ui_state["event_log"])
                            scroll = self._ui_state.get("log_scroll", 0)
                            # event.y > 0 = scroll up (show older); < 0 = scroll down
                            scroll = max(0, min(scroll - event.y,
                                                max(0, log_len - _max_log_lines)))
                            self._ui_state["log_scroll"] = scroll

            # Advance walk + dice animations (main thread)
            now = time.time()
            with self._lock:
                # Walk animation advance
                for _pid in self._player_ids:
                    pdata = self._ui_state.get(_pid)
                    if not isinstance(pdata, dict):
                        continue
                    anim = pdata.get("anim_path")
                    if anim and now - self._anim_step_time.get(_pid, 0) >= _ANIM_STEP_S:
                        pdata["display_pos"] = anim.pop(0)
                        self._anim_step_time[_pid] = now
                        if not anim:
                            pdata.pop("anim_path",   None)
                            pdata.pop("display_pos", None)

                # Dice animation management
                da = self._ui_state.get("dice_anim")
                if da:
                    elapsed = now - da["started_at"]
                    if elapsed >= da["duration"] + 0.5:
                        # Animation fully done: release game barrier
                        del self._ui_state["dice_anim"]
                        self._dice_display = None
                        self._speed_ctrl.resume_after_dice()
                    elif elapsed >= da["duration"]:
                        # Final phase: show actual values
                        self._dice_display = list(da["final"])
                    else:
                        # Rolling phase: randomise display every 80ms
                        if now - self._dice_update_t >= 0.08:
                            self._dice_display = [
                                random.randint(1, 6),
                                random.randint(1, 6),
                            ]
                            self._dice_update_t = now

            # Update speed + expire card overlay under one lock acquire
            with self._lock:
                self._ui_state["speed"] = self._speed_ctrl.speed
                overlay = self._ui_state.get("card_overlay")
                if overlay and time.time() > overlay.get("expires_at", 0):
                    del self._ui_state["card_overlay"]

            # Snapshot shared state under lock (hold lock minimally)
            with self._lock:
                state_snapshot = {
                    k: dict(v) if isinstance(v, dict) else v
                    for k, v in self._ui_state.items()
                }
                state_snapshot["event_log"] = list(self._ui_state["event_log"])
            # Inject main-thread-only dice display into snapshot
            state_snapshot["dice_display"] = (
                list(self._dice_display) if self._dice_display else None
            )
            state_snapshot["dice_anim_pid"] = (
                self._ui_state.get("dice_anim", {}).get("pid", "")
                if "dice_anim" in self._ui_state else ""
            )

            # Draw
            screen.fill(_BG)
            self._board_renderer.draw(
                screen, self._board, state_snapshot, font_tile, font_token, font_overlay
            )
            self._info_panel.draw(
                screen, state_snapshot, self._player_ids, font_body, font_heading
            )

            # Game over notice in event log (no separate screen - UI-SPEC Copywriting)
            # GAME_ENDED handler already appended the game over line to event_log.

            pygame.display.flip()
            clock.tick(_FPS)

        pygame.quit()
        # Safety: unblock game thread if closed during dice animation
        self._speed_ctrl.resume_after_dice()

    # ------------------------------------------------------------------
    # EventBus subscriptions
    # ------------------------------------------------------------------

    def _setup_subscriptions(self) -> None:
        """Register all EventBus handlers. MUST be called before SpeedController.start()."""
        relevant_types = [
            EventType.TURN_STARTED,
            EventType.TURN_ENDED,
            EventType.PLAYER_MOVE,
            EventType.TILE_LANDED,
            EventType.DICE_ROLL,
            EventType.PROPERTY_PURCHASED,
            EventType.PROPERTY_ACQUIRED,
            EventType.PROPERTY_UPGRADED,
            EventType.PROPERTY_SOLD,
            EventType.RENT_PAID,
            EventType.TAX_PAID,
            EventType.BONUS_RECEIVED,
            EventType.PLAYER_BANKRUPT,
            EventType.GAME_ENDED,
            EventType.CARD_DRAWN,
            EventType.PRISON_ENTERED,
            EventType.PRISON_EXITED,
            EventType.FESTIVAL_UPDATED,
            EventType.MINIGAME_RESULT,
            EventType.RENT_OWED,
            EventType.DEBT_SETTLED,
        ]
        for et in relevant_types:
            self._event_bus.subscribe(et, self._on_event)

    def _on_event(self, event: GameEvent) -> None:
        """Handle any game event - update _ui_state under lock.

        Runs in BACKGROUND THREAD context (EventBus dispatches synchronously
        inside controller.step()). MUST acquire _lock before writing.
        """
        with self._lock:
            pid = event.player_id
            et  = event.event_type

            # -- Update player position ---
            if et == EventType.PLAYER_MOVE:
                old_pos  = event.data.get("old_pos")
                new_pos  = event.data.get("new_pos")
                move_type = int(event.data.get("move_type", 2))

                if pid and pid in self._ui_state and new_pos is not None:
                    # Always update the authoritative position immediately
                    self._ui_state[pid]["position"] = new_pos

                    if move_type == 1 and old_pos is not None:
                        # Walk: queue tile-by-tile animation path
                        path = _build_walk_path(old_pos, new_pos)
                        existing = self._ui_state[pid].get("anim_path")
                        if existing is not None:
                            # Extend ongoing animation
                            existing.extend(path)
                        else:
                            self._ui_state[pid]["display_pos"] = old_pos
                            self._ui_state[pid]["anim_path"]   = path
                        self._ui_state["event_log"].append(
                            f"{pid} di chuyen: o {old_pos} -> o {new_pos}"
                        )
                    else:
                        # Teleport: clear any pending animation, jump instantly
                        self._ui_state[pid].pop("display_pos", None)
                        self._ui_state[pid].pop("anim_path", None)
                        if old_pos is not None:
                            self._ui_state["event_log"].append(
                                f"{pid} teleport: o {old_pos} -> o {new_pos}"
                            )

            # -- Update active player ---
            elif et == EventType.TURN_STARTED:
                if pid:
                    self._ui_state["active_player_id"] = pid
                    turn = event.data.get("turn", "?")
                    self._ui_state["event_log"].append(f"Turn {turn}: {pid}")
                    # Refresh cash from player object (safe: background thread context)
                    self._refresh_player_state(pid)

            # -- Refresh after any money-changing event ---
            elif et in (
                EventType.TURN_ENDED,
                EventType.RENT_PAID,
                EventType.TAX_PAID,
                EventType.BONUS_RECEIVED,
                EventType.PROPERTY_PURCHASED,
                EventType.PROPERTY_ACQUIRED,
                EventType.PROPERTY_UPGRADED,
                EventType.PROPERTY_SOLD,
                EventType.DEBT_SETTLED,
            ):
                # Refresh state for all involved players
                affected = set()
                if pid:
                    affected.add(pid)
                # Also refresh recipient if any (e.g. RENT_PAID recipient)
                recipient = event.data.get("recipient") or event.data.get("creditor")
                if recipient:
                    affected.add(recipient)
                for p in affected:
                    if p in self._ui_state:
                        self._refresh_player_state(p)

                # Update board_ownership on property events
                if et in (EventType.PROPERTY_PURCHASED, EventType.PROPERTY_ACQUIRED):
                    pos = event.data.get("position")
                    if pos is not None and pid:
                        self._ui_state["board_ownership"][pos] = pid
                elif et == EventType.PROPERTY_SOLD:
                    pos = event.data.get("position")
                    if pos is not None:
                        self._ui_state["board_ownership"].pop(pos, None)

                # Event log for key economic events
                if et == EventType.RENT_PAID:
                    amount = event.data.get("amount", 0)
                    recipient = event.data.get("recipient", "?")
                    pos = event.data.get("position", "?")
                    self._ui_state["event_log"].append(
                        f"{pid} tra thue ${int(amount):,} cho {recipient} (o{pos})"
                    )
                elif et == EventType.PROPERTY_PURCHASED:
                    pos = event.data.get("position", "?")
                    price = event.data.get("price", 0)
                    self._ui_state["event_log"].append(
                        f"{pid} mua dat o{pos} ${int(price):,}"
                    )
                elif et == EventType.PROPERTY_ACQUIRED:
                    pos = event.data.get("position", "?")
                    from_p = event.data.get("from_player", "?")
                    self._ui_state["event_log"].append(
                        f"{pid} cuop o{pos} tu {from_p}"
                    )

            # -- Bankrupt ---
            elif et == EventType.PLAYER_BANKRUPT:
                if pid and pid in self._ui_state:
                    self._ui_state[pid]["is_bankrupt"] = True
                    self._ui_state[pid].pop("display_pos", None)
                    self._ui_state[pid].pop("anim_path",   None)
                    self._ui_state["event_log"].append(f"*** {pid} PHA SAN ***")

            # -- Game ended ---
            elif et == EventType.GAME_ENDED:
                turns = event.data.get("turns", "?")
                self._ui_state["event_log"].append(
                    f"GAME OVER \u2014 Con {turns} luot"
                )
                self._game_over_flag = True

            # -- Card drawn ---
            elif et == EventType.CARD_DRAWN:
                card_id   = event.data.get("card_id", "?")
                effect    = event.data.get("effect", "?")
                now = time.time()
                self._ui_state["card_overlay"] = {
                    "player":     pid or "?",
                    "card_id":    card_id,
                    "effect":     effect,
                    "content_id": "",   # raw card data not cached here
                    "created_at": now,
                    "expires_at": now + 3.0,
                }
                self._ui_state["event_log"].append(f"{pid} rut the {card_id} [{effect}]")

            # -- Dice roll ---
            elif et == EventType.DICE_ROLL:
                d     = event.data.get("dice", ())
                total = event.data.get("total", 0)
                self._ui_state["event_log"].append(
                    f"{pid} tung xuc xac: {d[0] if d else '?'}+{d[1] if len(d)>1 else '?'}={total}"
                )
                # Start dice animation — pause game loop until animation completes
                self._ui_state["dice_anim"] = {
                    "pid":        pid or "",
                    "final":      list(d) if len(d) >= 2 else [1, 1],
                    "total":      total,
                    "started_at": time.time(),
                    "duration":   2.0,   # 2s rolling, then 0.5s final display
                }
                self._speed_ctrl.wait_for_dice_anim()

    def _refresh_player_state(self, pid: str) -> None:
        """Recompute cash and total_assets for player pid from live Player object.

        MUST be called under self._lock (already acquired by caller).
        Computes total_assets = cash + sum(invested build cost per owned tile).
        Safe because this runs in background thread context where Player fields
        are only mutated by the same thread (GameController.step()).
        """
        player = next((p for p in self._players if p.player_id == pid), None)
        if player is None:
            return

        # Compute total invested build cost for owned properties
        total_assets = player.cash
        for pos in (player.owned_properties or []):
            tile = self._board.get_tile(pos)
            if tile.space_id == SpaceId.CITY:
                cfg = self._board.get_land_config(tile.opt)
                if cfg:
                    buildings = cfg.get("building", {})
                    for lvl in range(1, tile.building_level + 1):
                        b = buildings.get(str(lvl), {})
                        total_assets += b.get("build", 0) * 1000
            elif tile.space_id == SpaceId.RESORT:
                # Resort: initCost * 1000 is the invested cost at level >= 1
                resort_cfg = self._board.get_resort_config()
                if resort_cfg:
                    total_assets += resort_cfg.get("initCost", 0) * 1000

        if pid in self._ui_state:
            self._ui_state[pid]["cash"]         = player.cash
            self._ui_state[pid]["total_assets"] = total_assets
            self._ui_state[pid]["position"]     = player.position
            self._ui_state[pid]["is_bankrupt"]  = player.is_bankrupt
