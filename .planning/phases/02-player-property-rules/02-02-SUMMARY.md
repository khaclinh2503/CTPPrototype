---
phase: 02-player-property-rules
plan: "02"
subsystem: game-economics
tags: [acquisition, upgrade, minigame, fsm, integration]
dependency_graph:
  requires:
    - 02-01 (SpaceId fix, BASE_UNIT, TileStrategy with players param)
  provides:
    - Acquisition flow: forced buy from opponent (D-14, D-16)
    - Upgrade logic: stub always-upgrade if affordable (D-15)
    - MiniGame: 3-round do den, stub AI (D-09 to D-12)
    - FSM 7 phases including ACQUIRE and UPGRADE
  affects:
    - All integration tests (7-phase loop now required)
    - test_headless.py safety limit updated
tech_stack:
  added: []
  patterns:
    - TDD Red-Green approach for both tasks
    - Module-per-controller pattern (acquisition.py, upgrade.py)
    - Lazy import inside FSM methods to avoid circular deps
key_files:
  created:
    - ctp/controller/acquisition.py
    - ctp/controller/upgrade.py
    - tests/test_acquisition.py
    - tests/test_minigame.py
    - tests/test_game_loop.py
  modified:
    - ctp/tiles/game.py (stub -> full MiniGame)
    - ctp/controller/fsm.py (5 -> 7 phases, 3 new methods)
    - tests/test_fsm.py (updated transitions for 7-phase flow)
    - tests/test_headless.py (safety limit 50 -> 200)
decisions:
  - "Acquisition price formula: build_level1 * BASE_UNIT * acquireRate (per D-16)"
  - "FSM uses lazy import for acquisition/upgrade to avoid circular dependencies"
  - "test_headless.py safety limit updated from 50 to 200 to accommodate 7 phases"
  - "Board.json/Card.json copied to worktree for integration tests (ConfigLoader uses __file__ path)"
metrics:
  duration: "~30min"
  completed: "2026-04-02"
  tasks: 2
  files_changed: 9
---

# Phase 02 Plan 02: Property Acquisition, Upgrade, and MiniGame — Summary

**One-liner:** Forced acquisition with ownership transfer, stub upgrade always-upgrade, MiniGame 3-round bet-double, FSM expanded to 7 phases.

## What Was Built

### Task 1: Acquisition module, Upgrade module, MiniGame strategy

**`ctp/controller/acquisition.py`** — `resolve_acquisition()`:
- Chỉ xử lý CITY tiles của người khác, chưa max level (< 5)
- Giá mua = build_level1 * BASE_UNIT * acquire_rate (per D-16)
- Stub: luôn mua nếu đủ tiền (per D-14), owner không có quyền từ chối
- Transfer: A.cash -= price, B.receive(price), ownership transfer đầy đủ
- Emit `PROPERTY_ACQUIRED` event

**`ctp/controller/upgrade.py`** — `resolve_upgrades()`:
- Upgrade tất cả CITY properties của player theo thứ tự
- Stub: luôn upgrade nếu affordable và chưa max level 5 (per D-15)
- Cost = building[str(next_level)]["build"] * BASE_UNIT
- Emit `PROPERTY_UPGRADED` event mỗi lần upgrade

**`ctp/tiles/game.py`** — `GameStrategy.on_land()`:
- MiniGame 3-round đỏ đen (per D-09 to D-12)
- Bet = costOptions[0] * STARTING_CASH = 50_000
- Thắng: nhận bet * 2^round (round 1 = x2)
- Thua: mất bet
- Stub AI: luôn chọn min bet, dừng sau round 1 (per D-12)
- Emit `MINIGAME_RESULT` event

### Task 2: FSM extension, tests

