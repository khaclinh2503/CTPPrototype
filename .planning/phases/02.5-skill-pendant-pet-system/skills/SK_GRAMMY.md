# Skill: Grammy

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_GRAMMY |
| Name | Grammy |
| Trigger | START tile — khi **đi qua** ô Bắt Đầu (`on_pass`) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → chọn **1 ô CITY trống ngẫu nhiên** trên map:
1. Ô trở thành của player (`tile.owner_id = player.player_id`)
2. Xây thẳng lên **L4 (nhà cấp 3)** miễn phí (`tile.building_level = 4`)

```
unowned = [t for t in board.tiles if t.space_id == SpaceId.CITY and t.owner_id is None]
if unowned:
    chosen = random.choice(unowned)
    chosen.owner_id = player.player_id
    chosen.building_level = 4  # nhà cấp 3 = L4
    player.add_property(chosen.position)
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 16%         | +1%             | 20%         |
| S    | 1★       | 22%         | +2%             | 30%         |
| R    | —        | dùng config S | —             | 30% (S5★)  |

## Notes

- Trigger khi **đi qua** Start (on_pass), không phải khi dừng tại Start
- nhà cấp 3 = L4 trong code (convention từ SK_O_KY_DIEU)
- Nếu không còn ô CITY trống → fail silently
- Miễn phí hoàn toàn — không trừ tiền player
- Stub AI: không cần logic đặc biệt
