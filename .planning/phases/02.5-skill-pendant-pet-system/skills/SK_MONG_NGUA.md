# Skill: Móng Ngựa

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_MONG_NGUA |
| Name | Móng Ngựa |
| Trigger | UPGRADE phase — khi xây Biểu Tượng (nâng lên L5 max level) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → lấy **Resort tile cùng cạnh bàn cờ** với ô vừa xây Biểu Tượng:

| Trạng thái Resort | Hành động |
|-------------------|-----------|
| Chưa có chủ | Lấy miễn phí (player trở thành chủ) |
| Của đối thủ | Cướp — chỉ đổi chủ, giữ nguyên level |
| Của chính player | Không có tác dụng |
| Không tồn tại trên cạnh đó | Skill fail silently |

### Lưu ý Resort
- Resort chỉ có **1 cấp** (không có upgrade level)
- Khi cướp: chỉ `tile.owner_id = player.player_id`, không thay đổi gì khác

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 36%         | +2%             | 44%         |
| S    | 1★       | 46%         | +3%             | 58%         |
| R    | —        | dùng config S | —             | 58% (S5★)  |

## Activation Formula

```
# Chỉ trigger khi nâng cấp lên đúng L5
if new_level == 5:
    rate_at_star = base_rate + (current_star - min_star) * chance
    if random(0, 100) < rate_at_star:
        side = get_board_side(current_tile.position)
        resort = find_resort_on_side(board, side)
        if resort and resort.owner_id != player.player_id:
            resort.owner_id = player.player_id
```

## Notes

- "Cùng cạnh" = cùng 1 trong 4 cạnh của bàn cờ hình thoi
- `find_resort_on_side()` cần biết layout cạnh bàn cờ từ Board.json
- Stub AI: không cần logic đặc biệt — skill trigger tự động
