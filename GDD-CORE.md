# Game Design Document — CTPPrototype Core Game
> Trạng thái: **Phase 1 + Phase 2 + Phase 2.1 + Phase 02.1.1 (Pygame UI) đã implement** (Phase 2.5 trở đi chưa có)
> Cập nhật: 2026-04-04

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
| 40 | WATER_SLIDE | — | — | 4 ô | Ô cầu trượt nước (xem mục 12.1) |

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

Mỗi lượt của một player chạy qua **7 phase** theo thứ tự, với rẽ nhánh sớm tại RESOLVE_TILE:

```
ROLL → MOVE → RESOLVE_TILE ─┬─ (cash < 0) → CHECK_BANKRUPTCY → END_TURN
                             └─ (cash ≥ 0) → ACQUIRE → UPGRADE → END_TURN
```

> CHECK_BANKRUPTCY chỉ trigger khi mất tiền thụ động (thuê, thuế). Mua nhà/nâng cấp có `can_afford` check nên không bao giờ gây âm tiền.

### 4.1 ROLL — Tung xúc xắc

- Tung 2d6 (mỗi con 1–6).
- **Đổ đôi (doubles):** player được đổ lại ngay trong cùng lượt.
- **Đổ đôi 3 lần liên tiếp:** vào tù ngay, không di chuyển.
- **Đang ở tù:** xem mục 4.7.
- **Đổ Chính Xác (Căn Lực):** trước khi tung xúc xắc, player có thể kích hoạt căn lực — chọn 1 trong 4 khoảng đích `[(2,4),(5,7),(7,9),(10,12)]`, sau đó tung xúc xắc thông thường. Nếu tổng xúc xắc nằm trong khoảng đã chọn, precision check pass (`random() < accuracy_rate`), xúc xắc được giữ trong khoảng; nếu không pass, tung lại ngẫu nhiên. AI ưu tiên chọn khoảng đưa đến ô CITY/RESORT chưa có chủ gần nhất. Base accuracy: `accuracy_rate = 15%` (Player field). Decrement `double_toll_turns` xảy ra đầu phase ROLL (trước căn lực).

### 4.2 MOVE — Di chuyển

- Di chuyển theo tổng 2 xúc xắc.
- **Đi qua ô START (vị trí 1):** nhận thưởng `passingBonusRate × STARTING_CASH = 15% × 1,000,000 = 150,000`.
- **Dừng tại ô START:** chọn 1 ô CITY đang sở hữu chưa max (< L5) để nâng cấp lên 1 level, trả phí bình thường. Nếu không sở hữu ô nào hoặc không đủ tiền, không có hiệu ứng.
- **Gặp ô nâng (GOD):** dừng tại ô nâng, ô hạ xuống, resolve bình thường, huỷ đổ đôi.
- **Đi vào vùng sóng (WATER_SLIDE):** bị đẩy đến ô đích, resolve bình thường, đổ đôi không bị huỷ.
- Nếu đổ đôi và không ở tù → sau khi giải quyết lượt, bắt đầu lượt mới ngay.

### 4.3 RESOLVE_TILE — Xử lý ô

Gọi `TileStrategy.on_land` tương ứng với loại ô player đang đứng. Với CITY/RESORT, rẽ theo 3 nhánh:

#### Nhánh A — Ô chưa có chủ
1. Check player có đủ tiền mua L1 không.
2. Nếu đủ tiền: đưa ra **2 lựa chọn**:
   - **Mua** → chọn **chính xác cấp muốn dừng lại** (L1, L2, L3, hoặc L4) theo chiến thuật:
     - Chỉ mua L1 (cắm cờ, giữ tiền mặt).
     - Mua đến L2, L3, hoặc L4 (tối đa lần đầu).
     - Mỗi cấp chỉ mua được nếu đủ tiền cấp đó.
   - **Không mua** → bỏ qua, kết thúc resolve.
3. Nếu không đủ tiền mua L1: bỏ qua.
4. → Tiếp tục sang ACQUIRE.

> *Headless AI hiện tại: luôn mua nếu đủ tiền, tự xây đến L3 hoặc đến khi hết tiền.*

#### Nhánh B — Ô của chính mình
1. Check cấp nhà hiện tại:
   - Chưa L4 (`building_level < 4`): player **chọn nâng lên cấp nào** (theo chiến thuật) trong phạm vi hiện tại→L4, mỗi cấp phải đủ tiền.
   - Đã L4 → player **chọn có xây Landmark (L5) không** nếu đủ tiền; có thể từ chối để giữ cash.
   - Đã L5 (Landmark): không làm gì.
