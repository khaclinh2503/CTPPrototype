# Skill: Moonwalk

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_MOONWALK |
| Name | Moonwalk |
| Trigger | ROLL phase — sau khi đổ xúc xắc |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → player được **chọn hướng di chuyển**:
- **Tiến** — di chuyển theo chiều bình thường (forward) số bước bằng kết quả xúc xắc
- **Lùi** — di chuyển ngược chiều (backward) số bước bằng kết quả xúc xắc

```
if random(0, 100) < rate_at_star:
    direction = player_choose_direction()  # "forward" hoặc "backward"
    if direction == "backward":
        player.move_backward(dice_result)  # wrap around board
    else:
        player.move_forward(dice_result)   # bình thường
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 15%         | +2%             | 23%         |
| S    | 1★       | 25%         | +5%             | 45%         |
| R    | —        | dùng config S | —             | 45% (S5★)  |

## Notes

- Di chuyển lùi wrap around board (vị trí 1 → 32 → 31...)
- Di chuyển lùi **không nhận thưởng qua START** (chỉ tiến mới nhận)
- Stub AI: chọn hướng có lợi hơn (ô đến có giá trị cao hơn)
- **Kết hợp với SK_XE_DO**: chọn parity (chẵn/lẻ) + chọn hướng → tiến hoặc lùi bằng số cùng parity
- **Kết hợp với SK_XXCT**: dice±1 × 2 hướng → player chọn 1 trong 4 ô đến
- **Không kết hợp 3 skill** (XeĐộ + XXCT + Moonwalk): không có tổ hợp này
