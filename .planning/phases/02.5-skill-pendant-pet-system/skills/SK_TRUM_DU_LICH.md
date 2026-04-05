# Skill: Trùm Du Lịch

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_TRUM_DU_LICH |
| Name | Trùm Du Lịch |
| Trigger | 2 trigger riêng biệt (xem bên dưới) |

---

## Effect 1 — Tạo thêm nhà mới

**Trigger:** Khi **mua đất mới** (ô trống chưa có chủ) HOẶC **mua lại đất** (acquisition từ đối thủ).

**Activation:** `random(0, 100) < rate1_at_star`

**Effect:** Lấy **1 ô CITY trống ngẫu nhiên** trên map, đặt level = level của ô vừa mua/xây. **Miễn phí.**

```
unowned = [t for t in board.tiles if t.space_id == SpaceId.CITY and t.owner_id is None]
if unowned:
    chosen = random.choice(unowned)
    chosen.owner_id = player.player_id
    chosen.building_level = newly_acquired_tile.building_level
```

### Rate 1 Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 21%         | +1%             | 25%         |
| S    | 1★       | 26%         | +1%             | 30%         |
| R    | —        | dùng config S | —             | 30% (S5★)  |

---

## Effect 2 — Mua Resort của đối thủ

**Trigger:** RESOLVE_TILE phase — khi dừng tại **Khu Du Lịch (Resort)** của đối thủ.

**Activation:** `random(0, 100) < rate2_at_star`

**Effect:** Player được phép mua Resort đó theo **giá acquisition** (forced sale — chủ không có quyền từ chối).

- Giá: `acquisition_price` theo config (acquireRate × initCost)
- Nếu player không đủ tiền → skill fail silently (không mua được)
- Tile effect (trả toll Resort) **vẫn xảy ra trước** khi check skill

### Rate 2 Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 15%         | +5%             | 35%         |
| S    | 1★       | 30%         | +5%             | 50%         |
| R    | —        | dùng config S | —             | 50% (S5★)  |

---

## Notes

- Effect 1: nếu không còn ô CITY trống trên map → fail silently
- Effect 2: toll Resort trả trước, sau đó mới check skill acquisition
- Stub AI: Effect 2 — luôn mua nếu đủ tiền