2. → Tiếp tục sang ACQUIRE.

#### Nhánh C — Ô của đối thủ
1. Tính tiền thuê và trừ vào cash player (xem 5.3).
2. **Rẽ nhánh sớm (early bankruptcy):**
   - Nếu `player.cash < 0` → chuyển thẳng sang `CHECK_BANKRUPTCY`, bỏ qua ACQUIRE và UPGRADE.
   - Nếu `player.cash ≥ 0` → tiếp tục flow bình thường sang ACQUIRE.

### 4.4 ACQUIRE — Mua cưỡng bức

Nếu ô là CITY **của đối thủ** và chưa Landmark (< L5):
- Tính `acquire_price = tổng build cost các cấp đã xây × acquireRate`.
- Player **chọn có cướp hay không** theo chiến thuật (không bắt buộc).
- Điều kiện: phải đủ tiền `acquire_price` mới được chọn.
- Chủ cũ **không có quyền từ chối**.
- Transfer: player trả tiền → chủ cũ nhận, ownership chuyển, **building_level giữ nguyên**.
- **Resort không bị Acquire** (chỉ có thể cướp Resort qua skill đặc biệt trong tương lai).

### 4.5 UPGRADE — Nâng cấp đất

Với mỗi ô trong danh sách eligible:
- Xây từng cấp liên tiếp lên đến `max_level` (đủ tiền thì xây).
- `max_level` mặc định là **4**.
- Khi ô đang ở **L4** (đã xây đủ L1→L4): `max_level = 5` → cho phép xây Landmark (L5).

### 4.6 CHECK_BANKRUPTCY — Kiểm tra phá sản

Chỉ có ý nghĩa khi player **bị mất tiền thụ động** (thuê đất, thuế) — mua nhà/nâng cấp luôn kiểm tra `can_afford` trước nên không thể gây âm tiền.

Trigger thực tế: sau RESOLVE_TILE khi `cash < 0` (Nhánh C — trả tiền thuê hoặc thuế).

**Flow xử lý:**
1. Bán nhà **rẻ nhất trước** (theo `calc_invested_build_cost`), giá bán = `sellRate (50%) × build cost đã đầu tư`.
2. Lặp đến khi `cash ≥ 0` hoặc hết đất.
3. Nếu vẫn `cash < 0` sau khi bán hết:
   - **Bankruptcy do trả thuê:** toàn bộ tài sản còn lại (cash + tiền bán nhà) chuyển cho chủ đất nhận.
   - **Bankruptcy do nguyên nhân khác:** tài sản trả về pool (không ai nhận).
   - `is_bankrupt = True` → loại khỏi game.

### 4.7 Luật Tù (PRISON)

Khi vào tù: `prison_turns_remaining = 3`.

Đầu lượt (ở trong ROLL phase), nếu `prison_turns_remaining > 0`:

| Tình huống | Hành động |
|-----------|-----------|
| Đủ tiền trả phí | Trả `escapeCostRate × STARTING_CASH = 5% × 1M = 50,000` → thoát, đổ xúc xắc bình thường |
| Không đủ tiền | Đổ xúc xắc (bắt buộc): ra đôi → thoát tù + **di chuyển bình thường** + cuối lượt được đổ thêm; không ra đôi → ở tiếp |
| Hết 3 lượt (hạn chế) | Tự động thoát tù, đổ xúc xắc và di chuyển bình thường |

### 4.8 END_TURN — Kết thúc lượt

- Nếu đổ đôi (và không ở tù): quay lại ROLL, chơi lần nữa.
- Nếu không đổ đôi: chuyển sang player tiếp theo.
- Kiểm tra điều kiện kết thúc ván theo thứ tự (xem mục 15).

---

## 5. Hệ thống Đất (CITY Tiles)

### 5.1 Mua đất trống

Khi dừng ở CITY/RESORT chưa có chủ:
- Giá L1 = `building["1"]["build"] × BASE_UNIT`.
- Player chọn có mua không và **dừng ở cấp nào theo chiến thuật**: L1, L2, L3, hoặc L4.
- Mỗi cấp phải đủ tiền mới mua được; có thể chọn chỉ mua L1 dù đủ tiền L4.
- Tối đa lần mua đầu là **L4** — Landmark (L5) chỉ xây được lần sau khi đã đạt L4.
- Thiết lập `tile.owner_id`, `tile.building_level`, cập nhật `player.owned_properties`.

