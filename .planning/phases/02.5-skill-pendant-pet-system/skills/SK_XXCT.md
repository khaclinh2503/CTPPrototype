# Skill: Xúc Xắc Chiến Thuật — Tiến Lùi 1 Ô

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_XXCT |
| Name | Xúc Xắc Chiến Thuật |
| Trigger | ROLL phase — **sau khi** đổ xúc xắc (có kết quả rồi) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → player được **chọn điều chỉnh ±1** so với kết quả xúc xắc:
- **Tiến thêm 1** — di chuyển `dice_result + 1` bước
- **Lùi 1** — di chuyển `dice_result - 1` bước
- **Giữ nguyên** — di chuyển `dice_result` bình thường

```
if random(0, 100) < rate_at_star:
    adjustment = player_choose(-1, 0, +1)  # AI stub: chọn điều chỉnh tối ưu
    final_steps = dice_result + adjustment
else:
    final_steps = dice_result
player.move_forward(final_steps)
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

- Check sau khi đã có kết quả xúc xắc
- `dice_result - 1` tối thiểu = 1 (không thể di chuyển 0 hoặc âm bước)
- **Không bypass PET_TROI_CHAN**: khi bị bind, điều kiện thoát là kết quả xúc xắc gốc phải chẵn — XXCT_2 điều chỉnh sau không được tính
- **Kết hợp với SK_MOONWALK**: dice±1 × 2 hướng → player chọn 1 trong 4 ô đến
- **Không kết hợp với SK_XE_DO**: hai skill này không tổ hợp với nhau
- Stub AI: chọn điều chỉnh đưa đến ô có lợi nhất