**`ctp/controller/fsm.py`** — 7-phase FSM:
- `TurnPhase`: thêm `ACQUIRE = auto()` và `UPGRADE = auto()`
- Flow mới: ROLL -> MOVE -> RESOLVE_TILE -> ACQUIRE -> UPGRADE -> CHECK_BANKRUPTCY -> END_TURN
- `_do_resolve_tile()`: truyền `players=self.players` vào strategy (rent transfer hoạt động)
- `_do_acquire()`: gọi `resolve_acquisition()` với acquire_rate=1.0
- `_do_upgrade()`: gọi `resolve_upgrades()`
- `step()`: thêm cases cho ACQUIRE và UPGRADE

## Integration Test Results

Full game loop (4 players, 15 turns):
- 332 steps, winner declared
- 17 property purchases, 13 rent payments
- Players accumulate properties, cash flows via rent and acquisition

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_fsm.py for 7-phase FSM**
- **Found during:** Task 2 — existing test_fsm.py tested RESOLVE_TILE -> CHECK_BANKRUPTCY
- **Issue:** Old 5-phase tests broke after adding ACQUIRE and UPGRADE phases
- **Fix:** Updated 3 test methods: `test_step_resolve_to_check_bankruptcy` -> `test_step_resolve_to_acquire`, added `test_step_acquire_to_upgrade`, `test_step_upgrade_to_check_bankruptcy`, updated `test_full_turn_cycle` from 5 to 7 steps
- **Files modified:** `tests/test_fsm.py`
- **Commit:** f7dd268

**2. [Rule 1 - Bug] Updated test_headless.py safety limit**
- **Found during:** Task 2 integration — safety limit 50 too low for 7 phases
- **Issue:** Game with 5 turns * 2 players * 7 phases = 70 steps > 50 limit
- **Fix:** Updated safety limit from 50 to 200 with explanatory comment
- **Files modified:** `tests/test_headless.py`
- **Commit:** f7dd268

**3. [Rule 3 - Blocking] Copied Board.json/Card.json to worktree**
- **Found during:** Task 2 integration tests — ConfigLoader uses `__file__` path to find Board.json
- **Issue:** Worktree didn't have Board.json/Card.json, ConfigLoader raised ConfigError
- **Fix:** Copied files from main repo to worktree `ctp/config/`
- **Files modified:** `ctp/config/Board.json`, `ctp/config/Card.json`
- **Commit:** f7dd268

## Known Stubs

- `resolve_acquisition`: Stub "luôn mua nếu đủ tiền" — future plan sẽ thêm AI decision logic
- `resolve_upgrades`: Stub "luôn upgrade" — future plan sẽ thêm upgrade strategy
- `GameStrategy`: Stub AI "luôn chọn min bet, dừng sau R1" — future plan sẽ implement full 3-round strategy
- `_do_acquire` in fsm.py: `acquire_rate = 1.0` hardcoded, chưa đọc từ Board.json General.acquireRate

## Self-Check: PASSED

Files created:
- `/d/workspace/CTP/CTPPrototype/.claude/worktrees/agent-aa41bde0/ctp/controller/acquisition.py` — FOUND
- `/d/workspace/CTP/CTPPrototype/.claude/worktrees/agent-aa41bde0/ctp/controller/upgrade.py` — FOUND
- `/d/workspace/CTP/CTPPrototype/.claude/worktrees/agent-aa41bde0/tests/test_acquisition.py` — FOUND
- `/d/workspace/CTP/CTPPrototype/.clone/worktrees/agent-aa41bde0/tests/test_minigame.py` — FOUND
- `/d/workspace/CTP/CTPPrototype/.claude/worktrees/agent-aa41bde0/tests/test_game_loop.py` — FOUND

Commits verified:
- 3a73739 — test(02-02): RED tests acquisition/upgrade/minigame
- 0714620 — feat(02-02): acquisition, upgrade, MiniGame implementation
- bf861b4 — test(02-02): RED tests FSM phases/debt/full game loop
- f7dd268 — feat(02-02): FSM 7 phases, test_fsm.py updated, config files

All 186 tests pass.
