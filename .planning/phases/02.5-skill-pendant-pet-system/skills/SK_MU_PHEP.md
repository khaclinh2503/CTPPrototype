# Skill: Mũ Phép

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_MU_PHEP |
| Name | Mũ Phép |
| Trigger | START tile — khi **đi qua** ô bắt đầu (`on_pass`) |

## Effect

**Luôn active (100%)** — không cần rate check.

Tăng tiền thưởng qua Start thêm **@value@%**:

```
bonus = normal_passing_bonus * (1 + value / 100)
# Ví dụ B1★: 150,000 × 1.41 = 211,500
```

## Rank Config

`value` = % tăng thêm (không phải activation rate — skill luôn active).

| Rank | Min Star | Value (base) | Chance (+/star) | Value tại 5★ |
|------|----------|--------------|-----------------|--------------|
| C    | —        | —            | —               | Không có     |
| D    | —        | —            | —               | Không có     |
| B    | 1★       | 41%          | +2%             | 49%          |
| A    | 1★       | 51%          | +3%             | 63%          |
| S    | 1★       | 66%          | +5%             | 86%          |
| R    | —        | dùng config S  | —             | 86% (S5★)   |

## Notes

- Đây là skill **stat buff thụ động** — không có activation chance, luôn áp dụng
- Xuất hiện từ rank B (khác các skill khác chỉ từ A)
- Tích hợp vào `StartStrategy.on_pass()` thông qua `effective_stat(passing_bonus_delta)`
- Nếu player có nhiều buff passing_bonus_delta → cộng dồn tất cả theo D-22
