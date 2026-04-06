# Pendant: Túi ba gang

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_TUI_BA_GANG |
| Name | Túi ba gang |
| Trigger 1 | `ON_OPPONENT_LAND_YOURS` — khi đối thủ dừng tại ô của player (trả toll) |
| Trigger 2 | `ON_SAME_TILE` — khi bất kỳ player nào đứng cùng ô với player |

## Effect — 2 rate độc lập

### Effect 1: Tăng % phí khi người khác tham quan

**Luôn active (100%)** — không roll xác suất. Tăng toll thêm effect_ratio %.

```
# ON_OPPONENT_LAND_YOURS — luôn xảy ra
toll_multiplier += effect1_ratio  # B:10%, A:20%, S:30%, R:50%, SR:60%
```

### Effect 2: Lấy % tiền của người đứng cùng ô

**Luôn active (100%)** — không roll xác suất. Lấy effect_ratio % tiền đối thủ.

```
# ON_SAME_TILE (player và opponent đang đứng cùng 1 ô) — luôn xảy ra
amount = opponent.cash * (effect2_ratio / 100)  # B:5%, A:7%, S:10%, R:15%, SR:36%
opponent.cash -= amount
player.cash += amount
```

Stub AI: Effect1 — luôn boost toll; Effect2 — luôn ăn tiền đối thủ.

## Rank Config

| Rank | Effect 1 (% tăng phí) | Effect 2 (% ăn tiền) |
|------|----------------------|---------------------|
| B    | 10%                  | 5%                  |
| A    | 20%                  | 7%                  |
| S    | 30%                  | 10%                 |
| R    | 50%                  | 15%                 |
| SR   | 60%                  | 36%                 |

## Activation

Cả hai effect **luôn active (100%)** khi trigger xảy ra — không roll xác suất. Số % trong table là magnitude effect, không phải activation rate.

## Notes

- Effect1 và Effect2 là hai trigger point khác nhau, fire độc lập
- **Stack với SK_SUNG_VANG**: cả hai đều fire độc lập khi player đáp ô đối thủ → steal 2 lần riêng biệt
- `ON_SAME_TILE`: trigger khi bất kỳ player (không chỉ opponent) kết thúc lượt cùng ô với player
- Kết hợp với PT_KET_VANG: cả hai đều có Effect1 tăng toll → stack lên nhau
- Tương tác với `_toll_modifiers.py` (xem codebase context)
