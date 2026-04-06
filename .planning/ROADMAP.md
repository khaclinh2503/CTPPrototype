# Roadmap: CTPPrototype — Cờ Tỷ Phú AI Simulator

## Overview

Four phases deliver a fully playable, AI-driven Monopoly-style simulator. Phase 1
builds the headless game engine: board, tiles, config validation, and turn FSM — all
runnable without a screen. Phase 2 layers on players, the skill/pendant/pet passive
buff system, and all property/trading logic to produce a complete game loop. Phase 3
adds the AI decision engine (heuristic + Monte Carlo rollouts), personality
parameterization, and SQLite history persistence that feeds back into heuristic
weights. Phase 4 adds the Pygame visualization layer: board rendering from config,
player tokens, info panels, speed control, and end-game stats.

## Phases

- [x] **Phase 1: Headless Core** - Board, config loader, tile system, FSM turn engine — game runs headless
- [ ] **Phase 2: Property Rules** - Fix SpaceId, property acquisition/trading/mini game, complete game loop với stubs
- [ ] **Phase 2.5: Skill / Pendant / Pet System** - Trigger-based passive buff system (27 skills, 12 pendants, 4 pets), SkillEngine dispatch, FSM hook integration
- [ ] **Phase 3: AI Engine + History** - Heuristic agent, Monte Carlo rollouts, personality system, SQLite history persistence
- [ ] **Phase 4: Pygame Visualization** - Board rendering, player tokens, info panels, speed control, end-game stats

## Phase Details

### Phase 1: Headless Core
**Goal**: A complete, verifiable game skeleton runs headless — config loads and validates, all tile types resolve correctly, and a turn sequence progresses from start to a terminal state.
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06, TILE-01, TILE-02, TILE-03, TILE-04, TILE-05, TILE-06
**Success Criteria** (what must be TRUE):
  1. Running `python main.py --headless` starts a game with 2-4 AI players and terminates (by bankruptcy or `max_turns`) without unhandled exceptions
  2. All six tile types (property, jail/penalty, tax, travel, festival corner, event card) trigger their correct effects when a player lands on them
  3. Config files with schema errors are caught at startup and print a clear validation error before the game loop begins — bad config never reaches game logic
  4. A game run with `max_turns = 10` terminates at exactly turn 10 if no player has gone bankrupt
  5. A player whose cash goes below zero and cannot cover debts by selling assets is marked bankrupt and removed from the game
**Plans**: 3 plans (COMPLETE)

Plans:
- [x] 01-01-PLAN.md — Project scaffold, config loader, and Pydantic schema validation
- [x] 01-02-PLAN.md — GameModel dataclasses, Board/Tile objects, Player skeleton, EventBus
- [x] 01-03-PLAN.md — GameController FSM, TileStrategy implementations, bankruptcy, headless runner

### Phase 2: Property Rules
**Goal**: SpaceId enum được fix đúng, toàn bộ property/trading economics hoạt động chính xác — một ván đấu chạy từ đầu đến cuối cho ra kết quả kinh tế hợp lý với stubs AI mua/bán/nâng cấp.
**Depends on**: Phase 1
**Requirements**: PROP-01, PROP-02, PROP-03, PROP-04, PROP-05
**Success Criteria** (what must be TRUE):
  1. SpaceId enum fix đúng (FESTIVAL=1, CHANCE=2, CITY=3, GAME=4, PRISON=5, RESORT=6, START=7, TAX=8, TRAVEL=9) — tất cả tile strategies resolve đúng loại ô
  2. Một player dừng ở đất chưa có chủ và đủ tiền → tự động mua; dừng ở đất của đối thủ → trả toll đúng level, sau đó có thể mua (forced acquisition, chủ không có quyền từ chối)
  3. TaxSpace tính đúng: 10% × tổng build cost tất cả property đang sở hữu
  4. Khi không đủ tiền trả nợ → bán cả ô (stub: bán ô rẻ nhất trước) cho đến khi đủ hoặc phá sản
  5. Mini game 3 lượt đỏ đen hoạt động: lượt 1 bắt buộc cược min (50k), thắng ×2/×4/×8, player có thể dừng sau khi thắng
**Plans**: 2 plans

Plans:
- [x] 02-01: Fix SpaceId enum, update TileStrategy registry, fix rent transfer (owner nhận tiền), fix TaxSpace (10% × tổng nhà), update starting_cash=1,000,000, BASE_UNIT=1,000
- [x] 02-02: Acquisition flow (A mua đất B forced, toll trước → mua → upgrade stub), MiniGame 3-round đỏ đen, debt resolution (bán cả ô rẻ nhất trước), GodStrategy stub, WaterSlideStrategy stub

### Phase 02.1: Card Draw and Đổ Chính Xác (INSERTED)

