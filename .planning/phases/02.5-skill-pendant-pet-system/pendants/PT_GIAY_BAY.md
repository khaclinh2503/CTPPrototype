# Pendant: Giày bay

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_GIAY_BAY |
| Name | Giày bay |
| Trigger | `ON_LAND_OPPONENT_WITH_TOLL` — khi player dừng tại ô đất đối thủ và phải trả toll |

## Effect

Nếu pendant active → player **miễn phí toll** VÀ được **teleport tới 1 ô Du Lịch (Travel tile) bất kỳ**.

```
# ON_LAND_OPPONENT_WITH_TOLL (chỉ check khi có toll phải trả)
if random(0, 100) < rate_at_rank:
    toll = 0  # miễn phí toll lần này
    chosen_travel_tile = ai_choose_travel_tile(player, board)
    player.move_to(chosen_travel_tile)
    # tile effect tại Travel tile đến vẫn trigger bình thường (SO_10, SiêuTaxi, v.v.)
```

Stub AI: chọn Travel tile có vị trí chiến lược nhất (gần ô đất trống hoặc xa ô đắt tiền của đối thủ).

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

- Trigger: đáp ô đất **đối thủ** (không phải ô Travel) + có toll phải trả
- Cả 2 effect (miễn toll + teleport Travel) xảy ra đồng thời khi active
- Sau khi teleport đến Travel tile: SO_10 / PT_SIEU_TAXI effect 1 có thể trigger bình thường tại đó
- **Priority với PT_SIEU_TAXI effect 2**: GiàyBay check trước — nếu active thì SiêuTaxi effect 2 không check nữa (player đã teleport đi)
- Nếu GiàyBay không active → mới check PT_SIEU_TAXI effect 2
- Nếu không có Travel tile trên bàn → chỉ miễn toll, không di chuyển
