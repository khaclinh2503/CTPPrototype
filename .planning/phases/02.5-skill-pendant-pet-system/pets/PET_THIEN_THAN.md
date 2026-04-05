# Pet: Thiên Thần

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PET_THIEN_THAN |
| Name | Thiên Thần |
| Trigger | `ON_CANT_AFFORD_TOLL` — khi player không đủ tiền trả toll |
| Max Stamina | **1** |

## Effect

Khi player không đủ tiền trả toll, nếu pet active → **dùng thẻ thiên thần miễn phí** (toll được bỏ qua hoàn toàn).

```
# ON_CANT_AFFORD_TOLL
if player.pet_stamina > 0:
    if random(0, 100) < tier_rates[player.pet_tier - 1]:
        toll = 0          # miễn phí lần này
        player.pet_stamina -= 1   # tiêu 1 thể lực (max_stamina=1 → pet hết dùng được)
```

Stub AI: luôn active nếu còn thể lực.

## Tier Rates

| Tier | Rate |
|------|------|
| 1    | 25%  |
| 2    | 35%  |
| 3    | 50%  |
| 4    | 70%  |
| 5    | 100% |

## Stamina

- **Max stamina: 1** — pet chỉ có thể kích hoạt **1 lần** trong cả ván
- Sau khi kích hoạt 1 lần: `pet_stamina = 0` → không còn check nữa

## Notes

- Tier 5: 100% — **luôn** kích hoạt khi không đủ tiền (nhưng vẫn chỉ 1 lần do max_stamina=1)
- Mạnh nhất khi player sắp phá sản với 1 lần cứu thua duy nhất
- `ON_CANT_AFFORD_TOLL`: trigger trước khi game xử lý thiếu tiền (bán nhà, vay nợ, v.v.)
- Khi max_stamina=1 và đã dùng: `pet_stamina=0` → pet không bao giờ check lại trong ván