> *Headless AI: luôn mua nếu đủ tiền L1, xây tiếp đến L3 hoặc đến khi hết tiền.*

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

**Flow trả tiền thuê:**
1. Trừ `rent` khỏi cash player, cộng vào cash chủ đất.
2. Nếu `player.cash < 0` sau khi trả → kích hoạt `resolve_bankruptcy(creditor=chủ_đất)`:
   - Bán **toàn bộ** tài sản (rẻ nhất trước), nhận 50% giá trị đầu tư mỗi ô.
   - Chuyển **toàn bộ cash còn lại** (nếu dương) cho chủ đất.
   - `player.cash = 0`, `is_bankrupt = True` → bị loại khỏi game.

### 5.4 Mua cưỡng bức (Acquisition)

- Chỉ xảy ra khi: đất **CITY** thuộc đối thủ **và** `building_level < 5` (chưa Landmark).
- `acquire_price = sum(build[1..current_level]) × BASE_UNIT × acquireRate`.
- Player **chọn có cướp hay không** theo chiến thuật, phải đủ tiền mới được chọn.
- Chủ cũ không từ chối được; building_level **không thay đổi** sau khi sang tay.
- Resort **không thể** bị Acquire thông thường.

> *Headless AI hiện tại: luôn mua nếu đủ tiền (stub — giá đang tính sai theo L1, cần fix theo công thức mới).*

---

## 6. Hệ thống Resort (RESORT Tiles)

Resort có cơ chế đơn giản hơn CITY:

| Tham số | Giá trị |
|---------|---------|
| Giá mua | `initCost (50) × BASE_UNIT = 50,000` |
| Max level | 3 |
| Toll cơ sở | `tollCost (25) × BASE_UNIT = 25,000` |
| Công thức toll | `int(tollCost × increaseRate^level) × BASE_UNIT` |

- Không có acquisition (chỉ CITY mới có).
- Auto-buy khi dừng ở Resort chưa có chủ (giống CITY).

### 6.1 Multiplier theo nhóm màu (opt)

Mỗi Resort có `opt` là mã nhóm màu (ví dụ: 101, 102). Có 2 loại tình huống:

**Trường hợp 1 — Nhóm có nhiều Resort (>1 ô cùng opt):**

Multiplier tính theo số Resort cùng opt mà **chủ sở hữu đang nắm**:

| Số resort cùng opt chủ sở hữu | Multiplier |
|-------------------------------|------------|
| 1 | ×1 (base) |
| 2 | ×2 |
| 3 | ×4 |

**Trường hợp 2 — Resort đơn (chỉ 1 ô duy nhất có opt đó trên map):**

Multiplier tính theo **tổng số lượt đã nhảy vào** ô đó (`visit_count`), kể cả chủ lẫn đối thủ:

| visit_count | Multiplier |
|-------------|------------|
| 1 | ×1 (base) |
| 2 | ×2 |
| ≥3 | ×4 |

- `visit_count` tăng mỗi khi bất kỳ người chơi nào dừng ở Resort đó (kể cả chủ, không trả tiền nhưng vẫn tính).
- Khi Resort bị bán do phá sản → `visit_count` reset về 0.

### 6.2 Ô Vàng (is_golden) với Resort

Nếu Resort được chọn là ô vàng (`is_golden=True`): toll nhân thêm ×2 **độc lập** với multiplier nhóm màu.

Ví dụ: Resort đơn đã có 2 visit + is_golden → toll × 2 (nhóm) × 2 (vàng) = ×4.

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
| `holdCostRate` | 0.02 | Tỷ lệ phí tổ chức lễ hội |
| `maxFestival` | 1 | Chỉ 1 ô festival trên map tại 1 thời điểm |

**Khi player dừng ở ô Festival:**
1. **Kiểm tra điều kiện:** Player phải **sở hữu ít nhất 1 ô CITY hoặc RESORT** và đủ tiền ≥ `holdCostRate × STARTING_CASH` (= 20,000) mới được tổ chức. Không thỏa → không có hiệu ứng, không mất tiền.
2. **Trả phí tổ chức (1 lần):** `holdCostRate × STARTING_CASH = **20,000**` vào hệ thống (không ai nhận).
3. **Chọn ô:** Player chọn 1 ô **CITY hoặc RESORT của mình** — stub AI chọn ngẫu nhiên trong danh sách đang sở hữu.
4. **Xóa festival cũ** và đặt festival mới tại ô được chọn (maxFestival = 1).

