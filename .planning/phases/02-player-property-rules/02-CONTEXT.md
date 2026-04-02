# Phase 2: Player + Property Rules - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 hoàn thiện toàn bộ kinh tế property/trading: fix SpaceId enum, implement buy/toll/acquisition/upgrade/debt flow đúng spec. Kết thúc phase: một ván đấu chạy từ đầu đến cuối cho ra kết quả kinh tế hợp lý.

**Không thuộc phase này:**
- Skill/Pendant/Pet passive buff system → chuyển sang Phase 2.5 (phase mới)
- AI decision logic thông minh (heuristic/Monte Carlo) → Phase 3
- Pygame visualization → Phase 4
- GOD space mechanics → mô tả sau
- WATER_SLIDE space mechanics → mô tả sau

</domain>

<decisions>
## Implementation Decisions

### SpaceId Enum Fix (CRITICAL — fix trước mọi thứ)
- **D-01:** SpaceId enum Phase 1 SAI — phải fix ngay đầu Phase 2:
  ```python
  FESTIVAL    = 1
  CHANCE      = 2   # Fortune/Event card (3 ô)
  CITY        = 3   # Land property (18 ô)
  GAME        = 4   # Mini game (1 ô)
  PRISON      = 5   # (1 ô)
  RESORT      = 6   # (5 ô)
  START       = 7   # (1 ô)
  TAX         = 8   # (1 ô)
  TRAVEL      = 9   # (1 ô)
  GOD         = 10  # Map 2 và Map 3 (mô tả sau)
  WATER_SLIDE = 40  # Map 3 only (mô tả sau)
  ```
- **D-02:** TileStrategy registry và tất cả tile implementations phải update theo SpaceId mới

### Scale tiền tệ
- **D-03:** `starting_cash = 1,000,000đ` (cập nhật game_rules.yaml từ 200 → 1,000,000)
- **D-04:** `BASE_UNIT = starting_cash / 1000 = 1,000đ` — mọi hệ số nguyên trong config (build, toll, initCost...) × 1,000 = giá thực
- **D-05:** Rate config (passingBonusRate, taxRate, escapeCostRate...) × starting_cash = giá thực
- **D-06:** TaxSpace: `tax = taxRate (0.1) × tổng giá trị nhà đang sở hữu` (không phải × starting_cash)

### Map System
- **D-07:** 3 map variants:
  - Map 1 (SpacePosition0): không có GOD, không có WATER_SLIDE
  - Map 2: có GOD (spaceId 10), không có WATER_SLIDE
  - Map 3: có WATER_SLIDE (spaceId 40), không có GOD
- **D-08:** GOD và WATER_SLIDE mechanics mô tả sau — Phase 2 chỉ cần đăng ký spaceId, stub on_land

### Mini Game (GAME tile — spaceId 4)
- **D-09:** Cơ chế đỏ đen 3 lượt:
  - Lượt 1 (bắt buộc): cược mức tối thiểu (costOptions[0] × 1,000,000 = 50,000đ)
  - Thắng → ×2 tiền cược. Thua → mất cược, kết thúc
  - Lượt 2/3 (tự chọn nếu thắng lượt trước): nhân ×4 rồi ×8
  - `maxChance: 3`, `increaseRate: 2`
- **D-10:** Người chơi có quyền dừng sau khi thắng
- **D-11:** Người chơi có thể đổi mức cược (3 mốc: 50k/100k/150k) giữa các lượt — hệ thống trừ tiền khi nâng mốc (trừ phần chênh lệch)
- **D-12:** Phase 2 stub: AI luôn chọn mức cược tối thiểu và dừng sau lượt 1 nếu thắng

### Property Flow (CITY tiles)
- **D-13:** Khi A dừng ở đất chưa có chủ → stub luôn mua nếu đủ tiền (Phase 3 AI thay)
- **D-14:** Khi A dừng ở đất của B:
  1. A trả toll cho B theo building level hiện tại
  2. Nếu đất chưa max level + A đủ tiền mua (`acquireRate × giá gốc`) → A tự quyết định mua (stub: luôn mua)
  3. **B không có quyền từ chối** — forced sale
  4. Sau khi mua, A có thể nâng cấp đất vừa mua (và bất kỳ đất nào đang sở hữu)
- **D-15:** Upgrade: stub luôn nâng cấp nếu đủ tiền và chưa max level — check sau mỗi lượt
- **D-16:** `acquireRate = 1.0` (config hiện tại) → giá mua = 100% giá build gốc của level hiện tại

### Debt Resolution
- **D-17:** Khi không đủ tiền trả: bán **cả ô** (không downgrade từng level)
- **D-18:** Thu về: `sellRate (0.5) × tổng build cost đã đầu tư vào ô đó`
- **D-19:** Thứ tự bán: stub bán ô có giá trị thấp nhất trước (giữ tài sản quý hơn)
- **D-20:** Tiếp tục bán cho đến khi đủ trả nợ hoặc hết tài sản → phá sản

