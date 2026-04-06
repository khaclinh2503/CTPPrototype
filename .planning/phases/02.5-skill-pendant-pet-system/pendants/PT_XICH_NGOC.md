# Pendant: Xích Ngọc

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_XICH_NGOC |
| Name | Xích Ngọc |
| Trigger 1 | `ON_PRISON_ROLL` — khi player đang ở tù và tung xúc xắc để thoát |
| Trigger 2 | `ON_DKXX_CHECK` — khi game kiểm tra DKXX activation |

## Effect — 2 rate độc lập

### Rate 1: Boost tỉ lệ tung đôi để thoát tù

Chỉ trigger khi player **chọn đổ xúc xắc** để thoát tù. Không check khi chọn các option khác (trả tiền, dùng thẻ, v.v.).

Flow: Chọn đổ xúc xắc → XíchNgọc boost doubles rate → đổ xúc xắc → tung đôi thì thoát tù.

```
# ON_PRISON_ROLL — chỉ khi player chọn option "đổ xúc xắc" để thoát tù
doubles_rate += rate1_at_rank  # cộng dồn vào tỉ lệ ra đôi cơ bản
```

### Rate 2: Boost điều khiển xúc xắc (DKXX)

```
# ON_DKXX_CHECK
if random(0, 100) < rate2_at_rank:
    player.dkxx_bonus_pool += rate2_at_rank  # cộng dồn vào pool DKXX (B:2, A:4, S:6, R:10, SR:14)

# Flow DKXX đầy đủ:
# 1. Check pool (skill + pendant + pet tổng cộng) → active: player CHỌN được số xúc xắc
# 2. Pool không active → fallback check chỉ số DKXX nhân vật → active: DKXX bị động (không chọn được)
```

Stub AI: Rate1 — luôn thoát tù nếu active; Rate2 — chọn số có lợi nhất.

## Rank Config

| Rank | Rate 1 (thoát tù) | Rate 2 (DKXX boost) |
|------|-------------------|---------------------|
| B    | 20%               | 2%                  |
| A    | 40%               | 4%                  |
| S    | 60%               | 6%                  |
| R    | 80%               | 10%                 |
| SR   | 100%              | 14%                 |

## Activation Formula

```
# Hai rate check độc lập nhau
r1_active = random(0, 100) < rate1_at_rank
r2_active = random(0, 100) < rate2_at_rank
```

## Notes

- Rate1 là **passive boost** cho tỉ lệ ra đôi khi tung xúc xắc trong tù — không phải auto-escape
- Không conflict với SK_JOKER: Joker auto-thoát đầu turn; XíchNgọc boost xúc xắc khi Joker không active
- Hai trigger point độc lập — mỗi trigger check rate tương ứng
- Kết hợp với PT_DKXX2 để tối đa DKXX boost
- Nếu player không trong tù → Rate1 trigger không xảy ra
