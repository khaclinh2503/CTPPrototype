# Pendant: Giày bay

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_GIAY_BAY |
| Name | Giày bay |
| Trigger | `ON_LAND_TRAVEL` — khi player dừng tại ô Du Lịch (Travel tile) |

## Effect

Nếu pendant active → player **miễn phí tham quan** (không tốn tiền) VÀ được **di chuyển tới 1 ô du lịch bất kỳ** khác.

```
# ON_LAND_TRAVEL
if random(0, 100) < rate_at_rank:
    toll = 0  # miễn phí tham quan lần này
    chosen_travel_tile = ai_choose_travel_destination(player, board)
    player.move_to(chosen_travel_tile)
    # tile effect tại điểm đến vẫn trigger bình thường
```

Stub AI: chọn Travel tile có lợi nhất (gần ô đất đối thủ giá trị cao nhất).

## Rank Config

| Rank | Rate |
|------|------|
| B    | 1%   |
| A    | 3%   |
| S    | 5%   |
| R    | 10%  |
| SR   | 15%  |

## Activation Formula

```
active = random(0, 100) < rate_at_rank
```

## Notes

- Cả 2 effect (miễn phí + di chuyển) xảy ra đồng thời khi active
- Ô đến mới: tile effect vẫn trigger bình thường
- Tương tự PT_SIEU_TAXI nhưng PT_GIAY_BAY tập trung vào free travel + teleport, PT_SIEU_TAXI tập trung vào move immediately
- Nếu không có Travel tile khác trên bàn → chỉ miễn phí, không di chuyển
