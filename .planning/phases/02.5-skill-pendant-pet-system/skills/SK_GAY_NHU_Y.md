# Skill: Gậy Như Ý

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_GAY_NHU_Y |
| Name | Gậy Như Ý |
| Trigger | 2 trigger riêng biệt (xem bên dưới) |

---

## Effect 1 — Đi theo đối thủ đến Travel tile

**Trigger (reactive):** Khi đối thủ di chuyển đến **ô Du Lịch (Travel tile, spaceId=9)**.

**Activation:** `random(0, 100) < rate1_at_star`

**Effect:** Player di chuyển **forward** đến cùng ô Du Lịch đó (không teleport).
- Đi qua START → nhận thưởng passing bonus bình thường
- Tile effect tại ô Du Lịch **xảy ra bình thường** với player (SK_TOC_CHIEN, PT_SIEU_TAXI, v.v.)

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

## Effect 2 — Xây Biểu Tượng + Di chuyển đến Travel tile

**Trigger:** UPGRADE phase — khi xây nhà (bất kỳ level nào).

**Activation:** `random(0, 100) < rate2_at_star`

**Effect chain** (giống SK_TEDDY):
1. Nâng cấp thẳng lên **L5 (Biểu Tượng)** — player chỉ trả tiền cho các level đã chọn xây (ví dụ: chọn xây đến L1 hoặc L2 → trả tiền L1/L2), các level còn lại đến L5 **miễn phí**
2. Nếu active → check tiếp: `random(0, 100) < 70` → di chuyển đến ô Du Lịch (Travel tile)

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

- Effect 1 là reactive — trigger khi đối thủ đến Travel tile (ô Du Lịch), không phải lượt của player
- Effect 2 giống SK_TEDDY: cùng mechanic (L5 + teleport Travel), chỉ khác secondary rate (70% vs 60%)
- Effect 2: secondary rate cố định 70% (không phụ thuộc rank/star)
- **Mutually exclusive với SK_TEDDY**: không thể trang bị cả hai cùng lúc
- Stub AI: Effect 1 — di chuyển theo; Effect 2 — xử lý như Teddy
