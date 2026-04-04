"""InfoPanel — draws the right-side info panel: speed indicator, player info, event log.

Panel region: x 853–1280, y 0–720 (427 × 720 px).
Rendering is stateless: receives a ui_state snapshot and paints each frame.

Layout (top to bottom):
    [0–28]    Speed indicator row
    [28–228]  Player info section — 2×2 grid (4 cells of 213×100 px)
    [228–720] Event log section (scrollable, ~30 visible lines)
"""
from __future__ import annotations

import pygame
from ctp.ui.speed_controller import SPEED_LABELS

# ── Panel geometry constants (pixels) ────────────────────────────────
PANEL_X      = 853    # left edge of panel
PANEL_W      = 427    # panel width (1280 - 853)
PANEL_H      = 720    # panel height
SPEED_H      = 28     # speed indicator row height
CELL_W       = PANEL_W // 2   # 213 — grid cell width
CELL_H       = 100             # grid cell height
INFO_H       = CELL_H * 2     # 200 — total player info height (2 rows)
LOG_Y        = SPEED_H + INFO_H   # y=228
LOG_H        = PANEL_H - LOG_Y    # 492 — event log height

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

        # ── Player info blocks — 2×2 grid ───────────────────────────
        active_pid = ui_state.get("active_player_id", "")
        active_players = [p for p in player_ids if p in ui_state]
        # Grid positions: (col, row) for player index 0-3
        _GRID = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for idx, pid in enumerate(active_players[:4]):
            col, row = _GRID[idx]
            cell_x = PANEL_X + col * CELL_W
            cell_y = SPEED_H + row * CELL_H
            self._draw_player_cell(
                screen, pid, ui_state[pid],
                cell_x, cell_y, CELL_W, CELL_H,
                is_active=(pid == active_pid),
                font_body=font_body,
                font_heading=font_heading,
            )

        # Grid lines between cells
        mid_x = PANEL_X + CELL_W
        mid_y = SPEED_H + CELL_H
        pygame.draw.line(screen, _C_DIVIDER, (mid_x, SPEED_H), (mid_x, LOG_Y), 1)
        pygame.draw.line(screen, _C_DIVIDER, (PANEL_X, mid_y), (PANEL_X + PANEL_W, mid_y), 1)

        # ── Divider above event log ───────────────────────────────────
        pygame.draw.line(screen, _C_DIVIDER,
                         (PANEL_X, LOG_Y), (PANEL_X + PANEL_W, LOG_Y), 2)

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

    def _draw_player_cell(
        self,
        screen: pygame.Surface,
        pid: str,
        pdata: dict,
        cell_x: int,
        cell_y: int,
        cell_w: int,
        cell_h: int,
        is_active: bool,
        font_body: pygame.font.Font,
        font_heading: pygame.font.Font,
    ) -> None:
        """Draw one player info cell in the 2×2 grid.

        Layout (3 lines inside CELL_H=100px):
            Line 1: "{pid}" heading + [PHA SAN] if bankrupt
            Line 2: "Tien: ${cash:,}"
            Line 3: "TS: ${total_assets:,}"
        """
        is_bankrupt = pdata.get("is_bankrupt", False)
        cash = int(pdata.get("cash", 0))
        total_assets = int(pdata.get("total_assets", 0))
        pad = 8

        # Active player highlight background
        if is_active and not is_bankrupt:
            pygame.draw.rect(screen, _C_ACTIVE_BG, (cell_x, cell_y, cell_w, cell_h))

        # Three lines at fixed y offsets within the cell
        y1 = cell_y + 20
        y2 = cell_y + 48
        y3 = cell_y + 72

        # Line 1: player name + bankrupt badge
        name_color = _C_BANKRUPT_TEXT if is_bankrupt else (
            _C_ACTIVE_TEXT if is_active else _C_TEXT
        )
        name_surf = font_heading.render(f"Nguoi choi {pid}", True, name_color)
        screen.blit(name_surf, (cell_x + pad, y1 - name_surf.get_height() // 2))
        if is_bankrupt:
            badge = font_body.render("[PHA SAN]", True, _C_BANKRUPT_LABEL)
            screen.blit(badge, (cell_x + pad, y1 + name_surf.get_height() // 2 - 2))

        # Line 2: cash
        cash_color = _C_BANKRUPT_TEXT if is_bankrupt else _C_TEXT
        cash_surf = font_body.render(f"Tien: ${cash:,}", True, cash_color)
        screen.blit(cash_surf, (cell_x + pad, y2 - cash_surf.get_height() // 2))

        # Line 3: total assets (abbreviated label to fit cell width)
        assets_surf = font_body.render(f"TS: ${total_assets:,}", True, cash_color)
        screen.blit(assets_surf, (cell_x + pad, y3 - assets_surf.get_height() // 2))

    def _draw_event_log(
        self,
        screen: pygame.Surface,
        ui_state: dict,
        font: pygame.font.Font,
    ) -> None:
        """Draw event log section (scrollable, LOG_H px tall)."""
        pygame.draw.rect(screen, _C_LOG_BG, (PANEL_X, LOG_Y, PANEL_W, LOG_H))

        lines = list(ui_state.get("event_log", []))
        scroll = int(ui_state.get("log_scroll", 0))

        max_lines = (LOG_H - 24) // _LOG_LINE_H  # reserve top 20px for scroll header
        total = len(lines)

        # Clamp scroll: 0 = newest at bottom, N = scroll up N lines
        max_scroll = max(0, total - max_lines)
        scroll = min(scroll, max_scroll)

        # Select slice to display
        if scroll > 0:
            end = total - scroll
            start = max(0, end - max_lines)
            visible = lines[start:end]
        else:
            visible = lines[-max_lines:] if lines else []

        if not visible:
            visible = ["(no events yet)"]

        # Scroll indicator header
        if total > max_lines:
            remaining_above = max(0, total - max_lines - scroll)
            if scroll > 0:
                header = f"↑ {remaining_above} older  |  scroll: {scroll}/{max_scroll}"
            else:
                header = f"↑ scroll to see {total - max_lines} older lines"
            hdr_surf = font.render(header, True, (120, 120, 200))
            screen.blit(hdr_surf, (PANEL_X + 4, LOG_Y + 4))
        header_h = 20

        # Render lines
        pad_top = LOG_Y + header_h
        clip_rect = pygame.Rect(PANEL_X, LOG_Y + header_h, PANEL_W, LOG_H - header_h)
        screen.set_clip(clip_rect)
        for i, line in enumerate(visible):
            y = pad_top + i * _LOG_LINE_H
            text_surf = font.render(str(line), True, _C_LOG_TEXT)
            screen.blit(text_surf, (PANEL_X + 4, y))
        screen.set_clip(None)
