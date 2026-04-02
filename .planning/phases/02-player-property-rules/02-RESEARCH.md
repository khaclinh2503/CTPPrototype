# Phase 2: Property Rules - Research

**Researched:** 2026-04-02
**Domain:** Game economics — property purchase/toll/acquisition/upgrade/debt/minigame
**Confidence:** HIGH

## Summary

Phase 2 cần fix SpaceId enum (Phase 1 SAI giá trị), implement toàn bộ property/trading economics, và thêm MiniGame tile. Codebase Phase 1 đã có foundation tốt: Strategy pattern cho tiles, EventBus pub/sub, FSM turn engine, bankruptcy handler. Tuy nhiên có nhiều lỗ hổng cần fix: SpaceId enum values không khớp Board.json, rent không transfer cho owner, TaxSpace tính sai (% cash thay vì % tổng nhà), starting_cash sai (200 thay vì 1,000,000), thiếu acquisition flow, thiếu upgrade mechanism, thiếu MiniGame strategy.

Điểm quan trọng nhất: **SpaceId enum Phase 1 SAI hoàn toàn** — phải fix trước mọi thứ khác vì Board.json parse dùng `SpaceId(entry["spaceId"])` trực tiếp. Nếu không fix, tất cả tile resolution sẽ sai loại.

**Primary recommendation:** Chia thành 2 plans: (1) Fix foundation (SpaceId, scale tiền, rent transfer, TaxSpace) và (2) Thêm features mới (acquisition, upgrade, MiniGame, debt resolution cải tiến, GOD/WATER_SLIDE stubs).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: SpaceId enum fix: FESTIVAL=1, CHANCE=2, CITY=3, GAME=4, PRISON=5, RESORT=6, START=7, TAX=8, TRAVEL=9, GOD=10, WATER_SLIDE=40
- D-02: TileStrategy registry va tat ca tile implementations phai update theo SpaceId moi
- D-03: starting_cash = 1,000,000d (update game_rules.yaml tu 200 -> 1,000,000)
- D-04: BASE_UNIT = starting_cash / 1000 = 1,000d — moi he so nguyen trong config x 1,000 = gia thuc
- D-05: Rate config (passingBonusRate, taxRate, escapeCostRate...) x starting_cash = gia thuc
- D-06: TaxSpace: tax = taxRate (0.1) x tong gia tri nha dang so huu (khong phai x starting_cash)
- D-07: 3 map variants (Map 1 = SpacePosition0, Map 2 co GOD, Map 3 co WATER_SLIDE)
- D-08: GOD va WATER_SLIDE Phase 2 chi can dang ky spaceId, stub on_land
- D-09: MiniGame 3 luot do den, luot 1 bat buoc cuoc min (50k), thang x2/x4/x8
- D-10: Nguoi choi co quyen dung sau khi thang
- D-11: Nguoi choi co the doi muc cuoc (3 moc: 50k/100k/150k) giua cac luot
- D-12: Phase 2 stub: AI luon chon muc cuoc toi thieu va dung sau luot 1 neu thang
- D-13: Dat chua co chu -> stub luon mua neu du tien
- D-14: Dat cua doi thu -> tra toll, neu chua max + du tien mua -> A tu quyet dinh mua (stub: luon mua), B khong co quyen tu choi (forced sale), sau mua co the nang cap
- D-15: Upgrade: stub luon nang cap neu du tien va chua max level
- D-16: acquireRate = 1.0 -> gia mua = 100% gia build goc cua level hien tai
- D-17: Khi khong du tien tra: ban CA O (khong downgrade tung level)
- D-18: Thu ve: sellRate (0.5) x tong build cost da dau tu vao o do
- D-19: Thu tu ban: stub ban o co gia tri thap nhat truoc
- D-20: Tiep tuc ban cho den khi du tra no hoac het tai san -> pha san

### Claude's Discretion
- Chi tiet implementation cua rent recipient (owner nhan tien truc tiep tu event)
- Cach Phase 2 stub quyet dinh upgrade thu tu o nao truoc
- Test fixtures cu the cho property flow

