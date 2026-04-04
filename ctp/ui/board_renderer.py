"""BoardRenderer — draws the 32-tile diamond board and player tokens.

Rendering is stateless: BoardRenderer receives the Board object (for tile
config) plus a ui_state snapshot each frame and paints to the given surface.

Board geometry:
    Diamond centre: (427, 360) — left 2/3 of 1280×720 window.
    Half-radius R: 280 px.
    Tile half-size s: 24 px.
    Corners: pos 1 = bottom (427,640), pos 9 = left (147,360),
             pos 17 = top (427,80), pos 25 = right (707,360).
    Traversal: clockwise 1→2→…→32 (bottom→left→top→right→bottom).
"""
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctp.core.board import Board

# ── Geometry constants ────────────────────────────────────────────────
_CX = 427          # board centre x (pixels)
_CY = 360          # board centre y (pixels)
_R  = 280          # half-radius of diamond (pixels)
_S  = 24           # tile rhombus half-size (pixels)

# ── Space type abbreviations (per UI-SPEC Tile Label Format) ──────────
_SPACE_ABBR: dict[int, str] = {
    1:  "LE",
    2:  "RUT",
    3:  "DAT",
    4:  "MG",
    5:  "TU",
    6:  "NGHI",
    7:  "XP",
    8:  "THUE",
    9:  "DL",
    10: "MAY",
    40: "TRUOT",
}

# ── Tile colours by land color group (UI-SPEC: Tile Colors — Land Groups) ──
_TILE_COLORS: dict[int, tuple[int, int, int]] = {
    0: (100, 100, 100),
    1: (255, 255, 153),
    2: (255, 204,  51),
    3: (255, 153,  51),
    4: (220,  60,  60),
    5: (200, 150, 220),
    6: (130,  60, 180),
    7: ( 70, 130, 200),
    8: ( 60, 180,  80),
}

# ── Special tile colours by SpaceId (UI-SPEC: Tile Colors — Special Spaces) ──
_SPECIAL_COLORS: dict[int, tuple[int, int, int]] = {
    7:  ( 80, 200,  80),   # START
    5:  (200,  80,  80),   # PRISON
    1:  (220, 180,  60),   # FESTIVAL
    2:  (180, 180, 255),   # CHANCE
    4:  (255, 160,  80),   # GAME
    8:  (160, 100,  60),   # TAX
    9:  ( 80, 200, 200),   # TRAVEL
    6:  (255, 200, 100),   # RESORT
    10: (255, 230, 150),   # GOD
    40: (100, 220, 240),   # WATER_SLIDE
}

# Light color groups (use dark text) — per UI-SPEC Text Colors
_LIGHT_GROUPS = {1, 2, 5}

# Player token offset map: {num_tokens: [(dx, dy), ...]}
# Per UI-SPEC Player Token Rendering
_TOKEN_OFFSETS: dict[int, list[tuple[int, int]]] = {
    1: [(0, 0)],
    2: [(-4, 0), (4, 0)],
    3: [(-4, 4), (4, 4), (0, -4)],
    4: [(-4, -4), (4, -4), (-4, 4), (4, 4)],
}


def _tile_center(pos: int) -> tuple[float, float]:
    """Compute screen pixel centre for board position pos (1–32).

    Traversal is clockwise: bottom(1) → left(9) → top(17) → right(25) → bottom.
    """
    i = (pos - 1) % 8
    side = (pos - 1) // 8
    t = i / 8
    if side == 0:   # pos 1-8: bottom → left (S→W)
        return (_CX - t * _R, _CY + _R - t * _R)
    elif side == 1: # pos 9-16: left → top (W→N)
        return (_CX - _R + t * _R, _CY - t * _R)
    elif side == 2: # pos 17-24: top → right (N→E)
        return (_CX + t * _R, _CY - _R + t * _R)
    else:           # pos 25-32: right → bottom (E→S)
        return (_CX + _R - t * _R, _CY + t * _R)


def _tile_polygon(cx: float, cy: float, s: float = _S) -> list[tuple[int, int]]:
    """4-point rhombus centred at (cx, cy) with half-size s."""
    return [
        (int(cx),     int(cy - s)),
        (int(cx + s), int(cy)),
        (int(cx),     int(cy + s)),
        (int(cx - s), int(cy)),
    ]


