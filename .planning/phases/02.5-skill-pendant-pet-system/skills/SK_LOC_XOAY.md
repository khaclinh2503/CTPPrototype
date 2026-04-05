# Skill: Lốc Xoáy

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_LOC_XOAY |
| Name | Lốc Xoáy |
| Trigger | RESOLVE_TILE phase — khi di chuyển đến ô có **đối thủ đang đứng** |

## Effect Flow

```
Activation: random(0, 100) < rate_at_star
    ↓ active
Check phụ: random(0, 100) < 60
    ↓ pass
1. Đẩy đối thủ đến 1 property của player (stub: ô đắt nhất)
2. Vô hiệu hóa toàn bộ skill + thẻ của đối thủ trong lượt này
```

### Chi tiết

- **Đẩy đối thủ**: di chuyển đến ô property của player → tile effect (toll) **xảy ra bình thường**
- **Vô hiệu hóa**: trong phần còn lại của lượt hiện tại, đối thủ không thể:
  - Active bất kỳ skill nào
  - Dùng held card
  - Sau khi lượt kết thúc → trở lại bình thường

```
if random(0, 100) < rate_at_star:
    if random(0, 100) < 60:
        target_tile = max(player.owned_properties, key=lambda p: calc_invested_build_cost(board, p))
        opponent.skills_disabled_this_turn = True
        opponent.cards_disabled_this_turn = True
        opponent.move_to(target_tile)
        resolve_tile(opponent, target_tile)
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 38%         | +2%             | 46%         |
| S    | 1★       | 48%         | +3%             | 60%         |
| R    | —        | dùng config S | —             | 60% (S5★)  |

## Notes

- Secondary rate cố định 60% (không phụ thuộc rank/star)
- Cần track `skills_disabled_this_turn` và `cards_disabled_this_turn` trên Player (reset cuối lượt)
- Nếu player không có property → đẩy fail silently, disable vẫn xảy ra
- **Thứ tự với SK_SUNG_VANG**: SừngVàng effect 1 (steal cash) → LốcXoáy check → SừngVàng effect 2 (đẩy) check. Mỗi bước độc lập
- Stub AI: không cần logic đặc biệt
