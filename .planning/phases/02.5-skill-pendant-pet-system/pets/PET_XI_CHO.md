# Pet: Xí Chỗ

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PET_XI_CHO |
| Name | Xí Chỗ |
| Trigger | `ON_OPPONENT_BUILD` — khi đối thủ xây nhà, VÀ đối thủ đang còn thiếu đúng 1 ô để hoàn thành điều kiện thắng |
| Max Stamina | **3** |

## Effect

Khi đối thủ xây nhà VÀ đang còn thiếu đúng 1 ô để thắng, nếu pet active:
1. Player **xây đất nền** (L1) vào 1 ô CITY trống bất kỳ
2. Ô đó **không thể bị mua lại** (acquisition) trong 1 lượt tiếp theo — đối thủ đáp vào trả toll nhưng không thể mua

```
# ON_OPPONENT_BUILD (check sau mỗi ON_BUILD/ON_UPGRADE của đối thủ)
# Chỉ trigger nếu đối thủ còn thiếu đúng 1 ô để thắng
if player.pet_stamina > 0 and tiles_needed_to_win(opponent) == 1:
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

- Trigger check sau mỗi `ON_BUILD/ON_UPGRADE` của đối thủ
- Điều kiện: `tiles_needed_to_win(opponent) == 1` — đối thủ còn thiếu **đúng 1 ô** để thắng
- Logic check: `tiles_needed_to_win(opponent)` cần được implement theo điều kiện thắng của game
- Nếu không có ô CITY trống: Effect 1 skip, chỉ có Effect 2 (anti-acquisition)
- **Không conflict với SK_GRAMMY**: Grammy lấy ô đất **trống**, ô XíChỗ vừa đặt đã có chủ (L1 của B) → Grammy không nhắm vào ô đó
- `acquisition_blocked_turns = 1`: chỉ block trong 1 lượt, sau đó reset
