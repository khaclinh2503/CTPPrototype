# Game Design Document — CTPPrototype Core Game
> Trạng thái: **Phase 1 + Phase 2 đã implement** (Phase 2.5 trở đi chưa có)
> Cập nhật: 2026-04-02

---

## 1. Tổng quan

**Thể loại:** Boardgame Cờ Tỷ Phú (Monopoly-style), toàn bộ người chơi là AI, headless simulation.

**Mục tiêu:** AI tự động hoàn chỉnh một ván đấu, lưu kết quả, và dùng lịch sử đó để chơi tốt hơn ở ván tiếp theo.

**Platform:** Desktop (Python), chạy headless không cần màn hình.

---

## 2. Cấu hình game (Board.json)

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `limitTurn` | 25 | Số lượt tối đa trước khi kết thúc ván |
| `limitTime` | 1500 | Giới hạn thời gian (giây) — chưa dùng |
| `actionTimeout` | 15 | Timeout cho mỗi action AI — chưa dùng |
| `acquireRate` | 1.0 | Hệ số giá mua cưỡng bức (acquisition) |
| `sellRate` | 0.5 | Hệ số giá bán tài sản (50% giá trị đầu tư) |
| `winReward` | 0.9 | Phần thưởng chiến thắng — chưa dùng |
| `BASE_UNIT` | 1,000 | Đơn vị tiền tệ (nhân tất cả config) |
| `STARTING_CASH` | 1,000,000 | Tiền khởi đầu mỗi player |

---

## 3. Bàn cờ

**32 ô**, bố cục 1 vòng, theo chiều kim đồng hồ, vị trí 1-32. Config đọc từ `Board.json → SpacePositionN`.

| Map | SpacePosition | Ô đặc trưng |
|-----|--------------|-------------|
| Map 1 | SpacePosition0 | TAX (pos 31) |
| Map 2 | SpacePosition1 | GOD ×4 (pos 5, 13, 21, 29) |
| Map 3 | SpacePosition6 | WATER_SLIDE ×4 (pos 2, 10, 18, 26) |

### Loại ô (SpaceId Enum)

| ID | Tên | Map 1 | Map 2 | Map 3 | Mô tả |
|----|-----|-------|-------|-------|-------|
| 1 | FESTIVAL | pos 17 | pos 17 | pos 9 | Góc lễ hội |
| 2 | CHANCE | 3 ô | 3 ô | 3 ô | Ô cơ hội — rút thẻ |
| 3 | CITY | 18 ô | 16 ô | 16 ô | Ô đất thành phố |
| 4 | GAME | pos 3 | pos 3 | pos 4 | Ô mini-game đỏ đen |
| 5 | PRISON | pos 9 | pos 9 | pos 17 | Ô tù / góc phạt |
| 6 | RESORT | 5 ô | 4 ô | 4 ô | Ô nghỉ dưỡng (opt 101/102) |
| 7 | START | pos 1 | pos 1 | pos 1 | Ô xuất phát |
| 8 | TAX | pos 31 | — | — | Ô thuế |
| 9 | TRAVEL | pos 25 | pos 25 | pos 25 | Ô du lịch / teleport |
| 10 | GOD | — | 4 ô | — | Ô thần (xem mục 12) |
| 40 | WATER_SLIDE | — | — | 4 ô | Ô cầu trượt nước (stub) |

### Sơ đồ bàn cờ — Map 1 (SpacePosition0)