**Khi player khác dừng vào ô đang có festival (CITY hoặc RESORT có chủ):**
- Trả tiền thuê bình thường cho chủ (như thường lệ).
- Trả thêm phí festival tích lũy theo số lần ô đó được chọn (`festival_level`):

| `festival_level` | Tổng phí |
|-----------------|----------|
| 1 (lần đầu) | **×2** toll |
| 2 | **×3** toll |
| 3+ | **×4** toll |

- `festival_level` tích lũy trong ván đang chơi, **reset về 0 khi ván kết thúc**.
- Nếu ô chưa có chủ: không có hiệu ứng festival.

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

- Khi **dừng** ở ô tù: `prison_turns_remaining = 3`.
- Khi **đổ đôi 3 lần liên tiếp**: vào tù ngay, không di chuyển.
- Phí thoát tù: `escapeCostRate (5%) × STARTING_CASH = 50,000`.
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

## 12.1 Ô Cầu Trượt Nước (WATER_SLIDE — vị trí 2, 10, 18, 26)

> Chỉ xuất hiện trên **Map 3** (SpacePosition6).

### Khi player đáp vào ô Water Slide

1. **Sóng cũ bị xóa** vô điều kiện (dù có hay không).
2. Player **chọn 1 ô đích** trong cùng hàng — không tính ô góc (pos 1, 9, 17, 25), không tính chính ô Water Slide.
3. **Sóng nước mới** được tạo từ ô Water Slide → ô đích.
4. Player **trượt ngay đến ô đích** và resolve effect của ô đích bình thường (trả thuê, mua đất, v.v.).

### Sóng nước

- Toàn bàn chỉ tồn tại **1 sóng** tại 1 thời điểm.
- **Vùng sóng:** các ô từ `source + 1` đến `dest` theo chiều tiến của bàn cờ (có thể bao gồm wrap-around).
- Sóng tồn tại **mãi mãi** cho đến khi có người đáp vào ô Water Slide tiếp theo — lúc đó sóng cũ bị xóa, bất kể người đó có tạo sóng mới hay không.

### Khi player khác di chuyển vào vùng sóng

- Nếu bất kỳ ô nào trong đường đi của player nằm trong vùng sóng:
  1. Player bị **đẩy ngay đến ô đích** (`dest`).
  2. Resolve effect của ô đích bình thường.
  3. **Sóng không bị tiêu** — vẫn còn tác dụng với player kế tiếp.
- Player tạo sóng cũng bị đẩy nếu lượt sau đi vào vùng sóng.

### AI headless — chọn dest

| Ưu tiên | Tiêu chí |
|---------|----------|
| 1 | CITY chưa có chủ — ưu tiên ô đắt nhất (giá trị cao nhất) |
| 2 | RESORT chưa có chủ |
| 3 | Ô đang sở hữu (không tốn tiền) |
| 4 | Ô không phải property (GAME, CHANCE, TAX, TRAVEL...) |
| 5 | Ô đối thủ có tiền thuê thấp nhất |

Events: `WATER_SLIDE_WAVE_SET` (sóng tạo/thay thế), `WATER_SLIDE_PUSHED` (player bị đẩy).

---

## 13. Ô Cơ hội (CHANCE — vị trí 10, 19, 27)

**Đã implement đầy đủ (Phase 2.1).** Khi player dừng tại ô CHANCE, `FortuneStrategy.on_land` rút 1 thẻ từ pool và áp dụng hiệu ứng ngay.

### 13.1 Rút thẻ

- Pool load từ `Card.json`, lọc bỏ thẻ `mapNotAvail` cho map hiện tại và thẻ `rate = 0`.
- Rút theo **weighted random** dựa trên trường `rate` của từng thẻ.
- 23 thẻ in-scope (IT_CA_1 – IT_CA_23 theo Card.json, trừ các thẻ bị lọc).

### 13.2 Held cards (lưu trữ, dùng sau)

5 thẻ được lưu vào `player.held_card` thay vì áp dụng ngay. Player dùng khi muốn trong lượt tiếp theo (kích hoạt qua EF_19 trong ROLL hoặc các trigger khác):

