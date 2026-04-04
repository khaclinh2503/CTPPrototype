"""InfoPanel — draws the right-side info panel: speed indicator, player info, event log.

Panel region: x 853–1280, y 0–720 (427 × 720 px).
Rendering is stateless: receives a ui_state snapshot and paints each frame.

Layout (top to bottom):
    [0–28]    Speed indicator row
    [28–540]  Player info section (2-4 player blocks stacked vertically)
    [540–720] Event log section (last 10 events)
"""
from __future__ import annotations

import pygame
from ctp.ui.speed_controller import SPEED_LABELS

# ── Panel geometry constants (pixels) ────────────────────────────────
PANEL_X      = 853    # left edge of panel
PANEL_W      = 427    # panel width (1280 - 853)
PANEL_H      = 720    # panel height
SPEED_H      = 28     # speed indicator row height
LOG_H        = 180    # event log section height
LOG_Y        = PANEL_H - LOG_H          # y=540
INFO_H       = PANEL_H - SPEED_H - LOG_H  # y=512 height for player info

# ── Colours (per UI-SPEC Color section) ──────────────────────────────
_C_PANEL_BG       = ( 45,  45,  45)
_C_SPEED_BG       = ( 50,  50,  50)
_C_DIVIDER        = ( 80,  80,  80)
_C_ACTIVE_BG      = ( 60,  80, 110)
_C_LOG_BG         = ( 35,  35,  35)
_C_TEXT           = (220, 220, 220)
_C_ACTIVE_TEXT    = (255, 255, 180)
_C_BANKRUPT_TEXT  = (120, 120, 120)
_C_BANKRUPT_LABEL = (200,  80,  80)
_C_SPEED_PAUSED   = (200,  80,  80)
_C_SPEED_RUNNING  = (180, 220, 180)
_C_LOG_TEXT       = (180, 180, 180)

# Log line height in pixels (fits 10 lines in 180px with 4px top/bottom padding)
_LOG_LINE_H = 16