```
Pos  1: START
Pos  2: CITY (opt 1)
Pos  3: GAME
Pos  4: CITY (opt 2)
Pos  5: RESORT (opt 101)
Pos  6: CITY (opt 3)
Pos  7: CITY (opt 4)
Pos  8: CITY (opt 5)
Pos  9: PRISON
Pos 10: RESORT (opt 102)
Pos 11: CITY (opt 6)
Pos 12: CITY (opt 7)
Pos 13: CHANCE
Pos 14: CITY (opt 8)
Pos 15: RESORT (opt 101)
Pos 16: CITY (opt 9)
Pos 17: FESTIVAL
Pos 18: CITY (opt 10)
Pos 19: RESORT (opt 101)
Pos 20: CITY (opt 11)
Pos 21: CHANCE
Pos 22: CITY (opt 12)
Pos 23: CITY (opt 13)
Pos 24: CITY (opt 14)
Pos 25: TRAVEL
Pos 26: RESORT (opt 102)
Pos 27: CITY (opt 15)
Pos 28: CITY (opt 16)
Pos 29: CHANCE
Pos 30: CITY (opt 17)
Pos 31: TAX
Pos 32: CITY (opt 18)
```

### Sơ đồ bàn cờ — Map 2 (SpacePosition1)

```
Pos  1: START
Pos  2: CITY (opt 1)
Pos  3: GAME
Pos  4: CITY (opt 2)
Pos  5: GOD (opt 1)
Pos  6: CITY (opt 3)
Pos  7: CITY (opt 4)
Pos  8: RESORT (opt 101)
Pos  9: PRISON
Pos 10: CHANCE
Pos 11: CITY (opt 5)
Pos 12: CITY (opt 6)
Pos 13: GOD (opt 2)
Pos 14: CITY (opt 7)
Pos 15: RESORT (opt 101)
Pos 16: CITY (opt 8)
Pos 17: FESTIVAL
Pos 18: CITY (opt 9)
Pos 19: CHANCE
Pos 20: CITY (opt 10)
Pos 21: GOD (opt 3)
Pos 22: CITY (opt 11)
Pos 23: CITY (opt 12)
Pos 24: RESORT (opt 101)
Pos 25: TRAVEL
Pos 26: CITY (opt 13)
Pos 27: CHANCE
Pos 28: CITY (opt 14)
Pos 29: GOD (opt 4)
Pos 30: CITY (opt 15)
Pos 31: RESORT (opt 102)
Pos 32: CITY (opt 16)
```

### Sơ đồ bàn cờ — Map 3 (SpacePosition6)

```
Pos  1: START
Pos  2: WATER_SLIDE (opt 1)
Pos  3: CITY (opt 1)
Pos  4: GAME
Pos  5: CITY (opt 2)
Pos  6: CITY (opt 3)
Pos  7: CITY (opt 4)
Pos  8: RESORT (opt 101)
Pos  9: FESTIVAL
Pos 10: WATER_SLIDE (opt 2)
Pos 11: CHANCE
Pos 12: CITY (opt 5)
Pos 13: CITY (opt 6)
Pos 14: CITY (opt 7)
Pos 15: RESORT (opt 101)
Pos 16: CITY (opt 8)
Pos 17: PRISON
Pos 18: WATER_SLIDE (opt 3)
Pos 19: CITY (opt 9)
Pos 20: CHANCE
Pos 21: CITY (opt 10)
Pos 22: CITY (opt 11)
Pos 23: CITY (opt 12)
Pos 24: RESORT (opt 101)
Pos 25: TRAVEL
Pos 26: WATER_SLIDE (opt 4)
Pos 27: CITY (opt 13)
Pos 28: CHANCE
Pos 29: CITY (opt 14)
Pos 30: CITY (opt 15)
Pos 31: RESORT (opt 102)
Pos 32: CITY (opt 16)
```
---

## 4. Vòng lặp game (FSM)

Mỗi lượt của một player chạy qua **7 phase** theo thứ tự:

```
ROLL → MOVE → RESOLVE_TILE → ACQUIRE → UPGRADE → CHECK_BANKRUPTCY → END_TURN
```

### 4.1 ROLL — Tung xúc xắc

- Tung 2d6 (mỗi con 1–6).
- **Đổ đôi (doubles):** player được đổ lại ngay trong cùng lượt.
- **Đổ đôi 3 lần liên tiếp:** vào tù ngay, không di chuyển.
- **Đang ở tù:** xem mục 4.7.