| EF | IT_CA | Tên | Hiệu ứng |
|----|-------|-----|----------|
| EF_2  | IT_CA_2  | Giảm Phí     | Giảm 50% tiền thuê khi đạp vào đất đối thủ (tiêu thẻ khi dùng) |
| EF_3  | IT_CA_3  | Bảo Vệ       | Chặn 1 đòn tấn công từ thẻ đối thủ — khi bị tấn công, popup hỏi người chơi có dùng không; chọn "Dùng" → huỷ đòn + tiêu thẻ, chọn "Bỏ qua" → đòn thực hiện bình thường + giữ thẻ |
| EF_19 | IT_CA_21 | Quay lại     | Thoát tù ngay khi bắt đầu lượt ở tù — hiện popup 3 lựa chọn: "Đổ xúc xắc" / "Trả tiền thoát" / "Dùng thẻ" (chỉ khi có thẻ); dùng thẻ → thoát tù + đổ bình thường |
| EF_20 | IT_CA_1  | Thiên Thần   | Miễn 100% tiền thuê khi đạp vào đất đối thủ (tiêu thẻ khi dùng) |
| EF_22 | IT_CA_23 | Chong Chóng  | Khi có ô nâng trong đường đi → popup hỏi "Dùng thẻ / Giữ thẻ"; dùng → bỏ qua ô nâng đi thẳng đến đích + tiêu thẻ; giữ → bị chặn tại ô nâng bình thường + giữ thẻ; AI auto-dùng |

**Popup interaction (Phase 02.1.1):** Khi người chơi người thật (P1) rút được held card:
- **Popup "Lấy thẻ / Bỏ thẻ"** hiện ra ngay sau khi rút — nếu bỏ thì thẻ bị discard, nếu lấy thì lưu vào `held_card` (đè thẻ cũ nếu có).
- **Popup "Dùng thẻ / Giữ thẻ"** hiện ra khi dừng ở đất đối thủ (CITY/RESORT) và đang giữ EF_20 hoặc EF_2 — nếu dùng thì áp dụng hiệu ứng + tiêu thẻ, nếu giữ thì trả toll bình thường.
- **Popup "Dùng thẻ / Bỏ qua" (EF_3)** hiện ra khi bị tấn công bởi thẻ đối thủ và đang giữ IT_CA_3 — nếu dùng thì huỷ đòn tấn công + tiêu thẻ, nếu bỏ qua thì đòn thực hiện bình thường + giữ thẻ. AI luôn dùng thẻ khi bị tấn công.
- **Popup 3 lựa chọn (EF_19)** hiện ra đầu ROLL khi đang ở tù: "Đổ xúc xắc" (luôn có) / "Trả $50,000" (dim nếu không đủ tiền) / "Dùng thẻ Quay Lại" (chỉ hiện nếu đang giữ EF_19). AI: ưu tiên thẻ > tiền > đổ.
- AI (P2/P3/P4): luôn nhận thẻ, luôn dùng khi có cơ hội, luôn dùng EF_3 khi bị tấn công (không popup).

### 13.3 Instant cards (áp dụng ngay)

16+ thẻ áp dụng hiệu ứng ngay khi rút:

