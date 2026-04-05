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

- Trigger sau khi player **đã đến đích** của Travel tile (không phải khi đi qua)
- Lượt thêm là đổ xúc xắc bình thường (không bị hạn chế ô đến)
- Stub AI: không cần logic đặc biệt
