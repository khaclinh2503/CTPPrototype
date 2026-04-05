# Pet: Phụ Thu

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PET_PHU_THU |
| Name | Phụ Thu |
| Trigger | `ON_OPPONENT_ACQUIRE_YOURS` — khi đối thủ mua lại ô đất của player |
| Max Stamina | **3** |

## Effect

Khi đối thủ acquisition ô đất của player, nếu pet active → player **cướp X% tiền mua lại** từ đối thủ.

```
# ON_OPPONENT_ACQUIRE_YOURS (khi đối thủ đang trả tiền mua nhà của player)
if player.pet_stamina > 0:
    if random(0, 100) < tier_rates[player.pet_tier - 1]:
        steal_amount = acquisition_cost * steal_ratio[tier]
        opponent.cash -= steal_amount
        player.cash += steal_amount
        player.pet_stamina -= 1
```

Stub AI: luôn active nếu còn thể lực.

## Tier Rates & Steal Ratio

| Tier | Activation Rate | Steal Ratio (% acquisition cost) |
|------|----------------|-----------------------------------|
| 1    | 25%            | 50%                               |
| 2    | 35%            | 75%                               |
| 3    | 50%            | 100%                              |
| 4    | 70%            | 150%                              |
| 5    | 100%           | 200%                              |

**Lưu ý Tier 4-5:** steal_ratio > 100% có nghĩa là đối thủ trả tiền mua nhà VÀ còn bị cướp thêm — tổng tiền đối thủ mất = acquisition_cost + (acquisition_cost × extra_ratio). Player nhận được nhiều hơn giá trị nhà.

## Stamina

- **Max stamina: 3** — pet có thể kích hoạt tối đa **3 lần** trong ván
- Mỗi lần kích hoạt: `pet_stamina -= 1`
- Khi `pet_stamina = 0`: không còn check nữa

## Notes

- Trigger: `ON_OPPONENT_ACQUIRE_YOURS` — chỉ khi đối thủ BUY BACK ô của player (acquisition), không phải khi player mua đất mới
- Tier 3 (100%): player nhận đúng bằng giá trị acquisition cost → bù đắp hoàn toàn việc mất nhà
- Tier 4-5: cộng thêm "tiền phạt" lên đối thủ dám cướp nhà
- Không ảnh hưởng đến việc acquisition có thành công hay không — chỉ điều chỉnh lượng tiền chuyển giao