| EF | IT_CA | contentId | Tên | Hiệu ứng |
|----|-------|-----------|-----|----------|
| EF_4  | IT_CA_4    | eff_force_sell                    | Bán Nhà              | Ép bán 1 tile có chủ không phải của mình — xem chi tiết bên dưới |
| EF_5  | IT_CA_5    | eff_change_city                   | Đổi Đất              | Hoán đổi 1 CITY của mình (rẻ nhất) ↔ 1 CITY của opponent (đắt nhất) |
| EF_6  | IT_CA_6/7  | eff_alien_invasion / eff_earth_quake | Xâm Lăng / Động Đất | Player chọn 1 CITY của đối thủ (không phải Landmark L5) để hạ 1 bậc; nếu về 0 thì mất quyền sở hữu; nếu không có ô hợp lệ thì bỏ qua hiệu ứng nhưng thẻ vẫn mất; IT_CA_6 mapNotAvail=[1] |
| EF_7  | IT_CA_8/10 | eff_virus / eff_city_black_out    | Dịch Bệnh / Mất Điện | Human player chọn 1 CITY của đối thủ qua popup (có thể bỏ qua, mất thẻ); AI auto-chọn tile cao nhất của richest opponent; sau khi chọn: check shield → tile-level debuff toll=0 (+ cặp màu nếu cùng chủ), 5 lượt, visitor đầu miễn toll + xóa debuff tile đó |
| EF_8  | IT_CA_9    | eff_yellow_sand                   | Cát Vàng             | Human player chọn 1 CITY của đối thủ qua popup (có thể bỏ qua, mất thẻ); AI auto-chọn tile cao nhất của richest opponent; sau khi chọn: check shield → tile-level debuff giảm 50% toll (+ cặp màu nếu cùng chủ), 5 lượt, visitor đầu trả 50% + xóa debuff |
| EF_10 | IT_CA_12   | eff_festival                      | Lễ Hội               | Teleport đến FESTIVAL tile hiện tại |
| EF_11 | IT_CA_13   | eff_festival_tour                 | Tour Lễ Hội          | Teleport đến tile đang tổ chức lễ hội (board.festival_tile_position); nếu không có festival → kết thúc lượt |
| EF_12 | IT_CA_15   | eff_travel                        | Du Lịch              | Teleport đến TRAVEL tile gần nhất, set pending_travel = True |
| EF_13 | IT_CA_14   | eff_exploring                     | Khám Phá             | Teleport đến PRISON, ngồi tù 3 lượt |
| EF_14 | IT_CA_16   | eff_start                         | Về Vạch Xuất Phát    | Di chuyển từng ô về START (move_type=3), nhận passing bonus (15% starting_cash) |
| EF_15 | IT_CA_17   | eff_host_dice_festival            | Tổ Chức Lễ Hội       | Đặt festival marker miễn phí trên tile sở hữu có building_level cao nhất |
| EF_16 | IT_CA_18   | eff_fee                           | Phí Phạt             | Self-debuff: double toll trong 1 lượt tiếp theo |
| EF_17 | IT_CA_19   | eff_city_donate                   | Tặng Đất             | Human: popup bắt buộc 2 bước — chọn 1 tile bất kỳ của mình → chọn người nhận (không thể bỏ qua); AI: tặng tile rẻ nhất cho player nghèo nhất |
| EF_18 | IT_CA_20   | eff_charity                       | Từ Thiện             | Mỗi player (trừ nghèo nhất) đóng 10% starting_cash cho player nghèo nhất |
| EF_21 | IT_CA_22   | eff_god_hand                      | Bàn Tay Thần         | Teleport đến GOD tile gần nhất; mapNotAvail=[1,3] |
| EF_24 | IT_CA_24   | eff_bank                          | Ngân Hàng            | Stub — Map 3 only |
| EF_25 | IT_CA_25   | eff_agency                        | Đại Lý               | Stub — Map 3 only |
| EF_26 | IT_CA_11   | eff_tax                           | Thuế                 | Teleport đến TAX tile gần nhất; mapNotAvail=[2,3] |
| EF_30 | IT_CA_30   | eff_water_slide                   | Cầu Trượt            | Teleport đến WATER_SLIDE tile gần nhất; mapNotAvail=[1,2] |

#### EF_4 — IT_CA_4 "Bán Nhà" (chi tiết)

Khi rút được thẻ này, **popup danh sách** hiện ra ngay, liệt kê tất cả tile đang có chủ và không thuộc về người chơi hiện tại. Mỗi mục hiển thị: `Ô {pos}  lv{building_level}  [{owner_id}]`.

- **Chọn 1 tile** → kiểm tra chủ tile có đang giữ IT_CA_3 (EF_3 Shield) không:
  - Nếu có → popup "Dùng thẻ / Bỏ qua" hiện ra cho chủ tile (chỉ P1; AI luôn dùng). Nếu chủ dùng Shield → đòn bị huỷ, Shield tiêu, không có hiệu lực.
  - Nếu không có (hoặc chủ bỏ qua) → tile bị reset về trạng thái unowned (`building_level = 0`, `owner_id = None`), chủ cũ nhận lại **50% tổng build cost đã đầu tư** vào tile đó.
- **Bỏ qua** (không chọn tile) → không có hiệu lực.
- Thẻ bị tiêu **dù có dùng hay không**.

AI (P2–P4): tự chọn tile có `building_level` cao nhất trong tất cả tile không phải của mình; không có popup.

### 13.4 Toll modifiers (priority order — D-44)

Khi visitor đến ô có chủ, áp dụng theo thứ tự ưu tiên:

1. **Tile virus/yellow-sand** (`tile.toll_debuff_turns > 0`): áp `tile.toll_debuff_rate` (0.0 = miễn phí, 0.5 = giảm 50%), xóa debuff tile ngay (`toll_debuff_turns = 0, toll_debuff_rate = 1.0`)
2. **Double toll** (`player.double_toll_turns > 0`): toll × 2
3. **Angel** (held EF_20): toll = 0, tiêu thẻ
4. **Discount** (held EF_2): toll × 0.5, tiêu thẻ