### Deferred Ideas (OUT OF SCOPE)
- PLAY-01 -> PLAY-06: Skill/Pendant/Pet passive buff system (Phase 2.5)
- GOD space mechanics (turnLiftActive: 2) — Map 2 va Map 3 (sau Phase 4)
- WATER_SLIDE mechanics — Map 3 only (sau Phase 4)
- BankSpace mechanics (tollTaxRate: 10) (sau Phase 4)
- D-21/D-22: Buff stat vocabulary va stacking logic (Phase 2.5)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROP-01 | Nguoi choi dung o dat chua co chu -> AI quyet dinh mua hay bo qua | LandStrategy.on_land() da co skeleton auto-buy; can apply BASE_UNIT scaling cho price, stub luon mua (D-13) |
| PROP-02 | Nguoi choi dung o dat doi thu -> tra tien thue theo cap hien tai | LandStrategy rent logic ton tai nhung KHONG transfer tien cho owner (line 81: `pass`); can fix |
| PROP-03 | Neu property chua max upgrade -> nguoi dung co the mua tu chu theo gia config | Chua co acquisition flow; can them sub-step sau RESOLVE_TILE trong FSM; acquireRate=1.0 tu General config |
| PROP-04 | AI quyet dinh co ban property hay khong khi bi offer gia acquisition | D-14: forced sale, B khong co quyen tu choi -> khong can AI decision, don gian hoa |
| PROP-05 | Nang cap property: AI quyet dinh upgrade khi du tien va dieu kien | Can them upgrade step sau acquisition; stub luon upgrade (D-15); building levels 1-5 tu LandSpace config |
</phase_requirements>

## Architecture Patterns

### Hien trang code Phase 1 - Cac van de can fix

#### 1. SpaceId Enum SAI (CRITICAL)

File `ctp/core/board.py` line 8-21 — **Tat ca values sai**:
```python
# HIEN TAI (SAI):
TAX = 1, FORTUNE_CARD = 2, LAND = 3, PRISON = 4, FESTIVAL = 5,
FORTUNE_EVENT = 6, START = 7, TRAVEL = 8, RESORT = 9

# CAN FIX THANH:
FESTIVAL = 1, CHANCE = 2, CITY = 3, GAME = 4, PRISON = 5,
RESORT = 6, START = 7, TAX = 8, TRAVEL = 9, GOD = 10, WATER_SLIDE = 40
```

**Impact:** Board.json SpacePosition0 dung gia tri so truc tiep (`SpaceId(entry["spaceId"])`). Hien tai:
- Position 17 co spaceId=1 trong JSON -> Phase 1 map thanh TAX (DUNG tinh co) nhung thuc ra la FESTIVAL
- Position 3 co spaceId=4 -> Phase 1 map thanh PRISON nhung that ra la GAME (MiniGame)
- Position 9 co spaceId=5 -> Phase 1 map thanh FESTIVAL nhung that ra la PRISON

**Ket qua:** Khi fix SpaceId, PHAI rename members + update tat ca references (TileRegistry, tile __init__.py, tests, bankruptcy.py).

#### 2. Rent KHONG Transfer Cho Owner

File `ctp/tiles/land.py` line 81-82:
```python
for p in board.board:  # This won't work - need to pass players
    pass  # Simplified - rent goes to "bank" for now in events
```

**Fix:** TileStrategy.on_land() hien tai KHONG co access den player list. Can truyen `players: list[Player]` hoac dung EventBus de owner nhan tien. **Recommendation:** Truyen `game_context` dict chua players list vao strategy, hoac dung event subscriber pattern (owner subscribes to RENT_PAID events).

#### 3. TaxSpace Tinh SAI

File `ctp/tiles/tax.py` line 34:
```python
tax_amount = int(player.cash * tax_rate)  # SAI: nhan voi cash
```

**Fix:** Tax = taxRate (0.1) x tong build cost tat ca property dang so huu. Can iterate player.owned_properties, tinh tong build cost cho tung o.

#### 4. Scale Tien

`game_rules.yaml` co `starting_cash: 200` -> can update thanh `1,000,000`. Moi gia tri `build`/`toll`/`initCost` trong Board.json la he so nguyen, nhan voi `BASE_UNIT = 1,000` de ra gia thuc.

**Vi du:** Land 1 level 1: `build: 10` -> gia thuc = 10 x 1,000 = 10,000d

