# Skill: Phá Hủy

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_PHA_HUY |
| Name | Phá Hủy |
| Trigger | MOVE phase — khi **đi qua** ô property của đối thủ (on_pass, không phải on_land) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active:

1. **Xóa hoàn toàn nhà** — ô đất về trạng thái trống (`tile.building_level = 0`, `tile.owner_id = None`)
2. **Nhận 50% tổng tiền đã đầu tư** vào ô đó:

```
invested = calc_invested_build_cost(board, tile.position)
player.cash += invested * 0.5

tile.building_level = 0
tile.owner_id = None
opponent.remove_property(tile.position)
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 14%         | +1%             | 18%         |
| S    | 1★       | 20%         | +1%             | 24%         |
| R    | —        | dùng config S | —             | 24% (S5★)  |

## Notes

- Trigger khi **đi qua** (mid-path), không phải khi dừng lại tại ô
- Ô trở thành đất trống hoàn toàn — không còn chủ, level = 0
- **Chain với SK_CAM_CO**: ngay sau khi PhaHuy phá xong → tile trống → CắmCờ check ngay tại ô đó (trong cùng lượt di chuyển)
- `calc_invested_build_cost()` đã có sẵn trong `ctp/core/constants.py`
- Stub AI: không cần logic đặc biệt
