# Skill: Xế Độ

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_XE_DO |
| Name | Xế Độ |
| Trigger | ROLL phase — sau khi đổ xúc xắc |

## Effect

Nếu skill active:
- Dice kết quả **chẵn** → player được chọn 1 số chẵn bất kỳ trong `{2, 4, 6, 8, 10, 12}` thay thế kết quả di chuyển
- Dice kết quả **lẻ** → player được chọn 1 số lẻ bất kỳ trong `{1, 3, 5, 7, 9, 11}` thay thế kết quả di chuyển

Stub AI: chọn số lớn nhất trong set (12 nếu chẵn, 11 nếu lẻ).

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 17%         | +1%             | 21%         |
| S    | 1★       | 22%         | +2%             | 30%         |
| R    | —        | dùng config S | —             | 30% (S5★)  |

## Activation Formula

```
rate_at_star = base_rate + (current_star - min_star) * chance
active = random(0, 100) < rate_at_star
```

R rank dùng config của S (rate=22, chance=2).

## Notes

- Skill này không có ở rank C, D, B
- Stub AI luôn chọn số lớn nhất trong tập hợp hợp lệ