### 13.5 Virus / Yellow-sand debuff (D-22/D-44/D-46)

**Cơ chế tile-level (EF_7/EF_8):**

1. AI chọn tile CITY có `building_level` cao nhất của opponent.
2. Nếu toàn bộ cặp màu (tất cả tile cùng `color` trong LandSpace) đều thuộc opponent → debuff cả cặp (thường 2–3 tile).
3. Nếu không → chỉ debuff tile đã chọn.
4. Set `tile.toll_debuff_turns = 5`, `tile.toll_debuff_rate = 0.0` (virus) hoặc `0.5` (yellow-sand).
5. **Visitor đầu tiên** nhảy vào tile bị debuff: không trả toll (hoặc trả 50%) + debuff tile đó bị xóa ngay.
6. Nếu không ai ghé: `_do_end_turn()` giảm `tile.toll_debuff_turns -= 1` mỗi lượt, tự hết sau 5 lượt.

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
  # Phase 2.1 — Card & Căn Lực fields
  held_card: str | None          # card_id đang giữ (held card), per D-09
  accuracy_rate: int             # Căn lực base accuracy (%), mặc định 15, per D-10
  double_toll_turns: int         # EF_16 self-debuff rounds còn lại, per D-12
  # virus_turns đã bỏ — EF_7/8 debuff nay là tile-level (tile.toll_debuff_turns/rate)