**Goal:** FortuneStrategy đầy đủ 23 card effects hoạt động (weighted random, held/instant cards, toll modifiers) và cơ chế Đổ Chính Xác (căn lực) 15% base accuracy tích hợp vào FSM.
**Requirements**: CARD-01, CARD-02, CARD-03, CARD-04, CARD-05
**Depends on:** Phase 2
**Plans:** 4/4 plans complete

Plans:
- [x] 02.1-01-PLAN.md — Foundation: Player 4 new fields, 20 EventType constants, Board.map_id + find_nearest_tile_by_space_id()
- [x] 02.1-02-PLAN.md — Card Effects: FortuneStrategy full implementation (23 cards), toll modifiers in LandStrategy/ResortStrategy
- [x] 02.1-03-PLAN.md — Căn Lực + FSM Integration: _resolve_can_luc(), FSM ROLL/MOVE/END_TURN updates, dict key bug fix

### Phase 02.1.1: Minimal PygameUI (INSERTED)

**Goal:** Minimal Pygame window to observe the running game — diamond board with 32 rhombus tiles, player tokens, info panel (cash/total_assets), event log, speed control (Pause/1x/5x/Max), wired to existing EventBus and GameController.
**Requirements**: VIZ-01, VIZ-02, VIZ-04, VIZ-05
**Depends on:** Phase 2.1
**Plans:** 3/3 plans complete

Plans:
- [x] 02.1.1-01-PLAN.md — SpeedController background thread + ctp/ui package + requirements.txt (pygame>=2.6.1)
- [x] 02.1.1-02-PLAN.md — BoardRenderer (diamond geometry, tile rhombuses, player tokens) + InfoPanel (player info, event log, speed indicator)
- [x] 02.1.1-03-PLAN.md — GameView (EventBus subscriptions, shared state dict, render loop) + main.py Pygame branch integration

### Phase 2.5: Skill / Pendant / Pet System
**Goal**: Hệ thống trigger-based passive buff hoạt động hoàn chỉnh — mỗi player có bộ skill/pendant/pet ngẫu nhiên, SkillEngine dispatch tại 20+ hook points trong FSM, 27 skills + 12 pendants + 4 pets với procedural logic per GD spec.
**Depends on**: Phase 2
**Requirements**: PLAY-01, PLAY-02, PLAY-03, PLAY-04, PLAY-05, PLAY-06
**Success Criteria** (what must be TRUE):
  1. Mỗi AI player bắt đầu ván với bộ ngẫu nhiên (5 skills, 3 pendants, 1 pet) từ config pools
  2. SkillEngine.fire(trigger, player, ctx) dispatches đúng handler tại mỗi trigger point
  3. Rate calculation theo D-05: base_rate + (star - min_star) * chance, R dùng S config
  4. Pet stamina depletes khi active, stops at 0
**Plans**: 16 plans

Plans:
- [x] 02.5-01-PLAN.md — Foundation: Player/Board extensions, schema redesign, SkillEngine core, YAML configs, random assignment, unit tests
- [x] 02.5-02-PLAN.md — ROLL-trigger skills: SK_XXCT_1, SK_XE_DO, SK_MOONWALK, SK_XXCT_2 (4 skills)
- [x] 02.5-03-PLAN.md — MOVE-trigger skills: SK_CAM_CO, SK_PHA_HUY (2 skills)
- [x] 02.5-04-PLAN.md — RESOLVE_TILE toll/reactive skills: SK_BUA_SET, SK_NGOI_SAO, SK_CUONG_CHE (3 skills)
- [x] 02.5-05-PLAN.md — RESOLVE_TILE same-tile + travel skills: SK_SUNG_VANG, SK_LOC_XOAY, SK_TOC_CHIEN (3 skills)
- [x] 02.5-06-PLAN.md — Prison + landmark skills: SK_JOKER, SK_HQXX, SK_LAU_DAI_TINH_AI (3 skills)
- [x] 02.5-07-PLAN.md — UPGRADE-trigger skills: SK_TEDDY, SK_O_KY_DIEU, SK_MONG_NGUA (3 skills)
- [x] 02.5-08-PLAN.md — Hybrid upgrade+land skills: SK_AO_ANH, SK_BIEN_CAM (2 skills)
- [x] 02.5-09-PLAN.md — START-pass skills: SK_GRAMMY, SK_MU_PHEP (2 skills)
- [x] 02.5-10-PLAN.md — ACQUIRE-trigger skills: SK_MC2, SK_TRUM_DU_LICH (2 skills)
- [x] 02.5-11-PLAN.md — Multi-trigger complex skills: SK_GAY_NHU_Y, SK_HO_DIEP, SK_SO_10 (3 skills)
- [x] 02.5-12-PLAN.md — Pendants land/travel: PT_GIAY_BAY, PT_CUOP_NHA, PT_MANG_NHEN, PT_SIEU_TAXI (4 pendants)
- [x] 02.5-13-PLAN.md — Pendants own-land + opponent-land: PT_TU_TRUONG, PT_BAN_TAY_VANG, PT_TUI_BA_GANG, PT_KET_VANG (4 pendants)
- [x] 02.5-14-PLAN.md — Pendants special triggers: PT_DKXX2, PT_XICH_NGOC, PT_CHONG_MUA_NHA, PT_SIEU_SAO_CHEP (4 pendants)
- [x] 02.5-15-PLAN.md — All 4 pets: PET_THIEN_THAN, PET_XI_CHO, PET_PHU_THU, PET_TROI_CHAN
- [x] 02.5-16-PLAN.md — FSM hook injection (20+ trigger points), register_all.py, main.py wiring, integration tests

