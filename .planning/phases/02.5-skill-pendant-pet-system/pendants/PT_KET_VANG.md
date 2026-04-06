# Pendant: Két vàng

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_KET_VANG |
| Name | Két vàng |
| Trigger 1 | `ON_OPPONENT_LAND_YOURS` — khi đối thủ dừng tại ô của player (trả toll) |
| Trigger 2 | `ON_LAND_OWN` — khi player dừng tại nhà của chính mình |

## Effect — 2 rate độc lập

### Effect 1: Tăng % phí khi người khác tham quan

**Luôn active (100%)** — không roll xác suất. Tăng toll thêm effect_ratio %.

```
# ON_OPPONENT_LAND_YOURS — luôn xảy ra
toll_multiplier += effect1_ratio  # B:10%, A:20%, S:30%, R:50%, SR:60%
```

### Effect 2: Nhận lại % phí xây dựng khi player dừng nhà mình

**Luôn active (100%)** — không roll xác suất. Refund effect_ratio % tiền đã đầu tư.

```
# ON_LAND_OWN — luôn xảy ra
invested = calc_invested_build_cost(board, player.position)
refund = invested * (effect2_ratio / 100)  # B:10%, A:15%, S:25%, R:50%, SR:60%
player.cash += refund
```

Stub AI: cả hai effect — luôn active.

## Rank Config

| Rank | Effect 1 (% tăng phí) | Effect 2 (% hoàn tiền xây) |
|------|----------------------|---------------------------|
| B    | 10%                  | 10%                       |
| A    | 20%                  | 15%                       |
| S    | 30%                  | 25%                       |
| R    | 50%                  | 50%                       |
| SR   | 60%                  | 60%                       |

## Activation

Cả hai effect **luôn active (100%)** khi trigger xảy ra — không roll xác suất. Số % trong table là magnitude effect, không phải activation rate.

## Notes

- Effect1 giống PT_TUI_BA_GANG E1 — cả hai có thể stack toll modifier
- Effect2 giống PT_TU_TRUONG R1 nhưng % cao hơn ở cấp cao (SR: 60% vs 50%)
- Sử dụng `calc_invested_build_cost()` đã có sẵn trong codebase
- Tương tác với `_toll_modifiers.py` cho Effect1
