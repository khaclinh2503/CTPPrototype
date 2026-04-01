# Phase 1: Headless Core - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Khởi tạo toàn bộ skeleton game chạy headless: project scaffold, config loader + Pydantic validation, game model dataclasses (Board/Tile/Player/EventBus), và GameController FSM với 7 loại tile strategy. Kết thúc phase: `python main.py --headless` chạy ván đấu 2-4 AI từ đầu đến terminal state (bankruptcy hoặc max_turns) mà không có exception.

**Không thuộc phase này:** Buff system (skill/pendant/pet), AI decision logic, property trading, Pygame visualization, card effect implementation.

</domain>

<decisions>
## Implementation Decisions

### Board & Tile Scope
- **D-01:** Board 32 ô, đọc layout từ `ctp/config/Board.json` (SpacePosition + LandSpace/ResortSpace/etc.)
- **D-02:** Phase 1 implement đúng 7 loại tile: **Land, Resort, Prison, Travel, Tax, Start, Festival** — mỗi loại có TileStrategy riêng
- **D-03:** FortuneSpace (ô cơ hội / event card) là **stub** trong Phase 1 — ghi nhận lượt draw nhưng không apply effect nào
- **D-04:** Card effects (EF_X codes từ Card.json) không implement trong Phase 1 — để Phase 3 xử lý

### Property Schema (Land & Resort)
- **D-05:** Land tile có **5 cấp nâng cấp** (building level 1→5), schema giữ nguyên format Board.json:
  ```json
  "building": {
    "1": {"build": 10, "toll": 1},
    "2": {"build": 5,  "toll": 3},
    "3": {"build": 15, "toll": 10},
    "4": {"build": 25, "toll": 28},
    "5": {"build": 25, "toll": 125}
  }
  ```
- **D-06:** Resort tile tách biệt với Land — dùng `ResortSpace` config (`initCost`, `tollCost`, `maxUpgrade: 3`, `increaseRate`)
- **D-07:** Pydantic schema validate cả Land và Resort khi load Board.json

### Config System
- **D-08:** Config files **dời vào trong package**: `ctp/config/Board.json`, `ctp/config/Card.json`
- **D-09:** Ngoài Board.json và Card.json đã có, Phase 1 tạo thêm: `ctp/config/skills.yaml`, `ctp/config/pendants.yaml`, `ctp/config/pets.yaml`, `ctp/config/game_rules.yaml` — chỉ cần schema skeleton, data thực điền ở Phase 2
- **D-10:** `ConfigLoader` class load tất cả files khi startup, raise `ConfigError` nếu schema sai — game không bao giờ khởi động với config lỗi
- **D-11:** `General` section trong Board.json cung cấp: `limitTurn` (max_turns = 25), `acquireRate`, `sellRate`, `winReward`

### Game Model
- **D-12:** `Player` skeleton trong Phase 1: chỉ có `player_id`, `cash`, `position`, `is_bankrupt`, `owned_properties` — không có buff slots (Phase 2)
- **D-13:** `GameEvent` / `EventBus` queue pattern — events publish/subscribe trong FSM
- **D-14:** Bankruptcy stub trong Phase 1: player có `cash < 0` → bán property theo thứ tự `sell_rate * build_cost` → nếu vẫn âm → mark `is_bankrupt = True`, loại khỏi game

### Game Controller FSM
- **D-15:** FSM states: `ROLL → MOVE → RESOLVE_TILE → CHECK_BANKRUPTCY → END_TURN`
- **D-16:** Dice roll: `2d6` standard
- **D-17:** `max_turns` đọc từ `General.limitTurn` (= 25), game kết thúc đúng ở turn đó

### Headless Runner Output
- **D-18:** `python main.py --headless` in **console log từng lượt**: player ID, dice result, tile landed, effect applied, cash change
- **D-19:** Cuối ván in summary: winner, total turns, final cash của từng player

### Project Layout
- **D-20:** Feature folders:
  ```
  ctp/
    config/        ← config files + ConfigLoader + Pydantic schemas
    core/          ← GameModel, Player, Board, Tile dataclasses, EventBus
    tiles/         ← TileStrategy base + 7 implementations
    controller/    ← GameController FSM
  main.py          ← entry point (--headless flag)
  tests/           ← headless test runner
  ```

### Claude's Discretion
- Tên cụ thể của Pydantic model classes (BoardSchema, LandTileSchema, v.v.)
- Internal EventBus implementation (simple list vs. deque)
- Test framework (pytest assumed)
- Logging format chi tiết của từng turn

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Config Data (đã có sẵn)
- `config/Board.json` — Board layout (SpacePosition), Land/Resort/Tax/Prison/Travel/Festival/Start space configs, General rules
- `config/Card.json` — Card definitions (IT_CA_1→IT_CA_29), effect codes, isActive flags, draw rates

### Planning
- `.planning/REQUIREMENTS.md` — CORE-01→05, CONF-01→06, TILE-01→06 (phase 1 requirements)
- `.planning/ROADMAP.md` — Phase 1 success criteria và plan breakdown (01-01, 01-02, 01-03)
- `.planning/STATE.md` — Architecture decisions: MVC+EventBus, Pydantic v2, Strategy pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Không có code hiện tại — greenfield project

### Established Patterns
- MVC + EventBus (từ STATE.md decisions)
- Pydantic v2 validation (fail-fast trước game loop)
- Strategy pattern cho tile types (không dùng if/else chain)

### Integration Points
- `main.py --headless` → `ConfigLoader` → `GameController` → `EventBus` → `TileStrategy`
- Phase 2 sẽ extend `Player` với buff slots
- Phase 3 sẽ replace decision stubs với `AIAgent`
- Phase 4 sẽ add Pygame layer lên trên `GameController`

</code_context>

<specifics>
## Specific Ideas

- Board.json có `tollMultiply` (nhân tiền thuê đặc biệt cho ô cụ thể) — planner cần handle trong Land TileStrategy
- `PrisonSpace.limitTurnByMapId` — số lượt ngồi tù phụ thuộc mapId, không phải hằng số
- `TravelSpace.travelCostRate` = 0.02 (phí 2% tài sản khi bị teleport)
- `FestivalSpace` có `holdCostRate`, `increaseRate`, `maxFestival` — cần track state lễ hội trên board
- `StartSpace.passingBonusRate` = 0.15 (thưởng 15% khi qua ô xuất phát)

</specifics>

<deferred>
## Deferred Ideas

- FortuneSpace card effects (EF_2 → EF_29) — Phase 3
- Buff/passive system (skill, pendant, pet) — Phase 2
- AI buy/sell/upgrade decisions — Phase 3
- Multi-map support (Board.json có SpacePosition0→7) — sau Phase 4
- `ResortSpace` mini-game logic (`MiniGame` config) — sau Phase 4

</deferred>

---

*Phase: 01-headless-core*
*Context gathered: 2026-04-01*
