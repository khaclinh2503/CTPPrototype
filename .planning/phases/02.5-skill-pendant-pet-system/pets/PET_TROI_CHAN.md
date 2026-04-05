# Pet: Trói chân

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PET_TROI_CHAN |
| Name | Trói chân |
| Trigger | `ON_OPPONENT_PASS_YOURS` — khi đối thủ đi qua ô của player (on_pass, không dừng) |
| Max Stamina | **5** |

## Effect

Khi đối thủ đi qua ô của player, nếu pet active → đối thủ bị **trói chân 1 lượt**: phải tung số chẵn mới được di chuyển.

```
# ON_OPPONENT_PASS_YOURS
if player.pet_stamina > 0:
    if random(0, 100) < tier_rates[player.pet_tier - 1]:
        opponent.bound_turns = 1   # trói 1 lượt
        player.pet_stamina -= 1

# Đầu lượt của đối thủ bị trói (FSM.ROLL):
if active_player.bound_turns > 0:
    dice = roll_dice()
    if dice % 2 != 0:   # tung số lẻ → skip move
        active_player.bound_turns -= 1
        skip_move = True
    else:   # tung số chẵn → di chuyển bình thường
        active_player.bound_turns -= 1
        # di chuyển theo dice bình thường
```

Stub AI (bị trói): chọn số chẵn nếu có DKXX; không có DKXX thì random bình thường.

## Tier Rates

| Tier | Rate |
|------|------|
| 1    | 25%  |
| 2    | 35%  |
| 3    | 45%  |
| 4    | 55%  |
| 5    | 70%  |

## Stamina

- **Max stamina: 5** — pet có thể kích hoạt tối đa **5 lần** trong ván
- Mỗi lần kích hoạt: `pet_stamina -= 1`
- Khi `pet_stamina = 0`: không còn check nữa

## Notes

- `bound_turns` đã có trong Player.D-15 — trường này được tạo chính xác cho pet này
- Trigger: `ON_OPPONENT_PASS_YOURS` — đối thủ ĐI QUA (không phải dừng tại) ô của player
- Nếu đối thủ tung số chẵn: bound_turns -= 1, di chuyển bình thường (không bị phạt)
- Nếu đối thủ tung số lẻ: bound_turns -= 1, **skip move** (không di chuyển lượt đó)
- Nhiều pet có thể stack: nếu bị trói nhiều lần, `bound_turns` tăng tương ứng
- Tier max (5): 70% — không phải 100%, vẫn có chance không active
- Kết hợp cực tốt khi player có nhiều ô đất → đối thủ thường đi qua
