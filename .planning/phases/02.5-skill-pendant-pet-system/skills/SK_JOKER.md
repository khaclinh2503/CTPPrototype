# Skill: Joker

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_JOKER |
| Name | Joker |
| Trigger | Khi player bị **vào tù** (enter prison) |

## Effect — 2 trường hợp

Activation: `random(0, 100) < rate_at_star` (check ngay khi vào tù)

---

### TH1: Vào tù trong lượt của mình
Nếu active → 3 effect xảy ra ngay lập tức:

1. **Thoát tù** — `player.exit_prison()`
2. **Chọn ô đất trống bất kỳ** — di chuyển đến 1 CITY tile chưa có chủ (tile effect không trigger)
3. **Đổ thêm 1 lượt** — đổ xúc xắc và di chuyển thêm ngay

---

### TH2: Vào tù ngoài lượt của mình (bị đẩy bởi skill/card đối thủ)
Nếu active → chỉ effect ngay:

1. **Thoát tù** — `player.exit_prison()`

Đến **lượt tiếp theo của player**:

2. **Chọn ô đất trống bất kỳ** — di chuyển đến 1 CITY tile chưa có chủ (tile effect không trigger)
3. **Đổ thêm 1 lượt** — đổ xúc xắc và di chuyển thêm

```
# Cần track pending reward
if random(0, 100) < rate_at_star:
    player.exit_prison()
    if is_player_turn:
        move_to_chosen_unowned_city(player)
        grant_extra_roll(player)
    else:
        player.joker_pending = True  # xử lý đầu lượt tiếp theo
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 50%         | +2%             | 58%         |
| S    | 1★       | 60%         | +3%             | 72%         |
| R    | —        | dùng config S | —             | 72% (S5★)  |

## Notes

- Trigger tại thời điểm **vào tù** (không phải đầu lượt trong tù)
- Nếu không có ô CITY trống → effect 2 skip, effect 1 và 3 vẫn xảy ra
- Stub AI: chọn ô CITY trống gần vị trí hiện tại nhất
- Lượt thêm xử lý ngay sau khi player được repositioned
