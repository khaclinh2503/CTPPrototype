# Skill: Biển Cấm

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_BIEN_CAM |
| Name | Biển Cấm |
| Trigger | UPGRADE phase (nâng lên L5) HOẶC RESOLVE_TILE phase (dừng tại Biểu Tượng L5 của mình) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → player **chọn 1 ô bất kỳ** trên map để đặt biển báo dừng.

### Quy tắc biển báo

- **Toàn map chỉ có 1 biển báo** tại một thời điểm — tạo mới xoá cái cũ (dù chủ cũ là ai)
- **Cả đối thủ lẫn người tạo** đi vào ô đó đều bị chặn lại (dừng tại ô đó, kết thúc di chuyển)
- Biển báo **tồn tại mãi mãi** cho đến khi bị trigger
- Sau khi 1 player (bất kỳ) bước vào → biển báo **biến mất**
- Tile effect tại ô đó **vẫn xảy ra bình thường**

### Board State

Cần thêm field vào Board: `stop_sign_position: int | None = None`

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 45%         | +2%             | 53%         |
| S    | 1★       | 55%         | +3%             | 67%         |
| R    | —        | dùng config S | —             | 67% (S5★)  |

## Activation Formula

```
rate_at_star = base_rate + (current_star - min_star) * chance
if random(0, 100) < rate_at_star:
    chosen_pos = player_choose_position()  # AI stub: chọn ô đắt nhất của mình
    board.stop_sign_position = chosen_pos
```

## Notes

- Khác Ảo Ảnh: biển cấm ảnh hưởng cả người tạo, không miễn trừ
- Biển báo tồn tại vô thời hạn — không decay theo lượt
- Cần check `board.stop_sign_position` trong MOVE phase sau mỗi bước (tương tự Ảo Ảnh)
- Stub AI: đặt tại ô property đắt nhất của đối thủ
