# Pendant: Dkxx2

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_DKXX2 |
| Name | Dkxx2 |
| Trigger | `ON_DKXX_CHECK` — khi game kiểm tra xem player có được dùng DKXX (điều khiển xúc xắc) không |

## Effect

Nếu pendant active → boost xác suất kích hoạt DKXX của player trong lượt đó.

```
# ON_DKXX_CHECK
if random(0, 100) < rate_at_rank:
    player.accuracy_rate += DKXX_BOOST  # boost thêm % điều khiển xúc xắc lần này
```

Stub AI: luôn active, chọn số có lợi nhất.

## Rank Config

| Rank | Rate |
|------|------|
| B    | 2%   |
| A    | 3%   |
| S    | 4%   |
| R    | 12%  |
| SR   | 18%  |

## Activation Formula

```
active = random(0, 100) < rate_at_rank
```

(Không có rank C/D — pendant tối thiểu rank B)

## Notes

- Pendant ranks: B / A / S / R / SR — không có C/D
- Kết hợp với PT_XICH_NGOC R2 để tối đa hoá DKXX rate
- Nếu player không có DKXX trong ván → trigger không xảy ra