### Phase 3: AI Engine + History
**Goal**: Each AI player makes economically rational decisions driven by heuristic scoring and Monte Carlo rollouts, with personality affecting thresholds — and every completed game is persisted to SQLite for cross-session learning.
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, HIST-01, HIST-02, HIST-03, HIST-04
**Success Criteria** (what must be TRUE):
  1. An `aggressive` personality player buys more properties per game on average than a `conservative` personality player when running 50 simulated games — measurable from history
  2. Monte Carlo rollout (`n_rollouts = 200`) completes within 500 ms per decision on a standard laptop (model clone is Pygame-free)
  3. After 10 completed games, `history.db` contains a `turn_log` table with one row per turn, `outcome` filled for all rows of finished games, and a queryable win-rate per `tile_id` + `decision` pair
  4. AI heuristic weights for a tile type shift (increase or decrease) between game 1 and game 11 based on observed win-rate from history
  5. A CSV/JSON export of all history records can be produced by calling `HistoryManager.export(format="csv")`
**Plans**: 3 plans

Plans:
- [ ] 03-01: `AIAgent` base class, heuristic scoring functions (buy, upgrade, sell, jail timing) using `effective_stat()` for buff-adjusted thresholds, personality parameter loading from `agents.yaml` (aggressive / balanced / defensive)
- [ ] 03-02: Monte Carlo rollout engine — `game_model.clone()` (no Pygame state), `simulate_to_end()` headless fast loop, `monte_carlo_buy_eval()` integrated into buy/sell decision path
- [ ] 03-03: `HistoryManager` — SQLite schema (`turn_log` + indexes), write `TurnRecord` per turn, fill `outcome` at game end, win-rate query, heuristic weight adjustment loop, CSV/JSON export

### Phase 4: Pygame Visualization
**Goal**: The game is visually playable — the board renders correctly from config, player tokens move in real time, all info panels update live, and speed control lets the user observe or skip to results.
**Depends on**: Phase 3
**Requirements**: VIZ-01, VIZ-02, VIZ-03, VIZ-04, VIZ-05, VIZ-06
**Success Criteria** (what must be TRUE):
  1. Board tiles render at positions defined in `board.json` with correct labels; changing a tile's `pixel_x`/`pixel_y` in config moves it on screen without code changes
  2. Player tokens appear on the correct tile after each move and animate smoothly between positions at 1x speed
  3. The player info panel shows current cash, owned properties, and active skills/pet for each player, updating after every turn resolution
  4. The log panel displays the last action taken (e.g., "Player 2 bought Red District 3 for 400") and scrolls as new events arrive
  5. Speed control buttons (pause, step, 1x, 5x, 10x, max/headless) change simulation speed immediately; Space key pauses/resumes; Right arrow advances one event in step mode
  6. When the game ends, a stats screen displays the winner, final wealth of all players, total turns, and a per-player property count
**Plans**: 3 plans

Plans:
- [ ] 04-01: Pygame window setup, `AssetCache`, board surface rendering from config tile positions (Layer 0 static board, Layer 1 tile overlays for ownership/upgrade), `GameView` class with `headless` flag
- [ ] 04-02: Player token sprites (`LayeredDirty`), token movement lerp animation, `AnimationQueue` driven by `GameEvent` stream, player info panel (cash, properties, skills/pet), turn log panel
- [ ] 04-03: `SpeedController` / `SpeedWidget` (pause / step / 1x / 5x / 10x / max), keyboard shortcuts (Space, arrow keys, +/-), end-game stats screen with per-player summary

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 2.1 → 2.1.1 → 2.5 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Headless Core | 3/3 | Complete   | 2026-04-02 |
| 2. Player + Property Rules | 0/2 | Not started | - |
| 2.1. Card Draw + Căn Lực | 0/3 | Complete    | 2026-04-03 |
| 2.1.1. Minimal PygameUI | 0/3 | Not started | - |
| 2.5. Skill/Pendant/Pet | 0/16 | Planning complete | - |
| 3. AI Engine + History | 0/3 | Not started | - |
| 4. Pygame Visualization | 0/3 | Not started | - |