class BoardRenderer:
    """Renders the diamond board, tile labels, ownership tint, and player tokens.

    Call draw(screen, board, ui_state, fonts) once per frame from the main thread.
    """

    def __init__(self) -> None:
        # Precompute all 32 tile centres at construction time (geometry is static).
        self._centers: dict[int, tuple[float, float]] = {
            pos: _tile_center(pos) for pos in range(1, 33)
        }

    def draw(
        self,
        screen: pygame.Surface,
        board: "Board",
        ui_state: dict,
        font_tile: pygame.font.Font,
        font_token: pygame.font.Font,
        font_overlay: pygame.font.Font | None = None,
    ) -> None:
        """Draw all 32 tiles, center decorations, player tokens, and card overlay.

        Args:
            screen: Target pygame Surface (main window).
            board: Board instance (read tile config, space_id, owner_id, is_golden).
            ui_state: Shared state snapshot dict (positions + board_ownership).
            font_tile: SysFont(None, 14) for tile labels.
            font_token: SysFont(None, 16) for player tokens.
            font_overlay: SysFont(None, 20) for card overlay text (optional).
        """
        board_ownership: dict[int, str] = ui_state.get("board_ownership", {})

        # ── Draw tiles ────────────────────────────────────────────────
        for pos in range(1, 33):
            tile = board.get_tile(pos)
            sid = int(tile.space_id)
            cx, cy = self._centers[pos]
            poly = _tile_polygon(cx, cy)

            # Determine base fill colour
            if sid == 3:  # CITY
                cfg = board.get_land_config(tile.opt)
                color_group = cfg.get("color", 0) if cfg else 0
                fill = _TILE_COLORS.get(color_group, _TILE_COLORS[0])
                is_light = color_group in _LIGHT_GROUPS
            else:
                fill = _SPECIAL_COLORS.get(sid, (100, 100, 100))
                is_light = False

            # Ownership tint: multiply RGB by 0.7 when owned
            if pos in board_ownership:
                fill = (int(fill[0] * 0.7), int(fill[1] * 0.7), int(fill[2] * 0.7))

            pygame.draw.polygon(screen, fill, poly)

            # Golden border (3 golden tiles per game)
            if tile.is_golden:
                pygame.draw.polygon(screen, (255, 215, 0), poly, 2)
            else:
                pygame.draw.polygon(screen, (30, 30, 30), poly, 1)

            # Tile label text (two lines: position number + abbreviation)
            text_color = (30, 30, 30) if is_light else (255, 255, 255)
            abbr = _SPACE_ABBR.get(sid, str(sid))
            self._draw_centered_text(screen, font_tile, str(pos),  cx, cy - 5, text_color)
            self._draw_centered_text(screen, font_tile, abbr,      cx, cy + 7, text_color)

        # ── Draw center card pile decorations ────────────────────────
        self._draw_center_decorations(screen, font_tile)

        # ── Draw player tokens ────────────────────────────────────────
        # Group players by current position
        pos_to_players: dict[int, list[str]] = {}
        _NON_PLAYER_KEYS = {"board_ownership", "event_log", "active_player_id",
                             "speed", "log_scroll", "card_overlay"}
        player_ids = [k for k in ui_state if isinstance(k, str)
                      and k not in _NON_PLAYER_KEYS
                      and isinstance(ui_state[k], dict)]
        for pid in player_ids:
            pdata = ui_state[pid]
            if pdata.get("is_bankrupt"):
                continue   # bankrupt tokens not rendered (per UI-SPEC)
            # display_pos is set during walk animation; fall back to authoritative position
            ppos = pdata.get("display_pos") or pdata.get("position", 1)
            pos_to_players.setdefault(ppos, []).append(pid)

        for tile_pos, pids in pos_to_players.items():
            cx, cy = self._centers[tile_pos]
            offsets = _TOKEN_OFFSETS.get(len(pids), _TOKEN_OFFSETS[4])
            for idx, pid in enumerate(pids):
                dx, dy = offsets[min(idx, len(offsets) - 1)]
                self._draw_token(screen, font_token, pid, cx + dx, cy + dy)

        # ── Card overlay (on top of everything) ──────────────────────
        if ui_state.get("card_overlay") and font_overlay:
            self._draw_card_overlay(screen, ui_state["card_overlay"], font_overlay, font_tile)

    # ── Private helpers ───────────────────────────────────────────────

    def _draw_center_decorations(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
    ) -> None:
        """Draw two card-pile icons at the board centre."""
        piles = [
            (_CX - 32, _CY - 12, (70, 130, 210), "?"),   # left pile (blue)
            (_CX + 32, _CY + 12, (210, 150, 50), "?"),   # right pile (gold)
        ]
        for cx, cy, color, label in piles:
            # Shadow layers (stacked cards effect)
            for k in range(3, 0, -1):
                shadow_poly = _tile_polygon(cx + k, cy - k * 2, 18)
                shade = (max(0, color[0] - 40), max(0, color[1] - 40), max(0, color[2] - 40))
                pygame.draw.polygon(screen, shade, shadow_poly)
                pygame.draw.polygon(screen, (60, 60, 60), shadow_poly, 1)
            # Top card
            poly = _tile_polygon(cx, cy, 18)
            pygame.draw.polygon(screen, color, poly)
            pygame.draw.polygon(screen, (200, 200, 200), poly, 1)
            self._draw_centered_text(screen, font, label, cx, cy, (255, 255, 255))

    def _draw_card_overlay(
        self,
        screen: pygame.Surface,
        overlay: dict,
        font_heading: pygame.font.Font,
        font_body: pygame.font.Font,
    ) -> None:
        """Draw semi-transparent card reveal box at board centre."""
        box_w, box_h = 220, 110
        box_x = _CX - box_w // 2
        box_y = _CY - box_h // 2

        # Semi-transparent background
        surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        surf.fill((15, 20, 55, 220))
        screen.blit(surf, (box_x, box_y))
        pygame.draw.rect(screen, (100, 150, 255), (box_x, box_y, box_w, box_h), 2)

        player   = overlay.get("player", "?")
        card_id  = overlay.get("card_id", "?")
        effect   = overlay.get("effect", "?")
        content  = overlay.get("content_id", "")

        title_surf = font_heading.render("RUT THE", True, (255, 215, 0))
        screen.blit(title_surf, title_surf.get_rect(centerx=_CX, top=box_y + 8))

        line1 = font_body.render(f"{player}: {card_id}", True, (220, 220, 220))
        screen.blit(line1, line1.get_rect(centerx=_CX, top=box_y + 36))

        if content:
            line2 = font_body.render(content, True, (160, 220, 160))
            screen.blit(line2, line2.get_rect(centerx=_CX, top=box_y + 56))

        line3 = font_body.render(f"[{effect}]", True, (160, 180, 255))
        screen.blit(line3, line3.get_rect(centerx=_CX, top=box_y + 76))

        # Progress bar (shrinks over 3 seconds — purely visual)
        expires = overlay.get("expires_at", 0)
        created = overlay.get("created_at", expires - 3.0)
        import time as _t
        elapsed = _t.time() - created
        frac = max(0.0, min(1.0, 1.0 - elapsed / 3.0))
        bar_w = int((box_w - 16) * frac)
        pygame.draw.rect(screen, (80, 80, 80),  (box_x + 8, box_y + box_h - 10, box_w - 16, 6))
        pygame.draw.rect(screen, (100, 150, 255), (box_x + 8, box_y + box_h - 10, bar_w, 6))

    @staticmethod
    def _draw_centered_text(
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        cx: float,
        cy: float,
        color: tuple[int, int, int],
    ) -> None:
        """Render text centred at (cx, cy)."""
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(int(cx), int(cy)))
        surface.blit(surf, rect)

    @staticmethod
    def _draw_token(
        surface: pygame.Surface,
        font: pygame.font.Font,
        letter: str,
        cx: float,
        cy: float,
    ) -> None:
        """Render player token letter with dark outline for contrast."""
        # Dark outline (1px offset in 4 directions)
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            outline = font.render(letter, True, (30, 30, 30))
            rect = outline.get_rect(center=(int(cx) + ox, int(cy) + oy))
            surface.blit(outline, rect)
        # White letter on top
        surf = font.render(letter, True, (255, 255, 255))
        rect = surf.get_rect(center=(int(cx), int(cy)))
        surface.blit(surf, rect)
