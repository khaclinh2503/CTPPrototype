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
from ctp.tiles.fortune import set_debug_card

if TYPE_CHECKING:
    from ctp.config import ConfigLoader

# ── Card name/description lookup (from vi.txt) ───────────────────────────────
_CARD_NAMES: dict[str, str] = {
    "IT_CA_1":  "Thiên Thần",
    "IT_CA_2":  "Giảm Phí",
    "IT_CA_3":  "Bảo Vệ",
    "IT_CA_4":  "Bán Nhà",
    "IT_CA_5":  "Hoán Đổi",
    "IT_CA_6":  "Thế lực siêu nhiên",
    "IT_CA_7":  "Động Đất",
    "IT_CA_8":  "Bệnh dịch",
    "IT_CA_9":  "Bão Cát",
    "IT_CA_10": "Mất Điện",
    "IT_CA_11": "Đóng Thuế",
    "IT_CA_12": "Lễ hội",
    "IT_CA_13": "Đến Lễ Hội",
    "IT_CA_14": "Ra Đảo",
    "IT_CA_15": "Du Lịch",
    "IT_CA_16": "Bắt Đầu",
    "IT_CA_17": "Tổ chức lễ hội",
    "IT_CA_18": "Tăng Phí",
    "IT_CA_19": "Tặng Đất",
    "IT_CA_20": "Tặng Tiền",
    "IT_CA_21": "Quay lại bàn chơi",
    "IT_CA_22": "Thần triệu tập",
    "IT_CA_23": "Chong chóng",
    "IT_CA_24": "Ngân hàng",
    "IT_CA_25": "Khinh khí cầu",
    "IT_CA_29": "Đến Cột Cờ",
    "IT_CA_30": "Đến ô nước",
}

_CARD_DESCS: dict[str, str] = {
    "IT_CA_1":  "Miễn 100% phí khi vào ô đất",
    "IT_CA_2":  "Giảm 50% phí khi vào ô đất của người khác",
    "IT_CA_3":  "Vô hiệu hoá tấn công từ người chơi khác",
    "IT_CA_4":  "Buộc người khác bán một nhà đang sở hữu",
    "IT_CA_5":  "Phải đổi một nhà bất kỳ với người chơi khác",
    "IT_CA_6":  "Gây hoả hoạn thiêu huỷ 1 cấp nhà",
    "IT_CA_7":  "Tạo động đất phá huỷ thành phố",
    "IT_CA_8":  "Phát tán virut gây dịch bệnh cho thành phố",
    "IT_CA_9":  "Gây bão cát cho thành phố",
    "IT_CA_10": "Cắt nguồn điện của thành phố",
    "IT_CA_11": "Di chuyển tới ô thuế",
    "IT_CA_12": "Di chuyển tới lễ hội",
    "IT_CA_13": "Di chuyển tới ô đất đang tổ chức lễ hội",
    "IT_CA_14": "Người chơi phải ra đảo nghỉ dưỡng",
    "IT_CA_15": "Tới ô bến xe",
    "IT_CA_16": "Di chuyển tới ô xuất phát",
    "IT_CA_17": "Miễn phí tổ chức lễ hội",
    "IT_CA_18": "Chịu gấp đôi phí tham quan lượt tiếp theo",
    "IT_CA_19": "Tặng một ô đất cho đối thủ bất kỳ",
    "IT_CA_20": "Mọi người tặng tiền cho người nghèo nhất",
    "IT_CA_21": "Đưa người chơi quay lại bàn chơi từ đảo",
    "IT_CA_22": "Di chuyển tới một trong các Tượng Thần",
    "IT_CA_23": "Vượt qua ô đất bị nhấc lên hoặc bẫy",
    "IT_CA_24": "Di chuyển đến ô Ngân hàng",
    "IT_CA_25": "Di chuyển đến ô Khinh khí cầu",
    "IT_CA_29": "Di chuyển đến ô Cột Cờ gần nhất",
    "IT_CA_30": "Di chuyển đến ô Xoáy Nước gần nhất",
}

# Window settings (per UI-SPEC Window section)
_WIN_W  = 1280
_WIN_H  = 720
_FPS    = 60
_TITLE  = "CTP \u2014 Co Ty Phu AI Simulator"
_BG     = (30, 30, 30)

