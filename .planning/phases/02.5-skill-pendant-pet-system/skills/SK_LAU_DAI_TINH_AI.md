# Skill: Lâu Đài Tình Ái

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_LAU_DAI_TINH_AI |
| Name | Lâu Đài Tình Ái |
| Trigger | RESOLVE_TILE phase — khi player di chuyển đến **landmark của mình** (CITY L5 / Biểu Tượng) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → chọn **1 đối thủ ngẫu nhiên** và hút họ đến ô Biểu Tượng hiện tại.
- Tile effect (toll) tại ô đó **xảy ra bình thường** với đối thủ bị hút

```
opponents = [p for p in players if p.player_id != player.player_id and not p.is_bankrupt]
if opponents:
    target = random.choice(opponents)
    target.move_to(player.position)
    resolve_tile(target, current_tile)  # trả toll bình thường
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 38%         | +2%             | 46%         |
| S    | 1★       | 48%         | +3%             | 60%         |
| R    | —        | dùng config S | —             | 60% (S5★)  |

## Notes

- Chỉ trigger khi đến **ô L5 của chính mình** (không trigger tại L5 của đối thủ)
- Đối thủ bị hút: random 1 người trong số còn sống, không phân biệt vị trí
- Đối thủ bị hút vẫn có thể dùng thẻ/skill để counter toll bình thường
- Stub AI: không cần logic đặc biệt
