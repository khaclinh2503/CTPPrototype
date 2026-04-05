# Pendant: Từ Trường

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_TU_TRUONG |
| Name | Từ Trường |
| Trigger 1 | `ON_LAND_OWN` — khi player dừng tại **nhà của mình** (CITY, bất kỳ level) |
| Trigger 2 | `ON_LAND_OWN` (biểu tượng) — khi player dừng tại **Biểu Tượng của mình** (building_level = 5) |

## Effect — 2 rate độc lập

### Rate 1: Nhận lại % phí xây dựng

Trigger khi player dừng tại BẤT KỲ nhà của mình (bao gồm cả biểu tượng):

```
# ON_LAND_OWN
if random(0, 100) < rate1_at_rank:
    invested = calc_invested_build_cost(board, player.position)
    refund = invested * REFUND_RATIO  # tỷ lệ hoàn lại tuỳ rate
    player.cash += refund
```

### Rate 2: Hút đối thủ trong 4 ô lân cận

Trigger chỉ khi player dừng tại **Biểu Tượng** (building_level = 5):

```
# ON_LAND_OWN khi building_level == 5
if random(0, 100) < rate2_at_rank:
    neighbors = get_tiles_within(board, player.position, radius=4)
    for opponent in opponents_on_tiles(neighbors):
        opponent.move_to(player.position)
        # tile effect (trả toll) trigger bình thường
```

Stub AI: Rate1 — luôn nhận refund; Rate2 — luôn active.

## Rank Config

| Rank | Rate 1 (phí xây dựng) | Rate 2 (hút đối thủ) |
|------|----------------------|----------------------|
| B    | 4%                   | 4%                   |
| A    | 10%                  | 5%                   |
| S    | 15%                  | 10%                  |
| R    | 25%                  | 25%                  |
| SR   | 50%                  | 42%                  |

## Activation Formula

```
r1_active = random(0, 100) < rate1_at_rank   # bất kỳ nhà của mình
r2_active = random(0, 100) < rate2_at_rank   # chỉ khi biểu tượng
```

## Notes

- Rate1 trigger trên MỌI `ON_LAND_OWN` (kể cả biểu tượng)
- Rate2 chỉ trigger khi `building_level == 5` (D-24: Biểu Tượng = L5)
- "4 ô lân cận" = 4 ô tính từ vị trí player theo D-27 (cùng cạnh bàn cờ)
- Đối thủ bị hút: phải trả toll tại ô Biểu Tượng của player
- refund ratio từ Rate1 là % hoàn lại tiền (không phải % rate — đây là lượng tiền hoàn)
