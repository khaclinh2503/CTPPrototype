# Skill: Búa Sét

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_BUA_SET |
| Name | Búa Sét |
| Trigger | RESOLVE_TILE phase — khi dừng tại **đất của đối thủ** (lúc phải trả toll) |

## Effect Flow

Activation: `random(0, 100) < rate_at_star`

Nếu active:

1. **Miễn toll** — không trả tiền tham quan lần này
2. **Acquisition & Upgrade vẫn diễn ra bình thường** — player vẫn có thể mua lại đất và nâng cấp theo luật thông thường
3. **Sau khi hoàn tất acquisition/upgrade** → di chuyển đến **ô CITY trống gần nhất** từ vị trí hiện tại
   - Tile effect tại ô đến **không trigger** (chỉ repositioned)

```
if random(0, 100) < rate_at_star:
    waive_toll()
    # acquisition & upgrade flow diễn ra bình thường
    handle_acquisition(player, tile)
    handle_upgrade(player)
    # sau đó di chuyển
    nearest_empty = find_nearest_unowned_city(board, player.position)
    if nearest_empty:
        player.move_to(nearest_empty.position)
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 25%         | +1%             | 29%         |
| S    | 1★       | 30%         | +2%             | 38%         |
| R    | —        | dùng config S | —             | 38% (S5★)  |

## Notes

- Miễn toll không ảnh hưởng đến acquisition — player vẫn phải trả acquisition price nếu mua
- "Gần nhất" = ô CITY unowned gần nhất tính từ vị trí sau acquisition
- Nếu không còn ô CITY trống → effect 3 skip (không di chuyển thêm)
- Stub AI: luôn mua nếu đủ tiền, luôn nâng cấp nếu đủ tiền
