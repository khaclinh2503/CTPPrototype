# Pendant: Két vàng

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_KET_VANG |
| Name | Két vàng |
| Trigger 1 | `ON_OPPONENT_LAND_YOURS` — khi đối thủ dừng tại ô của player (trả toll) |
| Trigger 2 | `ON_LAND_OWN` — khi player dừng tại nhà của chính mình |

## Effect — 2 rate độc lập

### Rate 1: Tăng % phí khi người khác tham quan

```
# ON_OPPONENT_LAND_YOURS
if random(0, 100) < rate1_at_rank:
    toll_multiplier += TOLL_BONUS  # tăng % phí tham quan lần này
```

### Rate 2: Nhận lại % phí xây dựng khi player dừng nhà mình

```
# ON_LAND_OWN
if random(0, 100) < rate2_at_rank:
    invested = calc_invested_build_cost(board, player.position)
    refund = invested * REFUND_RATIO
    player.cash += refund
```

Stub AI: cả hai rate — luôn active.

## Rank Config

| Rank | Rate 1 (tăng phí) | Rate 2 (hoàn tiền xây) |
|------|------------------|------------------------|
| B    | 10%              | 10%                    |
| A    | 20%              | 15%                    |
| S    | 30%              | 25%                    |
| R    | 50%              | 50%                    |
| SR   | 60%              | 60%                    |

## Activation Formula

```
r1_active = random(0, 100) < rate1_at_rank
r2_active = random(0, 100) < rate2_at_rank
```

## Notes

- Rate1 giống PT_TUI_BA_GANG R1 — cả hai có thể stack toll modifier
- Rate2 giống PT_TU_TRUONG R1 nhưng rate cao hơn ở cấp cao (SR: 60% vs 50%)
- Sử dụng `calc_invested_build_cost()` đã có sẵn trong codebase
- Refund ratio: lượng % tiền hoàn lại (tách biệt với activation rate)
- Tương tác với `_toll_modifiers.py` cho Rate1
