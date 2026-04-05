# Pendant: Túi ba gang

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_TUI_BA_GANG |
| Name | Túi ba gang |
| Trigger 1 | `ON_OPPONENT_LAND_YOURS` — khi đối thủ dừng tại ô của player (trả toll) |
| Trigger 2 | `ON_SAME_TILE` — khi bất kỳ player nào đứng cùng ô với player |

## Effect — 2 rate độc lập

### Rate 1: Tăng % phí khi người khác tham quan

```
# ON_OPPONENT_LAND_YOURS (trước hoặc sau khi tính toll)
if random(0, 100) < rate1_at_rank:
    toll_multiplier += TOLL_BONUS  # tăng % phí tham quan lần này
```

### Rate 2: Lấy % tiền của người đứng cùng ô

```
# ON_SAME_TILE (player và opponent đang đứng cùng 1 ô)
if random(0, 100) < rate2_at_rank:
    amount = opponent.cash * STEAL_RATIO
    opponent.cash -= amount
    player.cash += amount
```

Stub AI: Rate1 — luôn boost toll; Rate2 — luôn ăn tiền đối thủ.

## Rank Config

| Rank | Rate 1 (tăng phí) | Rate 2 (ăn tiền) |
|------|------------------|------------------|
| B    | 10%              | 5%               |
| A    | 20%              | 7%               |
| S    | 30%              | 10%              |
| R    | 50%              | 15%              |
| SR   | 60%              | 36%              |

## Activation Formula

```
r1_active = random(0, 100) < rate1_at_rank
r2_active = random(0, 100) < rate2_at_rank
```

## Notes

- Rate1 và Rate2 là hai trigger point khác nhau, check độc lập
- **Stack với SK_SUNG_VANG**: cả hai đều fire độc lập khi player đáp ô đối thủ → steal 2 lần riêng biệt
- `ON_SAME_TILE`: trigger khi bất kỳ player (không chỉ opponent) kết thúc lượt cùng ô với player
- STEAL_RATIO của Rate2: cần define trong config (ví dụ: 5–10% tuỳ thiết kế)
- Kết hợp với PT_KET_VANG: cả hai đều có Rate1 tăng toll → stack lên nhau
- Tương tác với `_toll_modifiers.py` (xem codebase context)
