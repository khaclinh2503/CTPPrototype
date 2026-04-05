# Pendant: Xích Ngọc

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_XICH_NGOC |
| Name | Xích Ngọc |
| Trigger 1 | `ON_PRISON_ESCAPE_CHECK` — khi player đang ở tù và game check thoát tù |
| Trigger 2 | `ON_DKXX_CHECK` — khi game kiểm tra DKXX activation |

## Effect — 2 rate độc lập

### Rate 1: Tăng xác suất ra tù

```
# ON_PRISON_ESCAPE_CHECK
if random(0, 100) < rate1_at_rank:
    player.exit_prison()   # thoát tù ngay lập tức
```

### Rate 2: Boost điều khiển xúc xắc (DKXX)

```
# ON_DKXX_CHECK
if random(0, 100) < rate2_at_rank:
    player.accuracy_rate += DKXX_BOOST  # tăng % điều khiển xúc xắc lần này
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

- SR rank: Rate1 = 100% → **luôn thoát tù** khi pendant này trang bị
- Hai trigger point độc lập — mỗi trigger check rate tương ứng
- Kết hợp với PT_DKXX2 để tối đa DKXX boost
- Nếu player không trong tù → Rate1 trigger không xảy ra
