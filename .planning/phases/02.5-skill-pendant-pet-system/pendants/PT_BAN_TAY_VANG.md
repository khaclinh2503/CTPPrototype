# Pendant: Bàn tay vàng

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_BAN_TAY_VANG |
| Name | Bàn tay vàng |
| Trigger | `ON_LAND_OWN` (biểu tượng) — khi player dừng tại **Biểu Tượng của mình** (building_level = 5) |

## Effect

Nếu pendant active → hút tất cả đối thủ đang đứng trên **cùng hàng (cạnh bàn cờ)** với Biểu Tượng đến ô đó.

```
# ON_LAND_OWN khi building_level == 5
if random(0, 100) < rate_at_rank:
    same_side = get_tiles_on_same_side(board, player.position)  # D-27: cùng 1 trong 4 cạnh
    for opponent in opponents_on_tiles(same_side):
        opponent.move_to(player.position)
        # tile effect (trả toll Biểu Tượng) trigger bình thường
```

Stub AI: luôn active (hút tối đa đối thủ).

## Rank Config

| Rank | Rate |
|------|------|
| B    | 2%   |
| A    | 5%   |
| S    | 20%  |
| R    | 50%  |
| SR   | 85%  |

## Activation Formula

```
active = random(0, 100) < rate_at_rank
```

## Notes

- Chỉ trigger khi `building_level == 5` (D-24: Biểu Tượng = L5)
- "Cùng hàng/cạnh" = cùng 1 trong 4 cạnh của bàn cờ hình thoi 32 ô (D-27)
- Khác PT_TU_TRUONG R2: PT_TU_TRUONG hút trong radius 4; PT_BAN_TAY_VANG hút **toàn bộ cạnh**
- Đối thủ bị hút phải trả toll Biểu Tượng — combo cực mạnh với property giá cao
- Rate nhảy mạnh ở S → R → SR: 20% → 50% → 85%
- **Stack với SK_LAU_DAI_TINH_AI**: cả hai fire độc lập — LDTA hút 1 đối thủ random, BànTayVàng hút toàn cạnh → đối thủ bị pull 2 lần, trả toll 2 lần
