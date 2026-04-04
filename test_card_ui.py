"""Card UI preview tool — cycle qua từng thẻ để kiểm tra popup.

Chạy: python test_card_ui.py

Controls:
  → / Space   : thẻ tiếp theo
  ←           : thẻ trước đó
  Q / Esc     : thoát
"""
import time
import pygame
from ctp.ui.board_renderer import BoardRenderer, _CX, _CY
from ctp.ui.game_view import _CARD_NAMES, _CARD_DESCS

# Danh sách tất cả thẻ theo thứ tự
_ALL_CARDS = [
    "IT_CA_1",  "IT_CA_2",  "IT_CA_3",  "IT_CA_4",  "IT_CA_5",
    "IT_CA_6",  "IT_CA_7",  "IT_CA_8",  "IT_CA_9",  "IT_CA_10",
    "IT_CA_11", "IT_CA_12", "IT_CA_13", "IT_CA_14", "IT_CA_15",
    "IT_CA_16", "IT_CA_17", "IT_CA_18", "IT_CA_19", "IT_CA_20",
    "IT_CA_21", "IT_CA_22", "IT_CA_23", "IT_CA_24", "IT_CA_25",
    "IT_CA_29", "IT_CA_30",
]

_EFFECT_MAP = {
    "IT_CA_1":  "EF_20", "IT_CA_2":  "EF_2",  "IT_CA_3":  "EF_3",
    "IT_CA_4":  "EF_4",  "IT_CA_5":  "EF_5",  "IT_CA_6":  "EF_6",
    "IT_CA_7":  "EF_6",  "IT_CA_8":  "EF_7",  "IT_CA_9":  "EF_8",
    "IT_CA_10": "EF_7",  "IT_CA_11": "EF_26", "IT_CA_12": "EF_10",
    "IT_CA_13": "EF_11", "IT_CA_14": "EF_13", "IT_CA_15": "EF_12",
    "IT_CA_16": "EF_14", "IT_CA_17": "EF_15", "IT_CA_18": "EF_16",
    "IT_CA_19": "EF_17", "IT_CA_20": "EF_18", "IT_CA_21": "EF_19",
    "IT_CA_22": "EF_21", "IT_CA_23": "EF_22", "IT_CA_24": "EF_24",
    "IT_CA_25": "EF_25", "IT_CA_29": "EF_29", "IT_CA_30": "EF_30",
}

_WIN_W, _WIN_H = 860, 720
_BG = (30, 30, 30)
_FPS = 60


def _make_overlay(card_id: str, player: str = "A") -> dict:
    now = time.time()
    return {
        "player":     player,
        "card_id":    card_id,
        "effect":     _EFFECT_MAP.get(card_id, "?"),
        "card_name":  _CARD_NAMES.get(card_id, card_id),
        "card_desc":  _CARD_DESCS.get(card_id, ""),
        "created_at": now,
        "expires_at": now + 999.0,   # không tự tắt khi test
    }


def main():
    pygame.init()
    screen = pygame.display.set_mode((_WIN_W, _WIN_H))
    pygame.display.set_caption("Card UI Preview")
    clock = pygame.time.Clock()

    import os as _os
    _FONT_PATH = _os.path.join(_os.path.dirname(__file__), "ctp", "font_game.ttf")
    font_tile    = pygame.font.Font(_FONT_PATH, 11)
    font_token   = pygame.font.Font(_FONT_PATH, 12)
    font_body    = pygame.font.Font(_FONT_PATH, 13)
    font_heading = pygame.font.Font(_FONT_PATH, 16)
    font_overlay = pygame.font.Font(_FONT_PATH, 15)
    font_ui      = pygame.font.Font(_FONT_PATH, 16)

    renderer = BoardRenderer()

    idx = 0
    total = len(_ALL_CARDS)
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                    idx = (idx + 1) % total
                elif event.key == pygame.K_LEFT:
                    idx = (idx - 1) % total
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False

        card_id = _ALL_CARDS[idx]
        overlay = _make_overlay(card_id)

        # Minimal ui_state: just enough for BoardRenderer.draw()
        ui_state = {
            "board_ownership": {},
            "event_log":       [],
            "active_player_id": "A",
            "speed":            "1x",
            "log_scroll":       0,
            "dice_display":     None,
            "dice_anim_pid":    "",
            "card_overlay":     overlay,
        }

        screen.fill(_BG)

        # Draw an empty board (no real Board object — skip tile/token rendering,
        # just draw the overlay directly)
        renderer._draw_card_overlay(screen, overlay, font_overlay, font_body)

        # Navigation hint (top-left)
        hint = font_ui.render(
            f"The {idx + 1}/{total}   ←  →/Space  Q=thoat",
            True, (180, 180, 180)
        )
        screen.blit(hint, (20, 20))

        # Card list on the left (highlight current)
        list_x, list_y = 20, 60
        for i, cid in enumerate(_ALL_CARDS):
            color = (255, 230, 80) if i == idx else (130, 130, 130)
            name = _CARD_NAMES.get(cid, cid)
            line = font_body.render(f"{cid}  {name}", True, color)
            screen.blit(line, (list_x, list_y + i * 22))

        pygame.display.flip()
        clock.tick(_FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
