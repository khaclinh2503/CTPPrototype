# Skill: Hồ Điệp

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_HO_DIEP |
| Name | Hồ Điệp |
| Trigger | 2 trigger riêng biệt (xem bên dưới) |

---

## Effect 1 — Ném tù

**Trigger (reactive):** Trong lượt của đối thủ, nếu đối thủ **active bất kỳ skill nào** trong danh sách sau:

**Activation:** `random(0, 100) < rate1_at_star`

**Skills kích hoạt HồĐiệp:**
- `SK_HQXX` — extra roll
- `SK_TOC_CHIEN` — extra roll sau Travel
- `SK_JOKER` — extra roll sau thoát tù
- `SK_MOONWALK` — chọn hướng di chuyển
- `SK_XXCT` — điều chỉnh ±1 bước
- `SK_SO_10` — dùng Travel ngay lập tức
- `SK_GAY_NHU_Y Effect 1` — follow đối thủ đến Resort

**Effect:** Ném đối thủ vào tù (`opponent.enter_prison()`).

### Rate 1 Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 44%         | +4%             | 60%         |
| S    | 1★       | 64%         | +4%             | 80%         |
| R    | —        | dùng config S | —             | 80% (S5★)  |

---

## Effect 2 — Di chuyển đến ô đất trống gần nhất

**Trigger:** Khi **xây nhà** (bất kỳ lần nâng cấp nào) trong khi đang sở hữu **cặp màu** (≥2 ô CITY cùng màu).

**Activation:** `random(0, 100) < rate2_at_star`

**Effect:** Di chuyển player đến **ô đất trống gần nhất cùng hàng** (cùng cạnh bàn cờ với ô vừa xây).
- "Đất trống" = CITY tile chưa có chủ (`owner_id is None`)
- "Gần nhất" = ô CITY trống gần nhất tính theo vị trí trên cạnh đó
- Tile effect tại ô đến **không xảy ra** (chỉ di chuyển, không trigger on_land)

### Rate 2 Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 30%         | +4%             | 46%         |
| S    | 1★       | 45%         | +4%             | 61%         |
| R    | —        | dùng config S | —             | 61% (S5★)  |

---

## Notes

- Effect 1 là **reactive** — check khi đối thủ active bất kỳ skill nào trong danh sách (HQXX, TốcChiến, Joker, Moonwalk, XXCT_2, SO_10, GậyNhưÝ Effect 1)
- Effect 2: nếu không có ô đất trống nào cùng hàng → skill fail silently
- Effect 2: tile effect không trigger (player chỉ repositioned, không on_land)
- Stub AI: không cần logic đặc biệt cho cả 2 effect
