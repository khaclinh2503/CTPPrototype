# Skill: Gậy Như Ý

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_GAY_NHU_Y |
| Name | Gậy Như Ý |
| Trigger | 2 trigger riêng biệt (xem bên dưới) |

---

## Effect 1 — Đi theo đối thủ đến Resort

**Trigger (reactive):** Khi đối thủ di chuyển đến **ô Resort (Khu Du Lịch)**.

**Activation:** `random(0, 100) < rate1_at_star`

**Effect:** Player di chuyển đến cùng ô Resort đó.
- Tile effect tại Resort **xảy ra bình thường** với player (trả toll nếu của đối thủ)

### Rate 1 Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 40%         | +4%             | 56%         |
| S    | 1★       | 60%         | +3%             | 72%         |
| R    | —        | dùng config S | —             | 72% (S5★)  |

---

## Effect 2 — Xây Biểu Tượng + Di chuyển đến Resort

**Trigger:** UPGRADE phase — khi xây nhà (bất kỳ level nào).

**Activation:** `random(0, 100) < rate2_at_star`

**Effect chain** (giống SK_TEDDY):
1. Nâng cấp thẳng lên **L5 (Biểu Tượng)**
2. Nếu active → check tiếp: `random(0, 100) < 70` → di chuyển đến ô Resort

### Rate 2 Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 14%         | +2%             | 22%         |
| S    | 1★       | 23%         | +3%             | 35%         |
| R    | —        | dùng config S | —             | 35% (S5★)  |

---

## Notes

- Effect 1 là reactive — trigger khi đối thủ đến Resort, không phải lượt của player
- Effect 2 giống SK_TEDDY nhưng rate khác
- Effect 2: secondary rate cố định 70% (không phụ thuộc rank/star)
- Stub AI: Effect 1 — di chuyển theo; Effect 2 — xử lý như Teddy