#### 5. Bankruptcy Handler Tinh SAI total_build_cost

File `ctp/controller/bankruptcy.py` line 84:
```python
return sum(b.get("build", 0) for b in building.values())  # Tinh TONG TAT CA levels
```

**Van de:** Hien tai tinh tong build cost cua TAT CA 5 levels (ke ca chua xay). Can chi tinh tong build cost cua cac level DA XAY (1 den building_level hien tai).

### FSM Flow Can Mo Rong

Hien tai FSM: `ROLL -> MOVE -> RESOLVE_TILE -> CHECK_BANKRUPTCY -> END_TURN`

Phase 2 can them sub-steps sau RESOLVE_TILE:

```
ROLL -> MOVE -> RESOLVE_TILE -> ACQUIRE_DECISION -> UPGRADE_DECISION -> CHECK_BANKRUPTCY -> END_TURN
```

**Option 1 (Recommended):** Them TurnPhase states `ACQUIRE` va `UPGRADE` vao FSM.
**Option 2:** Xu ly acquisition/upgrade ngay trong RESOLVE_TILE (don gian hon nhung kho mo rong).

### Recommended Approach: Players Accessible to Strategies

Hien tai `TileStrategy.on_land()` signature:
```python
def on_land(self, player: Player, tile: Tile, board: Board, event_bus) -> list[GameEvent]
```

Can them `players: list[Player]` hoac mot `GameContext` object de strategies co the:
- Transfer rent cho owner (PROP-02)
- Check debt/bankruptcy inline

**Recommendation:** Them `players` param vao on_land/on_pass. Tuy break API cua tat ca strategies nhung la cach don gian nhat. Alternative: GameContext dataclass.

### Recommended Project Structure Changes

```
ctp/
  tiles/
    game.py            # NEW: GameStrategy (MiniGame do den)
    god.py             # NEW: GodStrategy stub
    water_slide.py     # NEW: WaterSlideStrategy stub
  config/
    schemas.py         # UPDATE: them MiniGameConfig schema
    game_rules.yaml    # UPDATE: starting_cash = 1000000
  core/
    board.py           # UPDATE: SpaceId enum fix
    constants.py       # NEW (optional): BASE_UNIT = 1000
    models.py          # MINOR: co the them helper methods
  controller/
    fsm.py             # UPDATE: them ACQUIRE/UPGRADE phases
    bankruptcy.py      # UPDATE: fix total_build_cost, debt resolution order
```

### Pattern: Scale Tien Nhat Quan

Moi cho tinh tien PHAI nhan config value voi BASE_UNIT (1,000):
```python
BASE_UNIT = 1_000  # starting_cash / 1000

# Land price
actual_price = land_config["building"]["1"]["build"] * BASE_UNIT
# -> 10 * 1000 = 10,000d

# Resort initCost
actual_resort_cost = resort_config["initCost"] * BASE_UNIT
# -> 50 * 1000 = 50,000d

# Rate-based calculations dung starting_cash
passing_bonus = starting_cash * passingBonusRate
# -> 1,000,000 * 0.15 = 150,000d

# Tax (SPECIAL): taxRate * tong gia tri nha
tax = taxRate * sum_of_all_owned_build_costs
```

### Pattern: Acquisition Flow

```python
# Sau khi A tra toll cho B:
if tile.building_level < max_level:
    acquire_price = land_config["building"]["1"]["build"] * BASE_UNIT * acquireRate
    if player.can_afford(acquire_price):
        # Stub: luon mua
        player.pay(acquire_price)
        old_owner.receive(acquire_price)  # B nhan tien
        tile.owner_id = player.player_id
        player.add_property(tile.position)
        old_owner.remove_property(tile.position)
```

### Pattern: MiniGame 3-Round Do Den

```python
# Round 1: bat buoc cuoc min (costOptions[0] * starting_cash = 50k)
# Win (50%): x2, co the tiep tuc hoac dung
# Round 2 (neu thang R1): x4 tong
# Round 3 (neu thang R2): x8 tong
# Thua bat ky round nao: mat cuoc, ket thuc

# Doi muc cuoc giua cac round:
# costOptions = [0.05, 0.1, 0.15] * starting_cash = [50k, 100k, 150k]
# Khi doi tu 50k len 100k: tru them 50k (chenh lech)
```