### 4.2 MOVE — Di chuyển

- Di chuyển theo tổng 2 xúc xắc.
- **Đi qua ô START (vị trí 1):** nhận thưởng `passingBonusRate × STARTING_CASH = 15% × 1,000,000 = 150,000`.
- Nếu đổ đôi và không ở tù → sau khi giải quyết lượt, bắt đầu lượt mới ngay.

### 4.3 RESOLVE_TILE — Xử lý ô

Gọi `TileStrategy.on_land` tương ứng với loại ô player đang đứng.

Bổ sung sau khi resolve:
- Nếu ô là CITY **chưa có chủ**: `_try_buy_property` → mua và xây lên tối đa (xem 5.1).
- Nếu ô là CITY **của chính mình**: đánh dấu eligible để upgrade (xem 5.2).

### 4.4 ACQUIRE — Mua cưỡng bức

Nếu ô là CITY **của đối thủ** và chưa max level (< L5):
- Tính `acquire_price = level_1_build × BASE_UNIT × acquireRate`.
- Nếu player đủ tiền: **bắt buộc** mua, chủ cũ không có quyền từ chối.
- Transfer: player trả tiền → chủ cũ nhận, ownership chuyển.

### 4.5 UPGRADE — Nâng cấp đất

Với mỗi ô trong danh sách eligible:
- Xây từng cấp liên tiếp lên đến `max_level` (đủ tiền thì xây).
- `max_level` mặc định là **4**.
- Khi ô đang ở **L4** (đã xây đủ L1→L4): `max_level = 5` → cho phép xây Landmark (L5).

### 4.6 CHECK_BANKRUPTCY — Kiểm tra phá sản

- Nếu `player.cash < 0`: kích hoạt `resolve_bankruptcy`.
  - Bán đất **rẻ nhất trước** (theo `calc_invested_build_cost`).
  - Giá bán = `sellRate (50%) × tổng build cost đã đầu tư`.
  - Lặp đến khi `cash ≥ 0` hoặc hết đất.
  - Nếu vẫn `cash < 0` sau khi bán hết: `is_bankrupt = True` → loại khỏi game.

### 4.7 Luật Tù (PRISON)

Khi vào tù: `prison_turns_remaining = 2`.

Đầu lượt (ở trong ROLL phase), nếu `prison_turns_remaining > 0`:

| Tình huống | Hành động |
|-----------|-----------|
| Đủ tiền trả phí | Trả `escapeCostRate × STARTING_CASH = 10% × 1M = 100,000` → thoát, đổ xúc xắc bình thường |
| Không đủ tiền | Đổ xúc xắc (bắt buộc): ra đôi → thoát tù nhưng **kết thúc lượt ngay** (không di chuyển); không ra đôi → ở tiếp |
| Hết 2 lượt (hạn chế) | Tự động thoát tù, đổ xúc xắc và di chuyển bình thường |

### 4.8 END_TURN — Kết thúc lượt

- Nếu đổ đôi (và không ở tù): quay lại ROLL, chơi lần nữa.
- Nếu không đổ đôi: chuyển sang player tiếp theo.
- Nếu `current_turn ≥ max_turns` hoặc chỉ còn ≤1 player: game over.

---

## 5. Hệ thống Đất (CITY Tiles)

### 5.1 Mua đất trống

Khi dừng ở CITY chưa có chủ (tự động, không hỏi — headless AI):
- Giá L1 = `building["1"]["build"] × BASE_UNIT`.
- Mua L1, rồi **tiếp tục xây ngay lên đến L4** nếu đủ tiền cho từng cấp liên tiếp.
- Kết quả: property có thể đạt L1–L4 ngay lần mua đầu tiên tùy túi tiền.
- Thiết lập `tile.owner_id`, `tile.building_level`, cập nhật `player.owned_properties`.

