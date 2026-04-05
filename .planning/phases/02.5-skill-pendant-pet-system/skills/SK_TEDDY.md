# Skill: Teddy

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_TEDDY |
| Name | Teddy |
| Trigger | UPGRADE phase — khi player xây nhà (nâng cấp property) |

## Effect Chain

**Effect 1** (check trước):
- Activation: `random(0,100) < rate` → nâng cấp thẳng lên **L5 (Biểu tượng / max level)** thay vì +1 level bình thường

**Effect 2** (chỉ check nếu Effect 1 active):
- Activation: `random(0,100) < 60` (fixed 60%)
- Effect: Player di chuyển đến ô du lịch (TRAVEL tile)

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 14%         | +2%             | 22%         |
| S    | 1★       | 23%         | +3%             | 35%         |
| R    | —        | dùng config S | —             | 35% (S5★)  |

## Activation Formula

```
# Effect 1
rate_at_star = base_rate + (current_star - min_star) * chance
if random(0, 100) < rate_at_star:
    upgrade_to_L5()
    # Effect 2
    if random(0, 100) < 60:
        move_to_travel_tile()
```

## Notes

- Effect 2 rate cố định 60%, không phụ thuộc rank/star
- Skill không có ở rank C, D, B
- Stub AI: nếu di chuyển đến travel tile → xử lý bình thường như TravelStrategy
