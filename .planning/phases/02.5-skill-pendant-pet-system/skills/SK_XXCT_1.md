# Skill: Xúc Xắc Chiến Thuật (1) — Điều Khiển Xúc Xắc

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_XXCT_1 |
| Name | Xúc Xắc Chiến Thuật |
| Trigger | ROLL phase — **trước khi** đổ xúc xắc |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → player **tự chọn kết quả xúc xắc** (bất kỳ số nào từ 2–12).
- Bỏ qua hoàn toàn accuracy_rate check (căn lực không được check)
- Kết quả được dùng để di chuyển bình thường

```
# Trước khi roll
if random(0, 100) < rate_at_star:
    dice_result = player_choose_dice()  # AI stub: chọn số tối ưu
    # skip accuracy check
else:
    dice_result = roll_dice()
    # accuracy check bình thường
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 12%         | +1%             | 16%         |
| S    | 1★       | 17%         | +2%             | 25%         |
| R    | —        | dùng config S | —             | 25% (S5★)  |

## Notes

- Stub AI: chọn số đưa player đến ô có lợi nhất (ô đất trống hoặc tránh ô đắt của đối thủ)
- Nếu skill không active → flow đổ xúc xắc bình thường (kể cả accuracy check)