### Buff Stat Vocabulary (dùng cho Phase 2.5 — ghi lại ở đây để Phase 2.5 researcher đọc)
- **D-21:** 10 stat keys đã xác định cho `effective_stat()`:
  ```
  toll_income_multiplier    # × tiền thuê nhận được      (default 1.0)
  toll_pay_multiplier       # × tiền thuê phải trả       (default 1.0)
  tax_rate_delta            # + thuế rate                (default 0.0)
  build_cost_multiplier     # × giá mua/xây đất          (default 1.0)
  resort_cost_multiplier    # × giá mua/toll resort      (default 1.0)
  passing_bonus_delta       # + thưởng qua Start rate    (default 0.0)
  prison_turns_delta        # + số lượt tù (âm=giảm)     (default 0)
  escape_cost_multiplier    # × phí thoát tù             (default 1.0)
  travel_cost_multiplier    # × phí ô travel             (default 1.0)
  minigame_cost_multiplier  # × phí cược mini game       (default 1.0)
  ```
- **D-22:** Stacking: cộng dồn tất cả stat_deltas từ skills + pendants + pet
  - Multiplier: `effective = default × (1 + Σ deltas)`, sàn tối thiểu 0.1
  - Delta: `effective = default + Σ deltas`

### Claude's Discretion
- Chi tiết implementation của rent recipient (owner nhận tiền trực tiếp từ event)
- Cách Phase 2 stub quyết định upgrade thứ tự ô nào trước
- Test fixtures cụ thể cho property flow

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Config Data
- `ctp/config/Board.json` — SpacePosition0 (map 1, 32 ô), LandSpace (19 land configs), ResortSpace, MiniGame, PrisonSpace, StartSpace, TaxSpace, TravelSpace, FestivalSpace, General (acquireRate=1.0, sellRate=0.5, limitTurn=25)
- `ctp/config/game_rules.yaml` — cần update starting_cash từ 200 → 1,000,000

### Existing Code (Phase 1)
- `ctp/core/board.py` — SpaceId enum (SAI, cần fix), Tile dataclass, Board class
- `ctp/core/models.py` — Player skeleton (cần thêm buff slots ở Phase 2.5, không phải Phase 2)
- `ctp/tiles/land.py` — LandStrategy hiện tại (auto-buy stub, rent chưa transfer cho owner)
- `ctp/controller/bankruptcy.py` — Bankruptcy logic Phase 1 (cần update debt resolution order)
- `ctp/controller/fsm.py` — FSM states (cần thêm ACQUIRE/UPGRADE states hoặc sub-steps)

### Planning
- `.planning/REQUIREMENTS.md` — PROP-01→05 (phase 2 requirements), PLAY-01→06 (phase 2.5)
- `.planning/ROADMAP.md` — Phase 2 success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LandStrategy.on_land()` — có sẵn skeleton mua đất + trả thuê, cần fix: rent transfer và acquisition flow
- `BankruptcyHandler` — có logic bán property, cần update: bán cả ô, chọn ô rẻ nhất trước
- `GameEvent` / `EventType` — cần thêm event types: PROPERTY_ACQUIRED, PROPERTY_UPGRADED, MINIGAME_RESULT

### Established Patterns
- Strategy pattern cho tile types — thêm GameStrategy (mini game), fix ResortStrategy, GodStrategy stub, WaterSlideStrategy stub
- EventBus publish/subscribe — dùng cho tất cả property transactions
- Pydantic v2 validation — schema MiniGame, GodSpace, BankSpace cần thêm nếu chưa có

### Integration Points
- `GameController.FSM` → sau RESOLVE_TILE cần check acquisition opportunity
- `Player.owned_properties` → cần thêm tracking building_level per property (hoặc dùng `Tile.building_level` trên Board)
- Rent transfer: hiện tại rent trừ từ payer nhưng chưa cộng vào owner — fix trong LandStrategy

</code_context>

<specifics>
## Specific Ideas

- `acquireRate = 1.0` nghĩa là A mua đất của B với **giá build cost của level 1** (giá gốc), không phải tổng đã đầu tư
- TaxSpace tính thuế trên **tổng giá trị nhà** = Σ(build costs đã bỏ ra cho tất cả properties đang sở hữu)
- Mini game: khi đổi mức cược từ 50k lên 100k → trừ **50k chênh lệch** (không phải trừ 100k)
- WATER_SLIDE và GOD: đăng ký SpaceId, tạo stub strategy `on_land` returns `[]` — implement sau

</specifics>

<deferred>
## Deferred Ideas

### Phase 2.5 (phase mới — thêm vào roadmap)
- PLAY-01 → PLAY-06: Skill/Pendant/Pet passive buff system
- Player slot system (5 skills, 3 pendants, 1 pet)
- `effective_stat()` với stacking logic
- Random assignment từ config pool khi game start
- Buff vocab đã định nghĩa ở D-21/D-22 — Phase 2.5 researcher đọc từ đây

### Sau Phase 4
- GOD space mechanics (turnLiftActive: 2) — Map 2 và Map 3
- WATER_SLIDE mechanics — Map 3 only
- Multi-map switching UI
- BankSpace mechanics (tollTaxRate: 10)

</deferred>

---

*Phase: 02-player-property-rules*
*Context gathered: 2026-04-02*
