# Skill: Hộp Quà Xúc Xắc

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_HQXX |
| Name | Hộp Quà Xúc Xắc |
| Trigger | RESOLVE_TILE phase — khi di chuyển đến ô bất kỳ |

## Effect (tất cả active cùng lúc)

Activation: `random(0, 100) < rate_at_star`

Nếu active → 3 effect xảy ra đồng thời:

1. **Thêm 1 lượt đi** — player được đổ xúc xắc và di chuyển thêm 1 lượt ngay sau lượt hiện tại
2. **Đẩy đối thủ cùng hàng vào tù** — tất cả đối thủ đang đứng trên **cùng cạnh bàn cờ** với ô player vừa đến → `opponent.enter_prison()`
3. **Reset số lần đổ đôi** — `player.consecutive_doubles = 0`

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 20%         | +1%             | 24%         |
| S    | 1★       | 25%         | +2%             | 33%         |
| R    | —        | dùng config S | —             | 33% (S5★)  |

## Notes

- "Cùng hàng" = cùng cạnh bàn cờ với ô player vừa di chuyển đến
- Nếu không có đối thủ nào cùng cạnh → effect 2 skip, effect 1 và 3 vẫn xảy ra
- Reset doubles: `player.consecutive_doubles = 0` (tránh bị tù do đổ đôi 3 lần liên tiếp)
- Lượt thêm xử lý ngay sau RESOLVE_TILE hiện tại kết thúc
- Stub AI: không cần logic đặc biệt
