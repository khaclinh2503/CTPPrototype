# Skill: Tốc Chiến

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_TOC_CHIEN |
| Name | Tốc Chiến |
| Trigger | RESOLVE_TILE phase — sau khi di chuyển bằng ô **Travel (Du Lịch)** |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → player được **đổ thêm 1 lượt xúc xắc** ngay sau khi Travel tile resolve xong.

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 40%         | +2%             | 48%         |
| S    | 1★       | 50%         | +4%             | 66%         |
| R    | —        | dùng config S | —             | 66% (S5★)  |

## Notes

- Trigger sau khi **toàn bộ di chuyển Travel hoàn tất** (player đã đến đích cuối cùng)
- Di chuyển bằng Travel không thể đến Travel tile → không có chain vô hạn
- Lượt thêm là đổ xúc xắc bình thường (có thể dùng Moonwalk, XXCT, v.v.)
- Stub AI: không cần logic đặc biệt
