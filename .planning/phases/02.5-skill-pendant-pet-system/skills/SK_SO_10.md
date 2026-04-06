# Skill: Số 10

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_SO_10 |
| Name | Số 10 |
| Trigger | 2 effect riêng biệt (xem bên dưới) |

---

## Effect 1 — Du lịch ngay

**Trigger:** RESOLVE_TILE phase — khi dừng tại **Travel tile (spaceId=9)**.

**Activation:** `random(0, 100) < rate_at_star`

**Effect:** Sau khi Travel tile resolve xong, player được **ngay lập tức chọn đến ô bất kỳ** trên map (không cần chờ lượt sau).
- Tile effect tại ô đến **không trigger** (chỉ repositioned)

```
if random(0, 100) < rate_at_star:
    chosen = player_choose_any_tile()  # AI stub: chọn ô đất trống hoặc đắt nhất của mình
    player.move_to(chosen.position)
```

### Rate Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 44%         | +2%             | 52%         |
| S    | 1★       | 55%         | +4%             | 71%         |
| R    | —        | dùng config S | —             | 71% (S5★)  |

---

## Effect 2 — Tăng thưởng qua Start

**Luôn active (100%)** — không cần rate check.

Tăng tiền thưởng qua Start thêm **50%** (fixed, không phụ thuộc rank/star):

```
bonus = normal_passing_bonus * 1.5  # 150,000 × 1.5 = 225,000
```

---

## Notes

- Effect 1: player chọn bất kỳ ô nào trên map (kể cả ô đang đứng)
- Effect 2 giống SK_MU_PHEP nhưng value cố định 50% (không scale theo rank). Tích hợp vào `ON_PASS_START` trigger handler — không dùng stat_delta (D-30)
- Stub AI Effect 1: ưu tiên ô CITY trống gần nhất hoặc ô đất đắt nhất của mình