### Anti-Patterns to Avoid
- **Khong hardcode SpaceId values:** Luon dung `SpaceId.CITY` thay vi `SpaceId(3)` — except khi parse Board.json
- **Khong tinh tien trong tiles ma khong nhan BASE_UNIT:** Tat ca config values la he so, phai scale
- **Khong break TileStrategy interface qua nhieu:** Them 1 param (`players`) thay vi thay doi signature hoan toan
- **Khong mix Phase 2.5 logic:** Khong add buff/effective_stat vao Phase 2 — su dung gia tri config truc tiep

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Random win/lose MiniGame | Custom random logic | `random.random() < 0.5` | Standard Python random, don gian |
| Config validation | Manual checks | Pydantic v2 `MiniGameConfig` schema | Da co pattern tu Phase 1, nhat quan |
| Event dispatch | Manual callback lists | EventBus (da co) | Da implement, tested |
| Property value calculation | Inline math moi cho | Helper function `calc_build_cost(board, position, up_to_level)` | Dung o nhieu noi: tax, debt, sell, display |

## Common Pitfalls

### Pitfall 1: SpaceId Rename Khong Dong Bo
**What goes wrong:** Rename SpaceId members nhung quen update references trong tests, registry, bankruptcy handler
**Why it happens:** SpaceId.LAND -> SpaceId.CITY, SpaceId.FORTUNE_CARD -> SpaceId.CHANCE, etc. — nhieu cho reference
**How to avoid:** Grep toan bo project cho moi SpaceId member cu truoc khi rename. Danh sach day du:
- `SpaceId.TAX` (1->8), `SpaceId.FORTUNE_CARD` (2->CHANCE), `SpaceId.LAND` (3->CITY)
- `SpaceId.PRISON` (4->5), `SpaceId.FESTIVAL` (5->1), `SpaceId.FORTUNE_EVENT` (6->removed, merge vao CHANCE)
- `SpaceId.START` (7->7 KHONG DOI), `SpaceId.TRAVEL` (8->9), `SpaceId.RESORT` (9->6)
**Warning signs:** `ValueError: X is not a valid SpaceId` khi load Board.json

### Pitfall 2: BASE_UNIT Ap Dung Khong Nhat Quan
**What goes wrong:** Mot so cho nhan BASE_UNIT, mot so cho khong -> kinh te game bi lech
**Why it happens:** Config co 2 loai values: integer coefficients (build, toll, initCost) va rates (taxRate, passingBonusRate)
**How to avoid:** Quy tac ro rang:
- Integer config values (build, toll, initCost): `value * BASE_UNIT`
- Rate config values (taxRate, passingBonusRate): `rate * starting_cash` hoac `rate * base_value`
- costOptions trong MiniGame: `value * starting_cash` (0.05 * 1M = 50k)
**Warning signs:** Player cash tang/giam bat thuong (qua nhieu hoac qua it)

### Pitfall 3: Debt Resolution Khong Kiem Tra Resort
**What goes wrong:** Bankruptcy handler chi tinh Land tiles, quen Resort tiles
**Why it happens:** `_total_build_cost()` da handle Resort nhung dung `initCost` raw (chua x BASE_UNIT)
**How to avoid:** Moi property type (CITY + RESORT) deu phai co logic tinh gia tri nhat quan voi BASE_UNIT

### Pitfall 4: Acquisition Khong Clean Up Old Owner
**What goes wrong:** Player A mua dat cua B nhung quen remove tu B.owned_properties
**Why it happens:** Acquisition la flow moi, khong co trong Phase 1
**How to avoid:** Checklist: (1) A pay, (2) B receive, (3) tile.owner_id = A, (4) A.add_property, (5) B.remove_property, (6) event publish

### Pitfall 5: MiniGame Negative Cash
**What goes wrong:** Player thua MiniGame roi khong du tien tra rent/tax tiep theo
**Why it happens:** MiniGame tru tien cuoc truoc khi biet ket qua
**How to avoid:** MiniGame bet chi tru khi bat dau round. Neu thua -> tien da mat. Sau MiniGame, FSM tiep tuc binh thuong (CHECK_BANKRUPTCY se handle)