### 5.2 Bảng giá đất (opt=1 làm ví dụ)

Hai hệ số trong config (mỗi level đều có):
- **`build`** — hệ số xây/nâng cấp cho từng cấp. Chi phí mỗi cấp = `build × BASE_UNIT`.
- **`toll`** — hệ số phí thuê cho từng cấp. **Cả `build` và `toll` đều tính tổng cộng dồn.**

| Level | `build` (cấp đó) | `toll` (cấp đó) | Chi phí xây cộng dồn | Phí thuê cộng dồn |
|-------|-----------------|-----------------|----------------------|-------------------|
| L1    | 10              | 1               | 10 × 1,000 = **10,000**  | 1 × 1,000 = **1,000** |
| L2    | 5               | 3               | (10+5) × 1,000 = **15,000** | (1+3) × 1,000 = **4,000** |
| L3    | 15              | 10              | (10+5+15) × 1,000 = **30,000** | (1+3+10) × 1,000 = **14,000** |
| L4    | 25              | 28              | (10+5+15+25) × 1,000 = **55,000** | (1+3+10+28) × 1,000 = **42,000** |
| L5    | 25              | 125             | (10+5+15+25+25) × 1,000 = **80,000** | (1+3+10+28+125) × 1,000 = **167,000** |

> Mỗi opt có giá khác nhau; opt tăng → đất đắt hơn (opt 16 có L1 build = 100).

### 5.3 Thu tiền thuê

Khi dừng ở đất của đối thủ:

```
rent = sum(toll[1..current_level]) × BASE_UNIT × multiplier
```

**Multiplier cộng dồn** — base = 1, mỗi effect active cộng thêm +1:

| Effect | Điều kiện | Cộng |
|--------|-----------|------|
| Base | Luôn có | +1 |
| Đất vàng | `is_golden = True` | +1 |
| Full color set | Chủ sở hữu toàn bộ đất cùng màu | +1 |
| *(future effects)* | *(mỗi effect mới thêm vào đây)* | +1 |

Ví dụ: golden + full color set → multiplier = 3 → toll × 3.

- Player trả → chủ nhận.

### 5.4 Mua cưỡng bức (Acquisition)

- Chỉ xảy ra khi: đất thuộc đối thủ **và** `building_level < 5`.
- `acquire_price = level_1_build × BASE_UNIT × acquireRate (1.0)`.
- Stub AI: **luôn mua** nếu đủ tiền.

---

## 6. Hệ thống Resort (RESORT Tiles)

Resort có cơ chế đơn giản hơn CITY:

| Tham số | Giá trị |
|---------|---------|
| Giá mua | `initCost (50) × BASE_UNIT = 50,000` |
| Max level | 3 |
| Toll cơ sở | `tollCost (40) × BASE_UNIT = 40,000` |
| Công thức toll | `int(tollCost × increaseRate^level) × BASE_UNIT` |

- Không có acquisition (chỉ CITY mới có).
- Auto-buy khi dừng ở Resort chưa có chủ (giống CITY).

---

## 7. Ô Thuế (TAX)

> Hiện tại không có trong Map 1, nhưng logic đã implement.

- `tax = taxRate (10%) × tổng build cost đầu tư tất cả property đang sở hữu`.
- Nếu không có property: thuế = 0.

---

## 8. Ô Du lịch (TRAVEL — vị trí 25)

Mechanic 2 lượt:

**Lượt 1 — dừng ô Travel:**
- Set `pending_travel = True`, kết thúc lượt ngay (không di chuyển).

**Lượt 2 — đầu lượt kế:**
- FSM chọn ngẫu nhiên 1 ô **CITY hoặc RESORT** làm đích.
- Phí = `travelCostRate (0.02) × STARTING_CASH = **20,000**`.
- Stub AI: chấp nhận nếu đủ tiền, từ chối nếu không đủ.
- **Chấp nhận:** trả phí → teleport → kết thúc lượt.
- **Từ chối / không đủ tiền:** không di chuyển → kết thúc lượt.
- Cả 2 trường hợp đều **không roll xúc xắc** lượt đó.