class InfoPanel:
    """Renders the right info panel each frame.

    Call draw(screen, ui_state, player_ids, fonts) from the main thread.
    No state stored between frames — caller passes snapshot each time.
    """

    def draw(
        self,
        screen: pygame.Surface,
        ui_state: dict,
        player_ids: list[str],
        font_body: pygame.font.Font,
        font_heading: pygame.font.Font,
    ) -> None:
        """Draw panel contents.

        Args:
            screen: Target pygame Surface (main window).
            ui_state: Shared state snapshot (player dicts, event_log, active_player_id, speed).
            player_ids: Ordered list of player IDs (e.g. ['A', 'B', 'C', 'D']).
            font_body: SysFont(None, 18) for body text.
            font_heading: SysFont(None, 22) for headings and speed indicator.
        """
        # ── Panel background ─────────────────────────────────────────
        pygame.draw.rect(screen, _C_PANEL_BG,
                         (PANEL_X, 0, PANEL_W, PANEL_H))

        # ── Speed indicator ──────────────────────────────────────────
        self._draw_speed_indicator(screen, ui_state, font_heading)

        # ── Player info blocks ───────────────────────────────────────
        active_pid = ui_state.get("active_player_id", "")
        active_players = [p for p in player_ids if p in ui_state]
        num = max(len(active_players), 1)
        block_h = INFO_H // num   # e.g. 128 for 4 players → actually (512/4)=128

        for idx, pid in enumerate(active_players):
            y_top = SPEED_H + idx * block_h
            self._draw_player_block(
                screen, pid, ui_state[pid],
                y_top, block_h,
                is_active=(pid == active_pid),
                font_body=font_body,
                font_heading=font_heading,
            )
            # Separator line between player blocks
            if idx < num - 1:
                pygame.draw.line(screen, _C_DIVIDER,
                                 (PANEL_X, y_top + block_h),
                                 (PANEL_X + PANEL_W, y_top + block_h), 1)

        # ── Divider above event log ───────────────────────────────────
        pygame.draw.line(screen, _C_DIVIDER,
                         (PANEL_X, LOG_Y), (PANEL_X + PANEL_W, LOG_Y), 1)

        # ── Event log ────────────────────────────────────────────────
        self._draw_event_log(screen, ui_state, font_body)

    # ── Private helpers ───────────────────────────────────────────────

    def _draw_speed_indicator(
        self,
        screen: pygame.Surface,
        ui_state: dict,
        font: pygame.font.Font,
    ) -> None:
        """Draw speed indicator row at top of panel."""
        speed = ui_state.get("speed", "1x")
        label = SPEED_LABELS.get(speed, f"[{speed}]")
        color = _C_SPEED_PAUSED if speed == "pause" else _C_SPEED_RUNNING

        pygame.draw.rect(screen, _C_SPEED_BG, (PANEL_X, 0, PANEL_W, SPEED_H))

        surf = font.render(label, True, color)
        rect = surf.get_rect(center=(PANEL_X + PANEL_W // 2, SPEED_H // 2))
        screen.blit(surf, rect)

    def _draw_player_block(
        self,
        screen: pygame.Surface,
        pid: str,
        pdata: dict,
        y_top: int,
        block_h: int,
        is_active: bool,
        font_body: pygame.font.Font,
        font_heading: pygame.font.Font,
    ) -> None:
        """Draw one player info block.

        Lines rendered (from UI-SPEC D-07):
            Line 1: "{letter} — Nguoi choi {letter}" (font_heading=22)
            Line 2: "Tien: ${cash:,}"                 (font_body=18)
            Line 3: "Tai san: ${total_assets:,}"       (font_body=18)
        """
        is_bankrupt = pdata.get("is_bankrupt", False)
        cash = int(pdata.get("cash", 0))
        total_assets = int(pdata.get("total_assets", 0))
        pad = 16   # md spacing from UI-SPEC

        # Active player highlight background
        if is_active and not is_bankrupt:
            pygame.draw.rect(screen, _C_ACTIVE_BG,
                             (PANEL_X, y_top, PANEL_W, block_h))

        # Vertical centre of block for text placement
        # Three text lines: heading at 1/4, cash at 2/4, assets at 3/4
        line_positions = [
            y_top + block_h // 4,
            y_top + block_h * 2 // 4,
            y_top + block_h * 3 // 4,
        ]

        # Line 1: player name
        name_text = f"{pid} \u2014 Nguoi choi {pid}"
        name_color = _C_BANKRUPT_TEXT if is_bankrupt else (
            _C_ACTIVE_TEXT if is_active else _C_TEXT
        )
        name_surf = font_heading.render(name_text, True, name_color)
        screen.blit(name_surf, (PANEL_X + pad, line_positions[0] - name_surf.get_height() // 2))

        # Bankrupt label appended after name
        if is_bankrupt:
            label_surf = font_heading.render(" [PHA SAN]", True, _C_BANKRUPT_LABEL)
            screen.blit(label_surf,
                        (PANEL_X + pad + name_surf.get_width(),
                         line_positions[0] - label_surf.get_height() // 2))

        # Line 2: cash
        cash_color = _C_BANKRUPT_TEXT if is_bankrupt else _C_TEXT
        cash_surf = font_body.render(f"Tien: ${cash:,}", True, cash_color)
        screen.blit(cash_surf, (PANEL_X + pad, line_positions[1] - cash_surf.get_height() // 2))

        # Line 3: total assets
        assets_surf = font_body.render(f"Tai san: ${total_assets:,}", True, cash_color)
        screen.blit(assets_surf, (PANEL_X + pad, line_positions[2] - assets_surf.get_height() // 2))

    def _draw_event_log(
        self,
        screen: pygame.Surface,
        ui_state: dict,
        font: pygame.font.Font,
    ) -> None:
        """Draw event log section (bottom 180px of panel)."""
        pygame.draw.rect(screen, _C_LOG_BG,
                         (PANEL_X, LOG_Y, PANEL_W, LOG_H))

        event_log = ui_state.get("event_log", [])
        lines = list(event_log)   # deque or list — newest last

        if not lines:
            lines = ["(no events yet)"]

        # Render newest-at-bottom: show at most floor(LOG_H / _LOG_LINE_H) lines
        max_lines = LOG_H // _LOG_LINE_H
        visible = lines[-max_lines:]

        pad_top = 4
        for i, line in enumerate(visible):
            y = LOG_Y + pad_top + i * _LOG_LINE_H
            # Truncate line to fit panel width
            text = str(line)
            text_surf = font.render(text, True, _C_LOG_TEXT)
            # Clip to panel right edge
            if text_surf.get_width() > PANEL_W - 8:
                # Render with clipping
                clip_rect = pygame.Rect(PANEL_X + 4, y, PANEL_W - 8, _LOG_LINE_H)
                screen.set_clip(clip_rect)
                screen.blit(text_surf, (PANEL_X + 4, y))
                screen.set_clip(None)
            else:
                screen.blit(text_surf, (PANEL_X + 4, y))
