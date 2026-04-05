# Pendant: Siêu Taxi

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_SIEU_TAXI |
| Name | Siêu Taxi |
| Trigger 1 | `ON_LAND_TRAVEL` — khi player dừng tại ô Du Lịch (Travel tile) |
| Trigger 2 | `ON_LAND_OPPONENT` — khi player dừng tại ô đất của đối thủ |

## Effect — 2 rate độc lập

### Rate 1: Di chuyển ngay khi tới ô du lịch

```
# ON_LAND_TRAVEL
if random(0, 100) < rate1_at_rank:
    chosen_tile = ai_choose_travel_destination(player, board)
    player.move_to(chosen_tile)
    # tile effect tại điểm đến vẫn trigger bình thường
```

### Rate 2: Miễn phí tham quan khi vào đất đối thủ

```
# ON_LAND_OPPONENT (trước khi tính toll)
if random(0, 100) < rate2_at_rank:
    toll = 0  # miễn phí lần này
```

Stub AI: Rate1 — chọn Travel tile gần đất đối thủ giá cao; Rate2 — luôn active (miễn phí).

## Rank Config

| Rank | Rate 1 (di chuyển từ Travel) | Rate 2 (miễn phí tham quan) |
|------|-----------------------------|-----------------------------|
| B    | 30%                         | 3%                          |
| A    | 40%                         | 5%                          |
| S    | 50%                         | 8%                          |
| R    | 66%                         | 20%                         |
| SR   | 76%                         | 35%                         |

## Activation Formula

```
r1_active = random(0, 100) < rate1_at_rank
r2_active = random(0, 100) < rate2_at_rank
```

## Notes

- Rate1 cao (30–76%) — pendant này rất thường xuyên di chuyển khi tới Travel tile
- Rate2 thấp (3–35%) — tiết kiệm tiền ngẫu nhiên khi trả toll
- Khác PT_GIAY_BAY: PT_SIEU_TAXI di chuyển ngay (không miễn phí tham quan Travel), còn PT_GIAY_BAY miễn phí + teleport
- Hai trigger point khác nhau: Rate1 tại Travel tile, Rate2 tại đất đối thủ
