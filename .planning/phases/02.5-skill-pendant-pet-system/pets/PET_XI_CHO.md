# Pet: Xí Chỗ

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PET_XI_CHO |
| Name | Xí Chỗ |
| Trigger | `ON_OPPONENT_COMPLETE_2_COLOR_PAIRS` — khi bất kỳ đối thủ nào hoàn thành 2 cặp màu trở lên |
| Max Stamina | **3** |

## Effect

Khi đối thủ vừa hoàn thành 2 cặp màu, nếu pet active:
1. Player **xây đất nền** (L1) vào 1 ô CITY trống bất kỳ
2. Ô đó **không bị acquisition** trong 1 lượt tiếp theo

```
# ON_OPPONENT_COMPLETE_2_COLOR_PAIRS (check sau mỗi ON_ACQUIRE/ON_UPGRADE của đối thủ)
if player.pet_stamina > 0:
    if random(0, 100) < tier_rates[player.pet_tier - 1]:
        # Effect 1: xây đất nền vào ô trống bất kỳ
        empty_tiles = [t for t in board.tiles if t.tile_type == "CITY" and t.owner_id is None]
        if empty_tiles:
            chosen = ai_choose_city_tile(empty_tiles, player, board)
            chosen.owner_id = player.id
            chosen.building_level = 1   # đất nền L1
        # Effect 2: chống acquisition 1 lượt
        chosen.acquisition_blocked_turns = 1
        player.pet_stamina -= 1
```

Stub AI: chọn ô trống có giá trị vị trí cao nhất (nhiều đối thủ đi qua).

## Tier Rates

| Tier | Rate |
|------|------|
| 1    | 25%  |
| 2    | 35%  |
| 3    | 50%  |
| 4    | 70%  |
| 5    | 100% |

## Stamina

- **Max stamina: 3** — pet có thể kích hoạt tối đa **3 lần** trong ván
- Mỗi lần kích hoạt: `pet_stamina -= 1`
- Khi `pet_stamina = 0`: pet không check nữa

## Notes

- Trigger check sau mỗi `ON_ACQUIRE` hoặc `ON_UPGRADE` của đối thủ — game cần tính số cặp màu đối thủ sở hữu
- "Hoàn thành 2 cặp màu" = đối thủ có ít nhất 2 bộ đủ màu (mỗi màu có đủ tiles)
- Logic check: `count_complete_color_pairs(opponent)` trong `_count_complete_color_pairs()`
- Nếu không có ô CITY trống: Effect 1 skip, chỉ có Effect 2 (anti-acquisition)
- `acquisition_blocked_turns = 1`: chỉ block trong 1 lượt, sau đó reset
