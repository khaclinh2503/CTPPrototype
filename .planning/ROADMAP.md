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
- [ ] **Phase 2: Player + Property Rules** - Skill/Pendant/Pet passive buffs, property acquisition and trading, complete game loop
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

### Phase 2: Player + Property Rules
**Goal**: The passive buff system is fully operational and every property/trading decision resolves correctly — a game run from start to finish produces economically coherent outcomes.
**Depends on**: Phase 1
**Requirements**: PLAY-01, PLAY-02, PLAY-03, PLAY-04, PLAY-05, PLAY-06, PROP-01, PROP-02, PROP-03, PROP-04, PROP-05
**Success Criteria** (what must be TRUE):
  1. Each AI player starts a game with a randomly assigned set (5 skills, 3 pendants, 1 pet) drawn from config pools
  2. `player.effective_stat(stat)` returns the correct stacked value across all active skills, pendants, and pet — verified by unit test with known fixture data
  3. A player landing on an unowned property either purchases it (AI decision) or leaves it unowned; landing on an owned property pays rent at the correct upgrade level
  4. When a player is offered the acquisition price on an upgradeable property, the owning AI accepts or declines and the transaction resolves correctly
  5. AI can upgrade an owned property when it has sufficient funds and the tile is below max level
**Plans**: 2 plans

Plans:
- [ ] 02-01: Player slot system (5 skills / 3 pendants / 1 pet), StatDelta stacking, effective_stat(), random assignment from config pool on game start, buff floor/ceiling guards
- [ ] 02-02: Property ownership map on Board, rent calculation per upgrade level, buy/skip decision stub (returns True for now), acquisition offer flow, upgrade decision stub, debt resolution order (buildings → tiles → bankrupt)

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
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Headless Core | 3/3 | Complete   | 2026-04-02 |
| 2. Player + Property Rules | 0/2 | Not started | - |
| 3. AI Engine + History | 0/3 | Not started | - |
| 4. Pygame Visualization | 0/3 | Not started | - |