### Pitfall 6: Passing Start Bonus Tinh Sai Scale
**What goes wrong:** Passing bonus = 15% * cash (current) thay vi 15% * starting_cash
**Why it happens:** Phase 1 `start.py` line 53: `bonus = int(player.cash * bonus_rate)` — dung % cash hien tai
**How to avoid:** Fix: `bonus = int(starting_cash * bonus_rate)` = 150,000d co dinh. Hoac theo D-05: `passingBonusRate * starting_cash`.

## Code Examples

### SpaceId Enum Fix
```python
# ctp/core/board.py
class SpaceId(IntEnum):
    FESTIVAL    = 1
    CHANCE      = 2   # Was FORTUNE_CARD=2 + FORTUNE_EVENT=6
    CITY        = 3   # Was LAND=3
    GAME        = 4   # NEW: MiniGame tile
    PRISON      = 5   # Was PRISON=4
    RESORT      = 6   # Was RESORT=9
    START       = 7   # UNCHANGED
    TAX         = 8   # Was TAX=1
    TRAVEL      = 9   # Was TRAVEL=8
    GOD         = 10  # NEW: stub
    WATER_SLIDE = 40  # NEW: stub
```

### TileRegistry Update
```python
# ctp/tiles/__init__.py
from ctp.tiles.game import GameStrategy
from ctp.tiles.god import GodStrategy
from ctp.tiles.water_slide import WaterSlideStrategy

TileRegistry.register(SpaceId.CITY, LandStrategy())       # Was SpaceId.LAND
TileRegistry.register(SpaceId.RESORT, ResortStrategy())
TileRegistry.register(SpaceId.PRISON, PrisonStrategy())
TileRegistry.register(SpaceId.TRAVEL, TravelStrategy())
TileRegistry.register(SpaceId.TAX, TaxStrategy())
TileRegistry.register(SpaceId.START, StartStrategy())
TileRegistry.register(SpaceId.FESTIVAL, FestivalStrategy())
TileRegistry.register(SpaceId.CHANCE, FortuneStrategy())   # Was FORTUNE_CARD + FORTUNE_EVENT
TileRegistry.register(SpaceId.GAME, GameStrategy())        # NEW
TileRegistry.register(SpaceId.GOD, GodStrategy())          # NEW stub
TileRegistry.register(SpaceId.WATER_SLIDE, WaterSlideStrategy())  # NEW stub
```

### TaxSpace Fix
```python
# ctp/tiles/tax.py
def on_land(self, player, tile, board, event_bus, players=None):
    tax_rate = 0.1  # from TaxSpace config
    # Tinh tong build cost tat ca property dang so huu
    total_property_value = 0
    for pos in player.owned_properties:
        total_property_value += calc_invested_build_cost(board, pos)
    tax_amount = int(tax_rate * total_property_value)
    # ...
```

### Helper: Calc Invested Build Cost
```python
def calc_invested_build_cost(board: Board, position: int) -> int:
    """Tinh tong build cost DA DAU TU (level 1 den building_level hien tai)."""
    tile = board.get_tile(position)
    if tile.space_id == SpaceId.CITY:
        config = board.get_land_config(tile.opt)
        if not config:
            return 0
        building = config.get("building", {})
        total = 0
        for lvl in range(1, tile.building_level + 1):
            level_data = building.get(str(lvl), {})
            total += level_data.get("build", 0)
        return total * BASE_UNIT
    elif tile.space_id == SpaceId.RESORT:
        resort_config = board.get_resort_config()
        if not resort_config:
            return 0
        return resort_config.get("initCost", 0) * BASE_UNIT
    return 0
```

### MiniGame Strategy
```python
# ctp/tiles/game.py
class GameStrategy(TileStrategy):
    def on_land(self, player, tile, board, event_bus, players=None):
        events = []
        starting_cash = 1_000_000
        cost_options = [0.05, 0.1, 0.15]  # from MiniGame config
        max_chance = 3
        increase_rate = 2

        current_bet_index = 0  # Stub: luon chon muc min
        current_bet = int(cost_options[current_bet_index] * starting_cash)  # 50,000

        # Round 1 (bat buoc)
        player.pay(current_bet)
        winnings = current_bet
        if random.random() < 0.5:  # Win
            winnings *= increase_rate  # x2
            player.receive(winnings)
            # Stub: dung sau round 1
        else:
            # Thua, mat cuoc
            pass
        return events
```