# Walk animation: seconds between each tile step, keyed by speed level
_ANIM_STEP_BY_SPEED: dict[str, float] = {
    "pause": 0.07,
    "0.5x": 0.12,
    "1x":   0.07,
    "2x":   0.04,
    "5x":   0.02,
    "10x":  0.01,
}


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

        # -- Popup callback state ---
        # popup_event: set = not blocked; clear = waiting for human click
        self._popup_event: threading.Event = threading.Event()
        self._popup_event.set()
        self._popup_decision: bool = False
        self._popup_btn_yes_rect:  pygame.Rect | None = None
        self._popup_btn_no_rect:   pygame.Rect | None = None
        self._popup_btn_card_rect: pygame.Rect | None = None  # 3rd button (prison choice)
        # List-selection popup (force_sell and future multi-choice popups)
        self._popup_select_result = None   # any — set by click on list item or skip
        self._popup_list_rects: list = []  # [(pygame.Rect, value), ...]

        # Wire popup callbacks — shows popup only for human player (index 0 = P1)
        self._controller.accept_card_fn       = self._accept_card_callback
        self._controller.use_card_fn          = self._use_card_callback
        self._controller.shield_block_fn      = self._shield_block_callback
        self._controller.force_sell_select_fn = self._force_sell_select_callback
        self._controller.swap_city_select_fn  = self._swap_city_select_callback
        self._controller.downgrade_select_fn  = self._downgrade_select_callback
        self._controller.virus_select_fn      = self._virus_select_callback
        self._controller.donate_select_fn     = self._donate_select_callback
        self._controller.prison_choice_fn     = self._prison_choice_callback
        self._controller.pinwheel_bypass_fn   = self._pinwheel_bypass_callback

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
        self._ui_state["popup"]            = None
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

        # Debug card picker state (main-thread only)
        self._dbg_picker_open: bool = False
        self._dbg_picker_idx:  int  = 0
        self._dbg_picker_cards: list[str] = [
            "IT_CA_1",  "IT_CA_2",  "IT_CA_3",  "IT_CA_4",  "IT_CA_5",
            "IT_CA_6",  "IT_CA_7",  "IT_CA_8",  "IT_CA_9",  "IT_CA_10",
            "IT_CA_11", "IT_CA_12", "IT_CA_13", "IT_CA_14", "IT_CA_15",
            "IT_CA_16", "IT_CA_17", "IT_CA_18", "IT_CA_19", "IT_CA_20",
            "IT_CA_21", "IT_CA_22", "IT_CA_23", "IT_CA_24", "IT_CA_25",
            "IT_CA_29", "IT_CA_30",
        ]
        self._dbg_queued_card: str | None = None  # hiển thị trong UI sau khi queue

    # ------------------------------------------------------------------
    # Public: run() is called by ctp/ui/__init__.py run_pygame()
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Initialise Pygame, publish GAME_STARTED, start background thread, run render loop."""
        pygame.init()
        screen = pygame.display.set_mode((_WIN_W, _WIN_H))
        pygame.display.set_caption(_TITLE)
        clock = pygame.time.Clock()

        # Fonts — dùng font_game.ttf để hỗ trợ tiếng Việt
        import os as _os
        _FONT_PATH = _os.path.join(_os.path.dirname(__file__), "..", "font_game.ttf")
        font_tile    = pygame.font.Font(_FONT_PATH, 11)   # tile labels
        font_token   = pygame.font.Font(_FONT_PATH, 12)   # player tokens
        font_body    = pygame.font.Font(_FONT_PATH, 13)   # panel body
        font_heading = pygame.font.Font(_FONT_PATH, 16)   # panel headings / speed
        font_overlay = pygame.font.Font(_FONT_PATH, 15)   # card overlay text

        _LOG_LINE_H = 14  # must match info_panel._LOG_LINE_H
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
                    if self._dbg_picker_open:
                        self._handle_dbg_picker_key(event.key)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._speed_ctrl.toggle_pause()
                        with self._lock:
                            self._ui_state["speed"] = self._speed_ctrl.speed
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        _speeds = ["0.5x", "1x", "2x", "5x", "10x"]
                        _cur = self._speed_ctrl.speed
                        _idx = _speeds.index(_cur) if _cur in _speeds else 1
                        if event.key == pygame.K_RIGHT:
                            _idx = min(_idx + 1, len(_speeds) - 1)
                        else:
                            _idx = max(_idx - 1, 0)
                        _new_speed = _speeds[_idx]
                        self._speed_ctrl.set_speed(_new_speed)
                        with self._lock:
                            self._ui_state["speed"] = _new_speed
                    elif event.key == pygame.K_F8:
                        self._dbg_picker_open = True
                        self._dbg_picker_idx  = 0
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
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Handle popup button clicks (popup blocks background game thread)
                    if not self._popup_event.is_set():
                        mx, my = event.pos
                        with self._lock:
                            popup = self._ui_state.get("popup")
                        popup_type = popup.get("type") if popup else None
                        if popup_type in ("force_sell_tiles", "swap_city_step1", "swap_city_step2", "donate_city_step1", "donate_city_step2"):
                            # List-selection popup: check item rects, then skip button
                            handled = False
                            for rect, value in self._popup_list_rects:
                                if rect.collidepoint(mx, my):
                                    self._popup_select_result = value
                                    self._popup_event.set()
                                    handled = True
                                    break
                            if not handled and self._popup_btn_no_rect and self._popup_btn_no_rect.collidepoint(mx, my):
                                self._popup_select_result = None
                                self._popup_event.set()
                        elif popup_type == "prison_choice":
                            # 3-button popup: roll / pay / card
                            if self._popup_btn_yes_rect and self._popup_btn_yes_rect.collidepoint(mx, my):
                                self._popup_select_result = "roll"
                                self._popup_event.set()
                            elif self._popup_btn_no_rect and self._popup_btn_no_rect.collidepoint(mx, my):
                                self._popup_select_result = "pay"
                                self._popup_event.set()
                            elif self._popup_btn_card_rect and self._popup_btn_card_rect.collidepoint(mx, my):
                                self._popup_select_result = "card"
                                self._popup_event.set()
                        else:
                            if self._popup_btn_yes_rect and self._popup_btn_yes_rect.collidepoint(mx, my):
                                self._popup_decision = True
                                self._popup_event.set()
                            elif self._popup_btn_no_rect and self._popup_btn_no_rect.collidepoint(mx, my):
                                self._popup_decision = False
                                self._popup_event.set()

            # Advance walk + dice animations (main thread)
            now = time.time()
            with self._lock:
                # Walk animation advance
                for _pid in self._player_ids:
                    pdata = self._ui_state.get(_pid)
                    if not isinstance(pdata, dict):
                        continue
                    anim = pdata.get("anim_path")
                    anim_step_s = _ANIM_STEP_BY_SPEED.get(self._ui_state.get("speed", "1x"), 0.07)
                    if anim and now - self._anim_step_time.get(_pid, 0) >= anim_step_s:
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
                        # Keep _dice_display showing final values during movement
                        del self._ui_state["dice_anim"]
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

            # Popup overlay — waits for human player decision (blocks game thread)
            popup_data = state_snapshot.get("popup")
            if popup_data:
                self._draw_popup(screen, popup_data, font_overlay, font_body)

            # Scoreboard overlay when game ends
            if self._game_over_flag:
                self._draw_scoreboard(screen, state_snapshot, font_heading, font_body)

            # Debug card picker overlay
            if self._dbg_picker_open:
                self._draw_dbg_picker(screen, font_tile, font_body)
            elif self._dbg_queued_card:
                hint = font_body.render(
                    f"[DBG] Thẻ tiếp theo: {self._dbg_queued_card}  "
                    f"{_CARD_NAMES.get(self._dbg_queued_card, '')}",
                    True, (255, 220, 60)
                )
                screen.blit(hint, (10, _WIN_H - 28))

            pygame.display.flip()
            clock.tick(_FPS)

        # Safety: unblock any game thread waiting for popup or dice
        self._popup_event.set()
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
            EventType.CARD_EFFECT_FORCE_SELL,
            EventType.CARD_EFFECT_SWAP_CITY,
            EventType.CARD_EFFECT_DOWNGRADE,
            EventType.CARD_EFFECT_VIRUS,
            EventType.CARD_EFFECT_GO_TO_START,
            EventType.CARD_EFFECT_GO_TO_PRISON,
            EventType.CARD_EFFECT_DOUBLE_TOLL_DEBUFF,
            EventType.CARD_EFFECT_GO_TO_FESTIVAL,
            EventType.CARD_EFFECT_GO_TO_FESTIVAL_TILE,
            EventType.CARD_EFFECT_GO_TO_TRAVEL,
            EventType.CARD_EFFECT_GO_TO_TAX,
            EventType.CARD_EFFECT_GO_TO_GOD,
            EventType.CARD_EFFECT_HOST_FESTIVAL,
            EventType.CARD_EFFECT_DONATE_CITY,
            EventType.CARD_EFFECT_CHARITY,
            EventType.CARD_EFFECT_GO_TO_WATER_SLIDE,
            EventType.CARD_EFFECT_SHIELD_BLOCKED,
            EventType.CARD_EFFECT_ANGEL,
            EventType.CARD_EFFECT_DISCOUNT_TOLL,
            EventType.CARD_EFFECT_ESCAPE_USED,
            EventType.CARD_EFFECT_PINWHEEL_BYPASS,
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
                    self._ui_state[pid]["position"] = new_pos

                    if move_type in (1, 3) and old_pos is not None:
                        path = _build_walk_path(old_pos, new_pos)
                        existing = self._ui_state[pid].get("anim_path")
                        if existing is not None:
                            existing.extend(path)
                        else:
                            self._ui_state[pid]["display_pos"] = old_pos
                            self._ui_state[pid]["anim_path"]   = path
                        self._ui_state["event_log"].append(
                            f"  Di chuyen tu o{old_pos} den o{new_pos}"
                        )
                    else:
                        self._ui_state[pid].pop("display_pos", None)
                        self._ui_state[pid].pop("anim_path", None)
                        if old_pos is not None:
                            self._ui_state["event_log"].append(
                                f"  Dich chuyen tu o{old_pos} den o{new_pos}"
                            )

            # -- Turn started ---
            elif et == EventType.TURN_STARTED:
                if pid:
                    self._ui_state["active_player_id"] = pid
                    turn  = event.data.get("turn", "?")
                    reason = event.data.get("reason", "")
                    if reason == "in_prison":
                        self._ui_state["event_log"].append(
                            f"--- Luot {turn}: {pid} (dang o tu) ---"
                        )
                    else:
                        self._ui_state["event_log"].append(
                            f"--- Luot {turn}: Nguoi choi {pid} ---"
                        )
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

                # Event log
                if et == EventType.TURN_ENDED:
                    self._ui_state["event_log"].append("")
                elif et == EventType.RENT_PAID:
                    amount = event.data.get("amount", 0)
                    recip  = event.data.get("recipient", "?")
                    pos    = event.data.get("position", "?")
                    golden = " [x2 Dat Vang]" if event.data.get("is_golden") else ""
                    self._ui_state["event_log"].append(
                        f"  Tra thue ${int(amount):,} cho {recip} tai o{pos}{golden}"
                    )
                elif et == EventType.TAX_PAID:
                    amount = event.data.get("amount", 0)
                    reason = event.data.get("reason", "")
                    if reason == "prison_escape":
                        self._ui_state["event_log"].append(
                            f"  Tra phi thoat tu: ${int(amount):,}"
                        )
                    else:
                        self._ui_state["event_log"].append(
                            f"  Nop thue: ${int(amount):,}"
                        )
                elif et == EventType.BONUS_RECEIVED:
                    amount = event.data.get("amount", 0)
                    reason = event.data.get("reason", "")
                    if reason == "doubles_reroll":
                        self._ui_state["event_log"].append(
                            "  Tung doi - duoc tung them 1 lan nua!"
                        )
                    else:
                        self._ui_state["event_log"].append(
                            f"  Nhan thuong: +${int(amount):,}"
                        )
                elif et == EventType.PROPERTY_PURCHASED:
                    pos   = event.data.get("position", "?")
                    price = event.data.get("price", 0)
                    self._ui_state["event_log"].append(
                        f"  Mua dat o{pos}: -${int(price):,}"
                    )
                elif et == EventType.PROPERTY_ACQUIRED:
                    pos    = event.data.get("position", "?")
                    from_p = event.data.get("from_player", "?")
                    price  = event.data.get("price", 0)
                    self._ui_state["event_log"].append(
                        f"  Cuop dat o{pos} cua {from_p}: -${int(price):,}"
                    )
                elif et == EventType.PROPERTY_UPGRADED:
                    pos       = event.data.get("position", "?")
                    new_level = event.data.get("new_level", "?")
                    cost      = event.data.get("cost", 0)
                    self._ui_state["event_log"].append(
                        f"  Nang cap o{pos} len cap {new_level}: -${int(cost):,}"
                    )
                elif et == EventType.PROPERTY_SOLD:
                    pos   = event.data.get("position", "?")
                    value = event.data.get("value", 0)
                    self._ui_state["event_log"].append(
                        f"  Ban dat o{pos}: +${int(value):,}"
                    )
                elif et == EventType.DEBT_SETTLED:
                    creditor = event.data.get("creditor", "?")
                    paid     = event.data.get("paid", 0)
                    owed     = event.data.get("owed", 0)
                    self._ui_state["event_log"].append(
                        f"  Thanh toan no cho {creditor}: ${int(paid):,} / ${int(owed):,}"
                    )

            # -- Bankrupt ---
            elif et == EventType.PLAYER_BANKRUPT:
                if pid and pid in self._ui_state:
                    self._ui_state[pid]["is_bankrupt"] = True
                    self._ui_state[pid].pop("display_pos", None)
                    self._ui_state[pid].pop("anim_path",   None)
                    self._ui_state["event_log"].append(
                        f"*** NGUOI CHOI {pid} DA PHA SAN ***"
                    )

            # -- Game ended ---
            elif et == EventType.GAME_ENDED:
                turns = event.data.get("turns", "?")
                self._ui_state["event_log"].append(
                    f"=== KET THUC SAU {turns} LUOT ==="
                )
                self._game_over_flag = True

            # -- Card drawn ---
            elif et == EventType.CARD_DRAWN:
                card_id = event.data.get("card_id", "?")
                effect  = event.data.get("effect", "?")
                now = time.time()
                self._ui_state["card_overlay"] = {
                    "player":     pid or "?",
                    "card_id":    card_id,
                    "effect":     effect,
                    "card_name":  _CARD_NAMES.get(card_id, card_id),
                    "card_desc":  _CARD_DESCS.get(card_id, ""),
                    "created_at": now,
                    "expires_at": now + 3.0,
                }
                card_name = _CARD_NAMES.get(card_id, card_id)
                self._ui_state["event_log"].append(
                    f"  Rut the [{card_id}] {card_name}: {effect}"
                )

            # -- Prison entered ---
            elif et == EventType.PRISON_ENTERED:
                reason = event.data.get("reason", "")
                turns  = event.data.get("turns", 0)
                if reason == "triple_doubles":
                    self._ui_state["event_log"].append(
                        f"  Tung doi 3 lan lien tiep - {pid} vao TU! ({turns} luot)"
                    )
                else:
                    self._ui_state["event_log"].append(
                        f"  {pid} bi giam vao tu {turns} luot"
                    )

            # -- Prison exited ---
            elif et == EventType.PRISON_EXITED:
                reason = event.data.get("reason", "")
                if reason == "paid":
                    self._ui_state["event_log"].append(f"  {pid} da tra phi - ra tu!")
                elif reason == "doubles":
                    self._ui_state["event_log"].append(f"  {pid} tung doi - ra tu!")
                elif reason == "served":
                    self._ui_state["event_log"].append(f"  {pid} man han - ra tu!")

            # -- Dice roll ---
            elif et == EventType.DICE_ROLL:
                d     = event.data.get("dice", ())
                total = event.data.get("total", 0)
                d0    = d[0] if d else "?"
                d1    = d[1] if len(d) > 1 else "?"
                is_prison_roll = event.data.get("prison_roll", False)
                doubles_tag = " (tung doi!)" if event.data.get("doubles") else ""
                if is_prison_roll:
                    self._ui_state["event_log"].append(
                        f"  [Tu] Thu tung doi: {d0} + {d1} = {total}{doubles_tag}"
                    )
                else:
                    self._ui_state["event_log"].append(
                        f"  Tung xuc xac: {d0} + {d1} = {total}{doubles_tag}"
                    )
                # Start dice animation — pause game loop until animation completes
                self._ui_state["dice_anim"] = {
                    "pid":        pid or "",
                    "final":      list(d) if len(d) >= 2 else [1, 1],
                    "total":      total,
                    "started_at": time.time(),
                    "duration":   2.0,
                }
                self._speed_ctrl.wait_for_dice_anim()

            # -- Rent owed (not enough cash) ---
            elif et == EventType.RENT_OWED:
                amount    = event.data.get("amount", 0)
                recipient = event.data.get("recipient", "?")
                pos       = event.data.get("position", "?")
                self._ui_state["event_log"].append(
                    f"  No thue o{pos}: {pid} no {recipient} ${int(amount):,}"
                )

            # -- Minigame result ---
            elif et == EventType.MINIGAME_RESULT:
                won = event.data.get("won", False)
                bet = event.data.get("bet", 0)
                self._ui_state["event_log"].append(
                    f"  Minigame: {'THANG' if won else 'THUA'} (cuoc ${int(bet):,})"
                )

            # -- Card effects ---
            elif et == EventType.CARD_EFFECT_FORCE_SELL:
                target = event.data.get("target_player", "?")
                pos    = event.data.get("position", "?")
                refund = event.data.get("refund", 0)
                self._ui_state["event_log"].append(
                    f"  {pid} ep {target} ban o{pos} (hoan ${int(refund):,})"
                )
            elif et == EventType.CARD_EFFECT_SWAP_CITY:
                their = event.data.get("opponent", "?")
                my_p  = event.data.get("my_pos", "?")
                thr_p = event.data.get("their_pos", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} doi o{my_p} lay o{thr_p} cua {their}"
                )
            elif et == EventType.CARD_EFFECT_DOWNGRADE:
                if event.data.get("skipped"):
                    self._ui_state["event_log"].append(
                        "  Khong co o hop le — the bi mat, bo qua hieu ung"
                    )
                elif event.data.get("lost_ownership"):
                    target = event.data.get("target_player", "?")
                    pos    = event.data.get("position", "?")
                    self._ui_state["event_log"].append(
                        f"  o{pos} cua {target} bi ha cap ve 0 — mat quyen so huu!"
                    )
                else:
                    target = event.data.get("target_player", "?")
                    pos    = event.data.get("position", "?")
                    lvl    = event.data.get("new_level", "?")
                    self._ui_state["event_log"].append(
                        f"  o{pos} cua {target} bi ha cap con lv{lvl}"
                    )
            elif et == EventType.CARD_EFFECT_VIRUS:
                if event.data.get("cleared_by"):
                    # Tile debuff bị clear khi visitor đặt chân vào
                    pos        = event.data.get("tile_pos", "?")
                    cleared_by = event.data.get("cleared_by", "?")
                    self._ui_state["event_log"].append(
                        f"  {cleared_by} vao o{pos} bi virus - mien phi, hieu ung xoa!"
                    )
                else:
                    target    = event.data.get("target_player", "?")
                    positions = event.data.get("affected_positions", [])
                    duration  = event.data.get("duration", 0)
                    rate      = event.data.get("debuff_rate", 0.0)
                    effect_str = "mat phi" if rate == 0.0 else f"giam {int((1-rate)*100)}% phi"
                    pos_str    = ", ".join(f"o{p}" for p in positions)
                    self._ui_state["event_log"].append(
                        f"  {target} bi virus {duration} luot: {pos_str} ({effect_str})"
                    )
            elif et == EventType.CARD_EFFECT_GO_TO_START:
                bonus = event.data.get("bonus_received", 0)
                self._ui_state["event_log"].append(
                    f"  {pid} ve o Xuat Phat (+${int(bonus):,})"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_PRISON:
                pos = event.data.get("position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} bi dua thang vao Tu (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_DOUBLE_TOLL_DEBUFF:
                self._ui_state["event_log"].append(
                    f"  {pid} phai tra gap doi phi luot toi"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_FESTIVAL:
                pos = event.data.get("target_position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} di chuyen den Le Hoi (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_FESTIVAL_TILE:
                pos = event.data.get("target_position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} di chuyen den o dat Le Hoi (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_TRAVEL:
                pos = event.data.get("target_position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} di chuyen den Ben Xe (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_TAX:
                pos = event.data.get("target_position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} di chuyen den o Thue (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_GOD:
                pos = event.data.get("target_position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} di chuyen den Tuong Than (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_GO_TO_WATER_SLIDE:
                pos = event.data.get("target_position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} di chuyen den Xoay Nuoc (o{pos})"
                )
            elif et == EventType.CARD_EFFECT_HOST_FESTIVAL:
                pos = event.data.get("position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} to chuc Le Hoi mien phi tai o{pos}"
                )
            elif et == EventType.CARD_EFFECT_DONATE_CITY:
                recipient = event.data.get("recipient", "?")
                pos       = event.data.get("position", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} tang o{pos} cho {recipient}"
                )
            elif et == EventType.CARD_EFFECT_CHARITY:
                recipient = event.data.get("recipient", "?")
                total     = event.data.get("total_received", 0)
                self._ui_state["event_log"].append(
                    f"  Tu thien: moi nguoi gop tien cho {recipient} (+${int(total):,})"
                )
            elif et == EventType.CARD_EFFECT_SHIELD_BLOCKED:
                blocked_by = event.data.get("blocked_card", "?")
                self._ui_state["event_log"].append(
                    f"  {pid} chan tan cong bang Khien!"
                )
            elif et == EventType.CARD_EFFECT_ANGEL:
                self._ui_state["event_log"].append(
                    f"  {pid} duoc Thien Than bao ve - mien toan bo phi!"
                )
            elif et == EventType.CARD_EFFECT_DISCOUNT_TOLL:
                self._ui_state["event_log"].append(
                    f"  {pid} dung the Giam Phi - chi tra 50%"
                )
            elif et == EventType.CARD_EFFECT_ESCAPE_USED:
                self._ui_state["event_log"].append(
                    f"  {pid} dung the Thoat Nguc - ra tu ngay!"
                )
            elif et == EventType.CARD_EFFECT_PINWHEEL_BYPASS:
                self._ui_state["event_log"].append(
                    f"  {pid} dung Chong Chong - bo qua bep/cau tuot!"
                )

            # Auto-scroll log to latest on every new event
            self._ui_state["log_scroll"] = 0

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

    # ------------------------------------------------------------------
    # Popup callbacks (called from background thread, blocks until click)
    # ------------------------------------------------------------------

    def _accept_card_callback(self, player, card_id: str) -> bool:
        """Called when player draws a held card (IT_CA_1 / IT_CA_2 etc.).
        Human player (P1, index 0) → show popup; AI → always accept.
        Returns True = keep card, False = discard.
        """
        if player.player_id != self._player_ids[0]:
            return True   # AI: always accept
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "accept_card",
                "player_id": player.player_id,
                "card_id":   card_id,
                "card_name": _CARD_NAMES.get(card_id, card_id),
                "card_desc": _CARD_DESCS.get(card_id, ""),
                "btn_yes":   "Lấy thẻ",
                "btn_no":    "Bỏ thẻ",
            }
        self._popup_event.clear()
        self._popup_event.wait()    # blocks background thread until click
        with self._lock:
            self._ui_state["popup"] = None
        return self._popup_decision

    def _use_card_callback(self, player, card_id: str, toll_amount: int) -> bool:
        """Called when player lands on opponent land and has a usable held card.
        Human player (P1, index 0) → show popup; AI → always use.
        Returns True = use card, False = keep card and pay toll normally.
        """
        if player.player_id != self._player_ids[0]:
            return True   # AI: always use
        with self._lock:
            self._ui_state["popup"] = {
                "type":        "use_card",
                "player_id":   player.player_id,
                "card_id":     card_id,
                "card_name":   _CARD_NAMES.get(card_id, card_id),
                "card_desc":   _CARD_DESCS.get(card_id, ""),
                "toll_amount": toll_amount,
                "btn_yes":     "Dùng thẻ",
                "btn_no":      "Giữ thẻ",
            }
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
        return self._popup_decision

    def _shield_block_callback(self, defender, attacker_card: str) -> bool:
        """Called when defender has IT_CA_3 and is being attacked.
        Human defender → show popup; AI defender → always use.
        Returns True = dùng thẻ (chặn + tiêu thẻ), False = bỏ qua (giữ thẻ).
        """
        if defender.player_id != self._player_ids[0]:
            return True   # AI: always block
        atk_name = _CARD_NAMES.get(attacker_card, attacker_card)
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "shield_block",
                "player_id": defender.player_id,
                "card_id":   defender.held_card,
                "card_name": _CARD_NAMES.get(defender.held_card or "", "Bảo Vệ"),
                "card_desc": f"Bị tấn công bởi [{attacker_card}] {atk_name}. Dùng thẻ để huỷ đòn (thẻ sẽ bị tiêu)?",
                "btn_yes":   "Dùng thẻ",
                "btn_no":    "Bỏ qua",
            }
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
        return self._popup_decision

    def _pinwheel_bypass_callback(self, player) -> bool:
        """IT_CA_23: hỏi player có muốn dùng thẻ Chong Chóng để bỏ qua ô nâng không.
        Human P1 → popup; AI → auto True.
        Returns True = dùng thẻ (bypass), False = giữ thẻ (bị chặn bởi ô nâng).
        """
        if player.player_id != self._player_ids[0]:
            return True  # AI: auto-dùng
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "use_card",
                "player_id": player.player_id,
                "card_id":   "IT_CA_23",
                "card_name": _CARD_NAMES.get("IT_CA_23", "Chong Chóng"),
                "card_desc": "Co o nang tren duong di. Dung the de bo qua?",
                "toll_amount": 0,
                "btn_yes":   "Dùng thẻ",
                "btn_no":    "Giữ thẻ",
            }
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
        return self._popup_decision

    def _force_sell_select_callback(self, player, board, players):
        """IT_CA_4: player chọn 1 tile của bất kỳ đối thủ để ép bán.
        Human P1 → 1-step popup (list tất cả tile không phải của mình).
        AI → tự chọn richest opponent + tile cao nhất.
        Returns (opponent_id, tile_pos) or None (bỏ qua / không có target).
        """
        # Gom tất cả tile của đối thủ
        opponent_tiles = []
        for p in players:
            if p.player_id == player.player_id:
                continue
            for pos in p.owned_properties:
                t = board.get_tile(pos)
                opponent_tiles.append((p, t))

        if not opponent_tiles:
            return None

        if player.player_id != self._player_ids[0]:
            # AI: chọn tile building_level cao nhất
            _, best_tile = max(opponent_tiles, key=lambda pt: pt[1].building_level)
            opp = next(p for p, t in opponent_tiles if t.position == best_tile.position)
            return (opp.player_id, best_tile.position)

        # Human P1: single-list popup
        tile_items = [
            {
                "pos":   t.position,
                "id":    p.player_id,
                "label": f"Ô {t.position}  lv{t.building_level}  [{p.player_id}]",
            }
            for p, t in opponent_tiles
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "force_sell_tiles",
                "card_id":   "IT_CA_4",
                "card_name": _CARD_NAMES.get("IT_CA_4", "Bán Nhà"),
                "items":     tile_items,
                "btn_no":    "Bỏ qua",
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            result = self._popup_select_result  # (owner_id, pos) or None

        return result

    def _swap_city_select_callback(self, player, board, players):
        """IT_CA_5: 2-step popup — chọn CITY của mình, rồi chọn CITY của đối thủ.
        Human P1 → popup step 1 + step 2.
        AI → trả None (fortune.py xử lý AI riêng).
        Returns (my_pos, opponent_id, their_pos) or None.
        """
        if player.player_id != self._player_ids[0]:
            return None  # AI: handled in fortune.py

        from ctp.core.board import SpaceId

        # Step 1: chọn CITY của bản thân
        my_city_tiles = [
            board.get_tile(pos)
            for pos in player.owned_properties
            if board.get_tile(pos).space_id == SpaceId.CITY
        ]
        if not my_city_tiles:
            return None

        my_items = [
            {"pos": t.position, "id": player.player_id,
             "label": f"Ô {t.position}  lv{t.building_level}"}
            for t in my_city_tiles
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "swap_city_step1",
                "card_id":   "IT_CA_5",
                "card_name": _CARD_NAMES.get("IT_CA_5", "Hoán Đổi"),
                "prompt":    "Chọn CITY của bạn để đổi:",
                "items":     my_items,
                "btn_no":    "Bỏ qua",
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            step1 = self._popup_select_result  # (player_id, pos) or None

        if step1 is None:
            return None
        _, my_pos = step1

        # Step 2: chọn CITY của đối thủ
        opponent_city_tiles = []
        for p in players:
            if p.player_id == player.player_id or p.is_bankrupt:
                continue
            for pos in p.owned_properties:
                t = board.get_tile(pos)
                if t.space_id == SpaceId.CITY:
                    opponent_city_tiles.append((p, t))

        if not opponent_city_tiles:
            return None

        their_items = [
            {"pos": t.position, "id": p.player_id,
             "label": f"Ô {t.position}  lv{t.building_level}  [{p.player_id}]"}
            for p, t in opponent_city_tiles
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "swap_city_step2",
                "card_id":   "IT_CA_5",
                "card_name": _CARD_NAMES.get("IT_CA_5", "Hoán Đổi"),
                "prompt":    "Chọn CITY của đối thủ để nhận:",
                "items":     their_items,
                "btn_no":    "Bỏ qua",
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            step2 = self._popup_select_result  # (opponent_id, pos) or None

        if step2 is None:
            return None
        opponent_id, their_pos = step2

        return (my_pos, opponent_id, their_pos)

    def _downgrade_select_callback(self, player, board, players):
        """IT_CA_6/7: player chọn 1 CITY của đối thủ (không phải Landmark L5) để hạ cấp.
        Human P1 → popup danh sách.
        AI → trả None (fortune.py xử lý AI riêng).
        Returns (opponent_id, tile_pos) or None.
        """
        if player.player_id != self._player_ids[0]:
            return None  # AI: handled in fortune.py

        from ctp.core.board import SpaceId

        candidate_tiles = []
        for p in players:
            if p.player_id == player.player_id or p.is_bankrupt:
                continue
            for pos in p.owned_properties:
                t = board.get_tile(pos)
                if t.space_id == SpaceId.CITY and t.building_level < 5:
                    candidate_tiles.append((p, t))

        if not candidate_tiles:
            return None

        tile_items = [
            {
                "pos":   t.position,
                "id":    p.player_id,
                "label": f"Ô {t.position}  lv{t.building_level}  [{p.player_id}]",
            }
            for p, t in candidate_tiles
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "force_sell_tiles",
                "card_id":   "IT_CA_7",
                "card_name": _CARD_NAMES.get("IT_CA_7", "Động Đất"),
                "prompt":    "Chọn CITY của đối thủ để hạ cấp:",
                "items":     tile_items,
                "btn_no":    "Bỏ qua",
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            result = self._popup_select_result  # (owner_id, pos) or None

        return result

    def _virus_select_callback(self, player, board, players, card_id=None):
        """IT_CA_8/10 (EF_7) và IT_CA_9 (EF_8): player chọn 1 CITY của đối thủ để debuff.
        Human P1 → popup danh sách.
        AI → trả None (fortune.py xử lý AI riêng).
        Returns (opponent_id, tile_pos) or None.
        """
        if player.player_id != self._player_ids[0]:
            return None  # AI: handled in fortune.py

        from ctp.core.board import SpaceId

        candidate_tiles = []
        for p in players:
            if p.player_id == player.player_id or p.is_bankrupt:
                continue
            for pos in p.owned_properties:
                t = board.get_tile(pos)
                if t.space_id == SpaceId.CITY:
                    candidate_tiles.append((p, t))

        if not candidate_tiles:
            return None

        display_id   = card_id or "IT_CA_8"
        display_name = _CARD_NAMES.get(display_id, "Tấn công")

        tile_items = [
            {
                "pos":   t.position,
                "id":    p.player_id,
                "label": f"Ô {t.position}  lv{t.building_level}  [{p.player_id}]",
            }
            for p, t in candidate_tiles
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "force_sell_tiles",
                "card_id":   display_id,
                "card_name": display_name,
                "prompt":    "Chọn CITY của đối thủ để tấn công:",
                "items":     tile_items,
                "btn_no":    "Bỏ qua",
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            result = self._popup_select_result  # (owner_id, pos) or None

        return result

    def _donate_select_callback(self, player, board, players):
        """IT_CA_19 (EF_17): player chọn 1 tile của mình → chọn người nhận. Bắt buộc.
        Human P1 → 2-step popup không có nút bỏ qua.
        AI → trả None (fortune.py xử lý AI riêng).
        Returns (tile_pos, recipient_id) or None.
        """
        if player.player_id != self._player_ids[0]:
            return None  # AI: handled in fortune.py

        from ctp.core.board import SpaceId

        # Step 1: chọn tile của bản thân
        my_tiles = [
            board.get_tile(pos)
            for pos in player.owned_properties
        ]
        if not my_tiles:
            return None

        my_items = [
            {
                "pos":   t.position,
                "id":    player.player_id,
                "label": f"Ô {t.position}  lv{t.building_level}" + ("  [khu nghỉ dưỡng]" if t.space_id == SpaceId.RESORT else ""),
            }
            for t in my_tiles
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "donate_city_step1",
                "card_id":   "IT_CA_19",
                "card_name": _CARD_NAMES.get("IT_CA_19", "Tặng Đất"),
                "prompt":    "Chọn nhà muốn tặng:",
                "items":     my_items,
                # Không có btn_no — bắt buộc phải chọn
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            step1 = self._popup_select_result  # (player_id, tile_pos) or None

        if step1 is None:
            return None
        _, tile_pos = step1

        # Step 2: chọn người nhận
        recipients = [p for p in players if not p.is_bankrupt and p.player_id != player.player_id]
        if not recipients:
            return None

        recipient_items = [
            {
                "pos":   None,
                "id":    p.player_id,
                "label": f"{p.player_id}  ${p.cash:,}",
            }
            for p in recipients
        ]
        with self._lock:
            self._ui_state["popup"] = {
                "type":      "donate_city_step2",
                "card_id":   "IT_CA_19",
                "card_name": _CARD_NAMES.get("IT_CA_19", "Tặng Đất"),
                "prompt":    "Chọn người nhận:",
                "items":     recipient_items,
                # Không có btn_no — bắt buộc phải chọn
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            step2 = self._popup_select_result  # (recipient_id, None) or None

        if step2 is None:
            return None
        recipient_id, _ = step2

        return (tile_pos, recipient_id)

    def _prison_choice_callback(self, player, escape_fee: int, has_escape_card: bool) -> str:
        """Popup 3 lựa chọn khi human player đang ở tù đầu lượt.
        AI → tự quyết (không gọi hàm này).
        Returns 'roll' | 'pay' | 'card'.
        """
        if player.player_id != self._player_ids[0]:
            # AI fallback (không nên gọi, nhưng an toàn)
            if has_escape_card:
                return 'card'
            if player.can_afford(escape_fee):
                return 'pay'
            return 'roll'

        with self._lock:
            self._ui_state["popup"] = {
                "type":            "prison_choice",
                "escape_fee":      escape_fee,
                "has_escape_card": has_escape_card,
                "can_pay":         player.can_afford(escape_fee),
            }
            self._popup_select_result = None
        self._popup_event.clear()
        self._popup_event.wait()
        with self._lock:
            self._ui_state["popup"] = None
            result = self._popup_select_result or "roll"
        return result

    def _draw_prison_choice_popup(
        self,
        screen: pygame.Surface,
        popup: dict,
        font_big: pygame.font.Font,
        font_body: pygame.font.Font,
    ) -> None:
        """Vẽ popup chọn hành động khi ở tù: Đổ / Trả tiền / Dùng thẻ."""
        box_w = 520
        box_h = 220
        pad   = 20
        btn_w = 145
        btn_h = 42
        box_x = (_WIN_W - box_w) // 2
        box_y = (_WIN_H - box_h) // 2

        dim = pygame.Surface((_WIN_W, _WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((30, 15, 50, 245))
        screen.blit(panel, (box_x, box_y))
        pygame.draw.rect(screen, (200, 120, 255), (box_x, box_y, box_w, box_h), 2)

        title = font_big.render("Dang o tu — Chon hanh dong:", True, (255, 200, 80))
        screen.blit(title, (box_x + pad, box_y + pad))

        escape_fee  = popup.get("escape_fee", 0)
        can_pay     = popup.get("can_pay", False)
        has_card    = popup.get("has_escape_card", False)

        # Nút 1: Đổ xúc xắc (luôn hiện)
        # Nút 2: Dùng tiền (dim nếu không đủ)
        # Nút 3: Dùng thẻ (chỉ hiện nếu có thẻ)
        spacing = 12
        num_btns = 2 + (1 if has_card else 0)
        total_w  = btn_w * num_btns + spacing * (num_btns - 1)
        btn_y    = box_y + box_h - pad - btn_h
        start_x  = box_x + (box_w - total_w) // 2

        # Btn roll
        roll_rect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(screen, (40, 80, 160), roll_rect, border_radius=6)
        pygame.draw.rect(screen, (100, 160, 255), roll_rect, 1, border_radius=6)
        lbl = font_body.render("Do xuc xac", True, (220, 230, 255))
        screen.blit(lbl, lbl.get_rect(center=roll_rect.center))
        self._popup_btn_yes_rect = roll_rect

        # Btn pay
        pay_color  = (40, 130, 60) if can_pay else (60, 60, 60)
        pay_border = (100, 220, 120) if can_pay else (100, 100, 100)
        pay_rect   = pygame.Rect(start_x + btn_w + spacing, btn_y, btn_w, btn_h)
        pygame.draw.rect(screen, pay_color, pay_rect, border_radius=6)
        pygame.draw.rect(screen, pay_border, pay_rect, 1, border_radius=6)
        pay_lbl = font_body.render(f"Tra ${escape_fee:,}", True, (220, 255, 220) if can_pay else (140, 140, 140))
        screen.blit(pay_lbl, pay_lbl.get_rect(center=pay_rect.center))
        self._popup_btn_no_rect = pay_rect

        # Btn card (optional)
        if has_card:
            card_rect = pygame.Rect(start_x + (btn_w + spacing) * 2, btn_y, btn_w, btn_h)
            pygame.draw.rect(screen, (130, 50, 160), card_rect, border_radius=6)
            pygame.draw.rect(screen, (220, 120, 255), card_rect, 1, border_radius=6)
            clbl = font_body.render("Dung the", True, (255, 220, 255))
            screen.blit(clbl, clbl.get_rect(center=card_rect.center))
            self._popup_btn_card_rect = card_rect
        else:
            self._popup_btn_card_rect = None

    def _draw_list_popup(
        self,
        screen: pygame.Surface,
        popup: dict,
        font_big: pygame.font.Font,
        font_body: pygame.font.Font,
    ) -> None:
        """Vẽ list-selection popup (force_sell_opponents / force_sell_tiles)."""
        items = popup.get("items", [])
        item_h = 38
        pad    = 16
        btn_h  = 36
        header_h = font_big.get_linesize() + font_body.get_linesize() + pad * 2
        has_skip = bool(popup.get("btn_no"))
        box_w  = 420
        box_h  = header_h + len(items) * item_h + pad + (btn_h + pad if has_skip else pad)
        box_x  = (_WIN_W - box_w) // 2
        box_y  = (_WIN_H - box_h) // 2

        # Dim
        dim = pygame.Surface((_WIN_W, _WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # Panel
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((20, 25, 50, 248))
        screen.blit(panel, (box_x, box_y))
        pygame.draw.rect(screen, (100, 160, 255), (box_x, box_y, box_w, box_h), 2)

        # Header
        screen.blit(
            font_big.render(f"[{popup.get('card_id', '')}]  {popup.get('card_name', '')}", True, (255, 230, 60)),
            (box_x + pad, box_y + pad),
        )
        prompt = popup.get("prompt", "Chọn ngôi nhà muốn ép bán:")
        screen.blit(
            font_body.render(prompt, True, (180, 200, 240)),
            (box_x + pad, box_y + pad + font_big.get_linesize() + 4),
        )

        # List items — value stored as (owner_id, pos)
        self._popup_list_rects = []
        list_top = box_y + header_h
        for i, item in enumerate(items):
            iy = list_top + i * item_h
            rect = pygame.Rect(box_x + pad, iy + 3, box_w - pad * 2, item_h - 6)
            self._popup_list_rects.append((rect, (item.get("id"), item.get("pos"))))
            pygame.draw.rect(screen, (40, 60, 110), rect, border_radius=5)
            pygame.draw.rect(screen, (80, 120, 200), rect, 1, border_radius=5)
            lbl = font_body.render(item.get("label", ""), True, (220, 230, 255))
            screen.blit(lbl, lbl.get_rect(midleft=(rect.x + 10, rect.centery)))

        # Skip button (bottom centre) — chỉ hiển thị nếu popup có btn_no
        self._popup_btn_yes_rect = None
        if has_skip:
            skip_w = 140
            skip_rect = pygame.Rect(box_x + (box_w - skip_w) // 2, box_y + box_h - pad - btn_h, skip_w, btn_h)
            self._popup_btn_no_rect = skip_rect
            pygame.draw.rect(screen, (100, 40, 40), skip_rect, border_radius=6)
            pygame.draw.rect(screen, (200, 80, 80), skip_rect, 1, border_radius=6)
            skip_lbl = font_body.render(popup.get("btn_no", "Bỏ qua"), True, (255, 180, 180))
            screen.blit(skip_lbl, skip_lbl.get_rect(center=skip_rect.center))
        else:
            self._popup_btn_no_rect = None

    def _draw_popup(
        self,
        screen: pygame.Surface,
        popup: dict,
        font_big: pygame.font.Font,
        font_body: pygame.font.Font,
    ) -> None:
        """Vẽ modal popup chờ quyết định người chơi (Lấy/Bỏ thẻ hoặc Dùng/Giữ thẻ)."""
        if popup.get("type") in ("force_sell_tiles", "swap_city_step1", "swap_city_step2", "donate_city_step1", "donate_city_step2"):
            self._draw_list_popup(screen, popup, font_big, font_body)
            return
        if popup.get("type") == "prison_choice":
            self._draw_prison_choice_popup(screen, popup, font_big, font_body)
            return
        box_w = 500
        box_h = 230
        pad   = 20
        btn_w = 160
        btn_h = 40
        box_x = (_WIN_W - box_w) // 2
        box_y = (_WIN_H - box_h) // 2

        # Dim entire screen
        dim = pygame.Surface((_WIN_W, _WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        screen.blit(dim, (0, 0))

        # Panel background
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((20, 25, 50, 245))
        screen.blit(panel, (box_x, box_y))
        pygame.draw.rect(screen, (100, 160, 255), (box_x, box_y, box_w, box_h), 2)

        # Card name
        name_surf = font_big.render(
            f"[{popup['card_id']}]  {popup['card_name']}", True, (255, 230, 60)
        )
        screen.blit(name_surf, (box_x + pad, box_y + pad))

        # Card description
        desc_surf = font_body.render(popup["card_desc"], True, (200, 200, 200))
        screen.blit(desc_surf, (box_x + pad, box_y + pad + font_big.get_linesize() + 6))

        # Toll info (use_card popup only)
        if popup.get("type") == "use_card":
            toll_amt = popup.get("toll_amount", 0)
            toll_surf = font_body.render(
                f"Phí cần trả: ${int(toll_amt):,}", True, (255, 160, 60)
            )
            screen.blit(toll_surf, (
                box_x + pad,
                box_y + pad + font_big.get_linesize() + 6 + font_body.get_linesize() + 4,
            ))

        # Buttons (Yes left, No right)
        spacing = 20
        total_btn_w = btn_w * 2 + spacing
        btn_y = box_y + box_h - pad - btn_h
        yes_x = box_x + (box_w - total_btn_w) // 2
        no_x  = yes_x + btn_w + spacing

        yes_rect = pygame.Rect(yes_x, btn_y, btn_w, btn_h)
        no_rect  = pygame.Rect(no_x,  btn_y, btn_w, btn_h)

        # Store rects for click detection (main-thread only — no lock needed)
        self._popup_btn_yes_rect = yes_rect
        self._popup_btn_no_rect  = no_rect

        pygame.draw.rect(screen, (40, 140, 80),  yes_rect, border_radius=6)
        pygame.draw.rect(screen, (140, 50,  50), no_rect,  border_radius=6)
        pygame.draw.rect(screen, (100, 220, 120), yes_rect, 1, border_radius=6)
        pygame.draw.rect(screen, (220, 100, 100), no_rect,  1, border_radius=6)

        yes_label = font_body.render(popup.get("btn_yes", "Có"),    True, (220, 255, 220))
        no_label  = font_body.render(popup.get("btn_no",  "Không"), True, (255, 220, 220))
        screen.blit(yes_label, yes_label.get_rect(center=yes_rect.center))
        screen.blit(no_label,  no_label.get_rect(center=no_rect.center))

    # ------------------------------------------------------------------
    # Debug card picker (main-thread only — no lock needed)
    # ------------------------------------------------------------------

    def _handle_dbg_picker_key(self, key: int) -> None:
        """Xử lý phím khi debug picker đang mở."""
        total = len(self._dbg_picker_cards)
        if key == pygame.K_UP:
            self._dbg_picker_idx = (self._dbg_picker_idx - 1) % total
        elif key == pygame.K_DOWN:
            self._dbg_picker_idx = (self._dbg_picker_idx + 1) % total
        elif key == pygame.K_RETURN:
            card_id = self._dbg_picker_cards[self._dbg_picker_idx]
            set_debug_card(card_id)
            self._dbg_queued_card  = card_id
            self._dbg_picker_open  = False
        elif key in (pygame.K_ESCAPE, pygame.K_F8):
            self._dbg_picker_open = False

    def _draw_dbg_picker(
        self,
        screen: pygame.Surface,
        font_list: pygame.font.Font,
        font_head: pygame.font.Font,
    ) -> None:
        """Vẽ debug card picker overlay ở giữa màn hình."""
        row_h    = font_list.get_linesize()
        head_h   = font_head.get_linesize()
        padding  = 10
        cols     = 2
        per_col  = (len(self._dbg_picker_cards) + cols - 1) // cols
        col_w    = 300
        box_w    = col_w * cols + padding * 3
        box_h    = per_col * row_h + head_h + padding * 3
        box_x    = (_WIN_W - box_w) // 2
        box_y    = (_WIN_H - box_h) // 2

        # Background
        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        overlay.fill((20, 20, 20, 220))
        screen.blit(overlay, (box_x, box_y))
        pygame.draw.rect(screen, (100, 200, 255), (box_x, box_y, box_w, box_h), 2)

        # Heading
        head = font_head.render(
            "F8: Chọn thẻ debug  (↑↓  Enter  Esc)",
            True, (100, 200, 255)
        )
        screen.blit(head, (box_x + padding, box_y + padding))

        # Card list (2 columns)
        list_top = box_y + padding + head_h + padding
        for i, cid in enumerate(self._dbg_picker_cards):
            col    = i // per_col
            row    = i  % per_col
            tx     = box_x + padding + col * (col_w + padding)
            ty     = list_top + row * row_h
            is_sel = (i == self._dbg_picker_idx)
            if is_sel:
                pygame.draw.rect(screen, (60, 100, 160), (tx - 4, ty, col_w, row_h))
            color = (255, 230, 60) if is_sel else (180, 180, 180)
            name  = _CARD_NAMES.get(cid, cid)
            label = font_list.render(f"{cid}  {name}", True, color)
            screen.blit(label, (tx, ty))

    # ------------------------------------------------------------------
    # Scoreboard overlay (main-thread only)
    # ------------------------------------------------------------------

    _RANK_COLORS = [
        (255, 215,   0),   # 1st — gold
        (192, 192, 192),   # 2nd — silver
        (205, 127,  50),   # 3rd — bronze
        (160, 160, 160),   # 4th+
    ]
    _RANK_MEDALS = ["1", "2", "3", "4"]

    def _draw_scoreboard(
        self,
        screen: pygame.Surface,
        state: dict,
        font_head: pygame.font.Font,
        font_body: pygame.font.Font,
    ) -> None:
        """Vẽ bảng kết quả xếp hạng phủ lên board khi game kết thúc."""
        # Build sorted player list by total_assets desc (bankrupt last)
        rows: list[tuple[str, int, int, bool]] = []   # (pid, cash, total_assets, bankrupt)
        for pid in self._player_ids:
            pstate = state.get(pid, {})
            rows.append((
                pid,
                pstate.get("cash", 0),
                pstate.get("total_assets", 0),
                pstate.get("is_bankrupt", False),
            ))
        rows.sort(key=lambda r: (r[3], -r[2]))   # bankrupt last, then highest assets first

        row_h   = font_body.get_linesize() + 6
        head_h  = font_head.get_linesize() + 4
        pad     = 16
        col_w   = 200
        n_cols  = 4   # Hạng | Người chơi | Tài sản | Tiền mặt
        box_w   = col_w * n_cols + pad * 2
        box_h   = head_h + pad * 2 + row_h * (len(rows) + 1) + 28  # +1 for column header
        box_x   = (_WIN_W - box_w) // 2
        box_y   = (_WIN_H - box_h) // 2

        # Semi-transparent background
        surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        surf.fill((10, 10, 30, 230))
        screen.blit(surf, (box_x, box_y))
        pygame.draw.rect(screen, (100, 160, 255), (box_x, box_y, box_w, box_h), 2)

        # Title
        title = font_head.render("KẾT THÚC — BẢNG XẾP HẠNG", True, (255, 215, 0))
        screen.blit(title, title.get_rect(centerx=box_x + box_w // 2, top=box_y + pad))

        # Column headers
        hdr_y = box_y + pad + head_h + 4
        for ci, hdr in enumerate(["HẠNG", "NGƯỜI CHƠI", "TỔNG TÀI SẢN", "TIỀN MẶT"]):
            hsurf = font_body.render(hdr, True, (140, 180, 255))
            screen.blit(hsurf, (box_x + pad + ci * col_w, hdr_y))

        # Separator line
        sep_y = hdr_y + row_h - 2
        pygame.draw.line(screen, (80, 100, 180),
                         (box_x + pad, sep_y), (box_x + box_w - pad, sep_y))

        # Player rows
        for rank, (pid, cash, assets, bankrupt) in enumerate(rows):
            ry = sep_y + 4 + rank * row_h
            color = self._RANK_COLORS[min(rank, len(self._RANK_COLORS) - 1)]
            if bankrupt:
                color = (100, 100, 100)

            # Highlight winner row
            if rank == 0 and not bankrupt:
                hl = pygame.Surface((box_w - pad * 2, row_h), pygame.SRCALPHA)
                hl.fill((255, 215, 0, 30))
                screen.blit(hl, (box_x + pad, ry))

            medal = self._RANK_MEDALS[min(rank, len(self._RANK_MEDALS) - 1)]
            cells = [
                f"#{medal}",
                pid,
                f"{assets:,}",
                f"{cash:,}",
            ]
            for ci, text in enumerate(cells):
                if bankrupt and ci == 1:
                    text += " (phá sản)"
                csurf = font_body.render(text, True, color)
                screen.blit(csurf, (box_x + pad + ci * col_w, ry))

        # Footer hint
        hint = font_body.render("Đóng cửa sổ để thoát", True, (100, 100, 140))
        screen.blit(hint, hint.get_rect(
            centerx=box_x + box_w // 2,
            bottom=box_y + box_h - 6
        ))
