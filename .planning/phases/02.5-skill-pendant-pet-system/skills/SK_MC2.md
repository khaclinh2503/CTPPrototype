# Skill: MC2

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_MC2 |
| Name | MC2 |
| Trigger | ACQUIRE phase — khi **mua đất mới** (ô trống) HOẶC **mua lại đất đối thủ** (acquisition) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → lấy **1 ô CITY trống ngẫu nhiên** trên map, đặt level = level của ô vừa mua/xây. **Miễn phí.**

```
unowned = [t for t in board.tiles if t.space_id == SpaceId.CITY and t.owner_id is None]
if unowned:
    chosen = random.choice(unowned)
    chosen.owner_id = player.player_id
    chosen.building_level = newly_acquired_tile.building_level
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 21%         | +1%             | 25%         |
| S    | 1★       | 26%         | +2%             | 34%         |
| R    | —        | dùng config S | —             | 34% (S5★)  |

## Notes

- Logic giống Effect 1 của SK_TRUM_DU_LICH — có thể dùng chung implementation
- Nếu không còn ô CITY trống → fail silently
- Ô ngẫu nhiên: `random.choice(unowned_city_tiles)`
- Stub AI: không cần logic đặc biệt
