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

                    if move_type == 1 and old_pos is not None:
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