```

**Chưa implement (Phase 2.5):**
- `skills: list[SkillEntry]` — 5 slot
- `pendants: list[PendantEntry]` — 3 slot
- `pet: PetEntry` — 1 slot
- `effective_stat(stat)` — tính giá trị sau khi stack tất cả buff

---

## 15. Điều kiện kết thúc ván

Kiểm tra theo thứ tự tại cuối mỗi lượt (`END_TURN`):

### 15.1 Instant win — kết thúc ngay lập tức

Player thắng ngay khi đạt 1 trong 3 điều kiện sau (cuối lượt của người đó):

| Điều kiện | `reason` | Mô tả |
|-----------|----------|-------|
| Sở hữu **tất cả ô Resort** trên bàn | `"all_resorts"` | Toàn bộ RESORT trên map hiện tại (Map 1: 5 ô, Map 2: 4 ô) |
| Hoàn thành **3+ nhóm màu** | `"3_color_groups"` | Sở hữu **toàn bộ** CITY trong 3+ màu |
| Sở hữu **toàn bộ CITY + RESORT trong 1 hàng** | `"own_row"` | Một trong 4 hàng: pos 1-8, 9-16, 17-24, 25-32 |

**Nhóm màu — Map 1:**

| Màu | Opts | Vị trí CITY | Số ô |
|-----|------|-------------|------|
| 1 | 1, 2 | 2, 4 | 2 |
| 2 | 3, 4, 5 | 6, 7, 8 | 3 |
| 3 | 6, 7 | 11, 12 | 2 |
| 4 | 8, 9 | 14, 16 | 2 |
| 5 | 10, 11 | 18, 20 | 2 |
| 6 | 12, 13, 14 | 22, 23, 24 | 3 |
| 7 | 15, 16 | 27, 28 | 2 |
| 8 | 17, 18 | 30, 32 | 2 |

**Ô đất + resort trong mỗi hàng — Map 1:**

| Hàng | Pos | CITY | RESORT |
|------|-----|------|--------|
| 1 | 1–8 | 2, 4, 6, 7, 8 | 5 |
| 2 | 9–16 | 11, 12, 14, 16 | 10, 15 |
| 3 | 17–24 | 18, 20, 22, 23, 24 | 19 |
| 4 | 25–32 | 27, 28, 30, 32 | 26 |

> Lưu ý: Mỗi hàng khớp đúng 2 nhóm màu CITY. Sở hữu đủ CITY + RESORT của cả hàng thì thắng `own_row`.

### 15.2 Điều kiện thông thường

| Điều kiện | `reason` | Kết quả |
|-----------|----------|---------|
| Chỉ còn ≤1 player chưa phá sản | `"last_player_standing"` | Player còn lại thắng |
| Đạt `max_turns = 25` | `"max_turns"` | Player có **tổng tài sản** cao nhất thắng |

**Tổng tài sản (dùng khi hết 25 turn):**
```
tổng tài sản = cash + Σ(build_cost đầu tư cho từng cấp đã xây) + Σ(initCost resort đang sở hữu)
```

---

## 16. Trạng thái stub / chưa hoàn chỉnh

| Tính năng | Trạng thái | Phase xử lý |
|-----------|------------|-------------|
| Card effects (CHANCE) | **Implemented** — 23 cards, weighted random, held/instant, toll modifiers | ✅ Phase 2.1 |
| Đổ Chính Xác (Căn Lực) | **Implemented** — 15% base accuracy, 4 khoảng, AI target-aware | ✅ Phase 2.1 |
| Virus debuff (EF_7/8/10) | **Implemented** — tile-level `toll_debuff_turns/rate`, color-pair spread, clear-on-visit, END_TURN decrement | ✅ Phase 2.1 |
| TRAVEL đích thật | Teleport về Start thay vì đích config | Phase 2.5? |
| GOD tile effect | **Implemented** — mua đất (turn 1), xây nhà/nâng ô (turn 2+) | ✅ |
| WATER_SLIDE | **Implemented** — tạo sóng, trượt đến dest, đẩy player vào vùng sóng | ✅ |
| Mini-game round 2, 3 | Stub — dừng sau round 1 | AI Phase 3 |
| Acquisition decision AI | Luôn mua nếu đủ tiền | AI Phase 3 |
| Sell decision AI | Bán rẻ nhất trước (không tính chiến lược) | AI Phase 3 |
| Skills / Pendant / Pet | Schema validate OK, chưa apply vào gameplay | Phase 2.5 |
| Festival accumulation | Implemented: X2/X3/X4 theo `tile.festival_level`, xóa festival cũ | ✅ Done |
| History / SQLite | Chưa implement | Phase 3 |
| Pygame visualization | **Implemented** — BoardRenderer, InfoPanel, SpeedController (pause/1x-10x), walk animation, dice animation, card overlay, debug F8 picker, scoreboard | ✅ Phase 02.1.1 |
| Popup UI (held cards) | **Implemented** — accept_card popup khi rút IT_CA_1/IT_CA_2, use_card popup khi đạp đất đối thủ; callback injection qua `controller.accept_card_fn` / `use_card_fn` | ✅ Phase 02.1.1 |

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
│   ├── fortune.py  — FortuneStrategy (CHANCE) — 23 card effects, held/instant dispatch
│   ├── _toll_modifiers.py — apply_toll_modifiers() — virus/double_toll/angel/discount priority chain
│   ├── game.py     — GameStrategy (MINI-GAME)
│   ├── god.py      — GodStrategy (Map 2: mua đất / xây nhà / nâng ô)
│   └── water_slide.py — WaterSlideStrategy (Map 3: tạo sóng / AI pick_dest)
└── controller/
    ├── fsm.py         — GameController, TurnPhase FSM; accept_card_fn/use_card_fn callback slots
    ├── acquisition.py — resolve_acquisition()
    ├── upgrade.py     — resolve_upgrades()
    └── bankruptcy.py  — resolve_bankruptcy()
ctp/ui/
├── __init__.py        — run_pygame() entry point
├── game_view.py       — GameView coordinator; popup callbacks; threading model
├── board_renderer.py  — BoardRenderer (vẽ 32 ô + token + dice + card overlay)
├── info_panel.py      — InfoPanel (cash, log, speed indicator)
└── speed_controller.py — SpeedController (pause/0.5x/1x/2x/5x/10x, dice barrier)
```

**Pattern kiến trúc:** MVC + EventBus + Strategy (mỗi loại ô là 1 Strategy class).

**Threading model (Phase 02.1.1):**
- **Background thread:** `SpeedController._run()` → `GameController.step()` → EventBus handlers (ghi `_ui_state`)
- **Main thread:** `pygame.event.get()` → render 60fps (đọc snapshot `_ui_state`)
- **Lock:** `threading.Lock` bảo vệ `_ui_state` — handlers giữ lock suốt; render lấy snapshot nhanh rồi thả
- **Dice barrier:** `SpeedController._dice_barrier` (threading.Event) — background thread wait, main thread set sau animation
- **Popup barrier:** `GameView._popup_event` (threading.Event) — game thread wait, main thread set sau click người chơi

---

*GDD này mô tả đúng code đang chạy tính đến Phase 02.1.1. Khi Phase 2.5+ hoàn thành, cần cập nhật mục 14 và 16.*
