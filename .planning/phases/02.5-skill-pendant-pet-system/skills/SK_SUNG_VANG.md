# Skill: Sừng Vàng

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_SUNG_VANG |
| Name | Sừng Vàng |
| Trigger | RESOLVE_TILE phase — khi di chuyển đến ô có đối thủ đang đứng |

## Effect

### Effect 1 — Luôn xảy ra (100%)
Lấy **15% tiền hiện tại** của đối thủ đang đứng tại ô đó.

```
stolen = opponent.cash * 0.15
opponent.cash -= stolen
player.cash += stolen
```

### Effect 2 — Theo rate
Activation: `random(0, 100) < rate_at_star`

Đẩy đối thủ đến **ô đắt nhất** (highest total invested build cost) trong danh sách property của player.
- Tile effect tại ô đó xảy ra bình thường (đối thủ phải trả toll)

### Phong toả tương tác (áp dụng suốt lần tương tác này)
Trong toàn bộ lần tương tác Sừng Vàng:
- Đối thủ **không thể active skill** để counter
- Đối thủ **không thể dùng thẻ** (held card) để counter

Sau khi tương tác kết thúc → đối thủ hoạt động bình thường trở lại.

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 28%         | +2%             | 36%         |
| S    | 1★       | 38%         | +3%             | 50%         |
| R    | —        | dùng config S | —             | 50% (S5★)  |

## Activation Formula

```
# Effect 1 luôn xảy ra khi trigger
stolen = opponent.cash * 0.15
transfer(opponent, player, stolen)

# Effect 2 theo rate
rate_at_star = base_rate + (current_star - min_star) * chance
if random(0, 100) < rate_at_star:
    target_tile = max(player.owned_properties, key=lambda p: calc_invested_build_cost(board, p))
    opponent.move_to(target_tile)
    resolve_tile(opponent, target_tile)  # tile effect bình thường
```

## Notes

- "Ô đắt nhất" = ô có `calc_invested_build_cost` cao nhất trong `player.owned_properties`
- Nếu player không có property → Effect 2 skip (không có ô để đẩy)
- Phong toả chỉ áp dụng trong scope của event này, không persist sang lượt sau
- Stub AI: không cần logic đặc biệt — skill trigger tự động
