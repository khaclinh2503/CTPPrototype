# Pendant: Siêu Sao Chép

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_SIEU_SAO_CHEP |
| Name | Siêu Sao Chép |
| Trigger 1 | `ON_OPPONENT_UPGRADE_SYMBOL` — khi bất kỳ đối thủ nào xây Biểu Tượng (nâng lên L5) |
| Trigger 2 | `ON_GAME_START` — khi bắt đầu ván chơi |

## Effect — 2 rate độc lập

### Rate 1: Tạo biểu tượng ngẫu nhiên khi đối thủ xây

```
# ON_OPPONENT_UPGRADE_SYMBOL
if random(0, 100) < rate1_at_rank:
    candidate_tiles = [t for t in player.owned_properties if t.building_level < 5]
    if candidate_tiles:
        chosen = random.choice(candidate_tiles)
        chosen.building_level = 5   # tạo biểu tượng ngẫu nhiên
```

### Rate 2: x2 tiền đầu ván

```
# ON_GAME_START (1 lần duy nhất khi khởi tạo ván)
if random(0, 100) < rate2_at_rank:
    player.cash *= 2
```

Stub AI: Rate1 — chọn ô đất có giá trị cao nhất để upgrade; Rate2 — luôn active.

## Rank Config

| Rank | Rate 1 (copy biểu tượng) | Rate 2 (x2 tiền đầu ván) |
|------|--------------------------|--------------------------|
| B    | 5%                       | 10%                      |
| A    | 7%                       | 15%                      |
| S    | 10%                      | 20%                      |
| R    | 15%                      | 75%                      |
| SR   | 30%                      | 90%                      |

## Activation Formula

```
r1_active = random(0, 100) < rate1_at_rank
r2_active = random(0, 100) < rate2_at_rank
```

## Notes

- Rate1: chỉ trigger khi đối thủ xây biểu tượng (mỗi lần đối thủ nào đó đạt L5)
- Rate1: nếu player không có ô đất nào < L5 → effect skip
- Rate2: chỉ xảy ra 1 lần duy nhất khi bắt đầu ván (`ON_GAME_START`)
- Rate2 SR: 90% — gần như chắc chắn x2 tiền đầu ván → pendant cực kỳ mạnh ở SR
- Rate1 tạo biểu tượng ngẫu nhiên: chọn random từ owned_properties của player, không phải copy ô của đối thủ
- **Chain khi Rate1 active**: L5 được tạo → trigger ngay các skill của player: SK_MONG_NGUA (chiếm Resort), SK_TEDDY / SK_GAY_NHU_Y (teleport Travel). Bất kỳ skill nào liên quan đến "landmark được tạo" đều fire