---

## 9. Ô Lễ hội (FESTIVAL — vị trí 17)

| Tham số config | Giá trị | Ý nghĩa |
|----------------|---------|---------|
| `holdCostRate` | 0.02 | Tỷ lệ phí lễ hội |
| `maxFestival` | 1 | Chỉ 1 ô festival trên map tại 1 thời điểm |

**Khi player dừng ở ô Festival:**
- Player chọn 1 ô **CITY hoặc RESORT** bất kỳ trên map để tổ chức lễ hội.
- Ô được chọn trở thành "festival tile" — xóa festival cũ nếu có (maxFestival = 1).
- Stub AI: chọn ngẫu nhiên.

**Khi player dừng vào ô đang tổ chức lễ hội (CITY hoặc RESORT):**
- Trả phí lễ hội = `holdCostRate × STARTING_CASH = 0.02 × 1,000,000 = **20,000**` cho hệ thống (không ai nhận).
- Phí này cộng thêm vào các hiệu ứng khác của ô (thuê, acquisition...) — không thay thế.

---

## 10. Mini-game (GAME — vị trí 3)

**3-round đỏ đen (50/50):**

| Round | Mức cược (Stub: costOptions[0]) | Thắng | Thua |
|-------|--------------------------------|-------|------|
| 1 (bắt buộc) | 5% × 1M = 50,000 | Nhận `bet × 2^1 = 100,000` | Mất 50,000, dừng |
| 2 (tùy chọn) | 10% × 1M = 100,000 | Nhận `bet × 2^2 = 400,000` | Mất 100,000, dừng |
| 3 (tùy chọn) | 15% × 1M = 150,000 | Nhận `bet × 2^3 = 1,200,000` | Mất 150,000 |

**Stub AI hiện tại:** luôn chọn mức cược tối thiểu (`costOptions[0]`), dừng sau round 1 (không tiếp tục dù thắng).

---

## 11. Ô Tù (PRISON — vị trí 9)

- Khi **dừng** ở ô tù: `prison_turns_remaining = 2`.
- Khi **đổ đôi 3 lần liên tiếp**: vào tù ngay, không di chuyển.
- Phí thoát tù: `escapeCostRate (10%) × STARTING_CASH = 100,000`.
- Xem chi tiết tại 4.7.

---

## 12. Ô Thần (GOD — vị trí 5, 13, 21, 29)

> Chỉ xuất hiện trên **Map 2** (SpacePosition1).

### Khi đổ đôi vào ô Thần

| Điều kiện | Hành động |
|-----------|-----------|
|  (lượt đầu tiên của player) | Chọn 1 CITY chưa có chủ → mua + xây level 1, phí bình thường |
|  (từ lượt 2 trở đi) | Chọn **Xây nhà** hoặc **Nâng ô** |

**Xây nhà:** nâng cấp 1 CITY đang sở hữu lên 1 level, trả phí bình thường.

**Nâng ô:** đánh dấu 1 ô bất kì trên map bị nâng lên.
- Toàn map chỉ có **1 ô được nâng** tại 1 thời điểm.
- Khi player khác di chuyển và gặp ô nâng trong đường đi:
  1. Player dừng tại ô đó (không đi tiếp).
  2. Ô hạ xuống → resolve effect của ô đó bình thường.
  3. Lượt kết thúc — **đổ đôi không được đổ lại**.

Events:  (mua/nâng cấp),  (nâng ô),  (hạ ô).

---

## 13. Ô Cơ hội (CHANCE — vị trí 10, 19, 27)

**Stub hiện tại:** publish event `CARD_DRAWN` nhưng không áp dụng hiệu ứng thẻ.

Config: `Card.json` đã load, schema validate, nhưng card effects chưa implement.