### Debt Resolution Fix
```python
# Sell whole tile, cheapest first, calculate by invested cost
while player.cash < 0 and player.owned_properties:
    prop_pos = min(
        player.owned_properties,
        key=lambda p: calc_invested_build_cost(board, p)
    )
    tile = board.get_tile(prop_pos)
    invested = calc_invested_build_cost(board, prop_pos)
    sell_value = invested * sell_rate  # 0.5

    player.cash += sell_value
    player.remove_property(prop_pos)
    tile.owner_id = None
    tile.building_level = 0
```

## State of the Art

| Old Approach (Phase 1) | Current Approach (Phase 2) | Impact |
|------------------------|---------------------------|--------|
| SpaceId values sai | Fix enum theo Board.json spec | Tat ca tile resolution dung |
| starting_cash = 200 | starting_cash = 1,000,000 | Kinh te game thuc te |
| Rent khong transfer | Rent transfer cho owner | PROP-02 works |
| Tax = 10% cash | Tax = 10% tong gia tri nha | D-06 dung spec |
| Bankruptcy: bao gom tat ca levels | Bankruptcy: chi invested levels | Gia tri ban chinh xac |
| No acquisition | Forced acquisition flow | PROP-03/04 works |
| No MiniGame | 3-round do den | Success criteria 5 |

## Open Questions

1. **TileStrategy signature change**
   - What we know: Hien tai on_land() khong co access den players list, can cho rent transfer va acquisition
   - What's unclear: Nen them `players` param hay dung `GameContext` object?
   - Recommendation: Them `players: list[Player] | None = None` default param de backward compatible. Don gian, khong can tao class moi.

2. **FORTUNE_EVENT merge vao CHANCE**
   - What we know: Phase 1 co 2 SpaceId cho Fortune (FORTUNE_CARD=2 va FORTUNE_EVENT=6). Phase 2 chi co CHANCE=2
   - What's unclear: Board.json SpacePosition0 khong co spaceId=6, chi co spaceId=2 (3 o). Kiem tra xac nhan: SpacePosition0 khong co `opt=101/102` cho fortune.
   - Recommendation: Xoa FORTUNE_EVENT, chi giu CHANCE=2 map den FortuneStrategy. SpacePosition0 chi co 3 o voi spaceId=2.

3. **Resort opt values 101/102**
   - What we know: Resort tiles trong SpacePosition0 co opt=101 hoac opt=102 (khong phai 1,2,3...)
   - What's unclear: Y nghia cua opt cho resort? Phase 1 khong dung opt cho resort.
   - Recommendation: Giu nguyen, resort khong can opt de resolve (dung chung config ResortSpace).

## Sources

### Primary (HIGH confidence)
- `ctp/config/Board.json` — SpacePosition0 co 9 loai spaceId (1-9), distribution: 1x1, 3x2, 18x3, 1x4, 1x5, 5x6, 1x7, 1x8, 1x9
- `ctp/config/Board.json` — MiniGame config: maxChance=3, costOptions=[0.05, 0.1, 0.15], increaseRate=2
- `ctp/config/Board.json` — General: acquireRate=1, sellRate=0.5
- `ctp/config/Board.json` — LandSpace["1"]["1"]: building levels 1-5 voi build/toll values
- `ctp/core/board.py` — SpaceId enum hien tai (PHAI FIX)
- `ctp/tiles/land.py` — Rent transfer comment line 81: "This won't work"
- `ctp/tiles/tax.py` — Tax tinh sai: `player.cash * tax_rate`
- `02-CONTEXT.md` — 22 locked decisions (D-01 to D-22)

### Secondary (MEDIUM confidence)
- Code pattern analysis tu Phase 1 tiles — Strategy pattern, EventBus usage nhat quan

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Khong co external libraries moi, chi dung Python stdlib + existing codebase
- Architecture: HIGH - Patterns da establish tu Phase 1, chi mo rong
- Pitfalls: HIGH - Da doc truc tiep source code va xac dinh cac loi cu the (line numbers)

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable — internal codebase, khong co external dependencies thay doi)
