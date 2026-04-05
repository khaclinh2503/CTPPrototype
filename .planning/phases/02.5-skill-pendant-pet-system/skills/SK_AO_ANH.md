# Skill: Ảo Ảnh

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_AO_ANH |
| Name | Ảo Ảnh |
| Trigger | UPGRADE phase (khi xây nhà) HOẶC RESOLVE_TILE phase (khi đứng vào landmark của mình) |

## Effect

Nếu skill active → đặt **1 bẫy ảo ảnh** tại ô hiện tại (ô đang xây / đang đứng).

### Quy tắc ảo ảnh

- **Toàn map chỉ có 1 ảo ảnh** tại một thời điểm — tạo mới sẽ xoá cái cũ (dù chủ cũ là ai)
- Khi player khác di chuyển và **đi qua / dừng tại ô có ảo ảnh** → dừng lại tại ô đó, kết thúc di chuyển
- **Tile effect vẫn xảy ra bình thường** (ví dụ: đất của người tạo → vẫn trả toll)
- Sau khi triggered → ảo ảnh biến mất
- **Không có tác dụng** với player tạo ra nó

### Board State

Cần thêm field vào Board: `illusion_position: int | None = None` (vị trí ô có ảo ảnh, None = không có).

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 50%         | +2%             | 58%         |
| S    | 1★       | 60%         | +3%             | 72%         |
| R    | —        | dùng config S | —             | 72% (S5★)  |

## Activation Formula

```
rate_at_star = base_rate + (current_star - min_star) * chance
if random(0, 100) < rate_at_star:
    board.illusion_position = current_tile.position
```

## Notes

- Ảo ảnh chặn movement mid-path (player không đi tiếp dù còn bước)
- Cần check `board.illusion_position` trong MOVE phase sau mỗi bước di chuyển
- Stub AI: không cần logic đặc biệt — skill trigger tự động