---

## 14. Player Model

```
Player:
  player_id: str
  cash: int                      # Tiền mặt, khởi đầu 1,000,000
  position: int                  # Vị trí trên bàn (1-32)
  is_bankrupt: bool              # True khi bị loại
  owned_properties: list[int]    # Danh sách vị trí đang sở hữu
  prison_turns_remaining: int    # 0 = tự do, >0 = đang ở tù
  turns_taken: int               # Số lượt đã hoàn thành (dùng cho God tile)
```

**Chưa implement (Phase 2.5):**
- `skills: list[SkillEntry]` — 5 slot
- `pendants: list[PendantEntry]` — 3 slot
- `pet: PetEntry` — 1 slot
- `effective_stat(stat)` — tính giá trị sau khi stack tất cả buff

---

## 15. Điều kiện kết thúc ván

| Điều kiện | Kết quả |
|-----------|---------|
| Chỉ còn 1 player không phá sản | Player đó thắng |
| Đạt `max_turns = 25` | Player có cash cao nhất thắng |

---

## 16. Trạng thái stub / chưa hoàn chỉnh

| Tính năng | Trạng thái | Phase xử lý |
|-----------|------------|-------------|
| Card effects (CHANCE) | Stub — event publish nhưng không apply | Phase 3 |
| TRAVEL đích thật | Teleport về Start thay vì đích config | Phase 2.5? |
| GOD tile effect | **Implemented** — mua đất (turn 1), xây nhà/nâng ô (turn 2+) | ✅ |
| WATER_SLIDE | Không làm gì | Map 3 |
| Mini-game round 2, 3 | Stub — dừng sau round 1 | AI Phase 3 |
| Acquisition decision AI | Luôn mua nếu đủ tiền | AI Phase 3 |
| Sell decision AI | Bán rẻ nhất trước (không tính chiến lược) | AI Phase 3 |
| Skills / Pendant / Pet | Schema validate OK, chưa apply vào gameplay | Phase 2.5 |
| Festival accumulation | Publish event nhưng chưa track pool | Phase 2.5? |
| History / SQLite | Chưa implement | Phase 3 |
| Pygame visualization | Chưa implement | Phase 4 |

---

## 17. Kiến trúc code

```
ctp/
├── config/         — Board.json, Card.json, skills.yaml, pendants.yaml, pets.yaml, game_rules.yaml
├── core/
│   ├── board.py    — Board, Tile, SpaceId enum
│   ├── models.py   — Player dataclass
│   ├── events.py   — EventBus, GameEvent, EventType
│   └── constants.py — BASE_UNIT, STARTING_CASH, calc_invested_build_cost()
├── tiles/
│   ├── registry.py — TileRegistry (SpaceId → Strategy)
│   ├── land.py     — LandStrategy (CITY, chỉ thu thuê)
│   ├── resort.py   — ResortStrategy
│   ├── prison.py   — PrisonStrategy
│   ├── travel.py   — TravelStrategy
│   ├── tax.py      — TaxStrategy
│   ├── festival.py — FestivalStrategy
│   ├── fortune.py  — FortuneStrategy (CHANCE)
│   ├── game.py     — GameStrategy (MINI-GAME)
│   ├── god.py      — GodStrategy (Map 2: mua đất / xây nhà / nâng ô)
│   └── water_slide.py — WaterSlideStrategy (stub)
└── controller/
    ├── fsm.py         — GameController, TurnPhase FSM
    ├── acquisition.py — resolve_acquisition()
    ├── upgrade.py     — resolve_upgrades()
    └── bankruptcy.py  — resolve_bankruptcy()
```

**Pattern kiến trúc:** MVC + EventBus + Strategy (mỗi loại ô là 1 Strategy class).

---

*GDD này mô tả đúng code đang chạy tính đến Phase 2. Khi Phase 2.5+ hoàn thành, cần cập nhật mục 14 và 16.*
