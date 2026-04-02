---
phase: 02-player-property-rules
verified: 2026-04-02T00:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 02: Property Rules — Verification Report

**Phase Goal:** SpaceId enum được fix đúng, toàn bộ property/trading economics hoạt động chính xác — một ván đấu chạy từ đầu đến cuối cho ra kết quả kinh tế hợp lý với stubs AI mua/bán/nâng cấp.
**Verified:** 2026-04-02
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria + Plan must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SpaceId enum đúng: FESTIVAL=1, CHANCE=2, CITY=3, GAME=4, PRISON=5, RESORT=6, START=7, TAX=8, TRAVEL=9, GOD=10, WATER_SLIDE=40 — tất cả 32 tiles parse không lỗi | VERIFIED | `python -c "from ctp.core.board import SpaceId; assert SpaceId(1).name=='FESTIVAL'..."` passes; Board loads 32 tiles from Board.json |
| 2 | Player dừng ở đất chưa có chủ và đủ tiền → tự động mua; dừng ở đất đối thủ → trả toll, sau đó có thể mua forced (chủ không có quyền từ chối) | VERIFIED | `LandStrategy.on_land` auto-buys unowned; `resolve_acquisition` forces transfer; spot-check ownership transfer confirmed |
| 3 | Rent transfer cho owner — khi A trả toll thì B (owner) nhận đúng số tiền | VERIFIED | `owner.receive(rent)` present in `land.py:85`; spot-check A.cash -= 1000, B.cash += 1000 |
| 4 | TaxSpace tính thuế = 10% × tổng build cost của tất cả properties đang sở hữu | VERIFIED | `tax.py` uses `calc_invested_build_cost`; spot-check: 2 props at level 1 (build=10 each) → tax = 2000 |
| 5 | Scale tiền nhất quán — tất cả giá trị config nhân BASE_UNIT=1000, starting_cash=1,000,000 | VERIFIED | `constants.py`: `BASE_UNIT=1_000`, `STARTING_CASH=1_000_000`; `land.py`, `resort.py`, `upgrade.py` all use `BASE_UNIT` |
| 6 | MiniGame 3-round đỏ đen hoạt động: lượt 1 bắt buộc cược min (50k), thắng x2/x4/x8 | VERIFIED | `game.py` bet = `int(0.05 * 1_000_000) = 50_000`; multiplier = `increase_rate ** 1 = 2` (x2 round 1) |
| 7 | Khi không đủ tiền trả nợ → bán cả ô (rẻ nhất trước) cho đến khi đủ hoặc phá sản | VERIFIED | `bankruptcy.py:29` uses `min(..., key=lambda p: calc_invested_build_cost(...))` |
| 8 | FSM có ACQUIRE và UPGRADE phases sau RESOLVE_TILE | VERIFIED | `TurnPhase` = ROLL→MOVE→RESOLVE_TILE→ACQUIRE→UPGRADE→CHECK_BANKRUPTCY→END_TURN confirmed |
| 9 | Acquisition price = build cost level 1 × BASE_UNIT × acquireRate | VERIFIED | `acquisition.py:60`: `acquire_price = int(level_1_build * BASE_UNIT * acquire_rate)`; spot-check confirmed |
| 10 | Một ván đấu chạy từ đầu đến cuối không crash, có property purchases | VERIFIED | 4 players, max_turns=15: 262 steps, winner=p1, 12 purchases, 5 rents — no exceptions |

**Score:** 10/10 truths verified

---

### Required Artifacts

#### Plan 02-01 Artifacts

| Artifact | Provides | Status | Evidence |
|----------|----------|--------|----------|
| `ctp/core/board.py` | SpaceId enum với 11 members đúng giá trị | VERIFIED | FESTIVAL=1...WATER_SLIDE=40 confirmed; 135 lines |
| `ctp/core/constants.py` | BASE_UNIT=1000, STARTING_CASH=1_000_000, calc_invested_build_cost() | VERIFIED | All 3 exports present; 49 lines |
| `ctp/tiles/land.py` | LandStrategy với rent transfer cho owner, giá nhân BASE_UNIT | VERIFIED | `owner.receive` present; `BASE_UNIT` import confirmed |
| `ctp/tiles/tax.py` | TaxSpace tính thuế theo tổng giá trị nhà | VERIFIED | `calc_invested_build_cost` used in tax calculation |
| `ctp/tiles/game.py` | GameStrategy MiniGame 3-round đỏ đen | VERIFIED | Full implementation 97 lines; `increaseRate`, `STARTING_CASH`, `MINIGAME_RESULT` all present |
| `ctp/tiles/god.py` | GodStrategy stub | VERIFIED | `class GodStrategy` exists; returns `[]`; registered in TileRegistry |
| `ctp/tiles/water_slide.py` | WaterSlideStrategy stub | VERIFIED | `class WaterSlideStrategy` exists; returns `[]`; registered in TileRegistry |
| `tests/test_foundation_fix.py` | Tests cho SpaceId fix, rent transfer, tax fix, BASE_UNIT scaling | VERIFIED | 594 lines (min_lines=80 met) |

#### Plan 02-02 Artifacts

| Artifact | Provides | Status | Evidence |
|----------|----------|--------|----------|
| `ctp/controller/acquisition.py` | Acquisition flow: toll → forced buy → ownership transfer | VERIFIED | 90 lines; `resolve_acquisition` exported; `owner.receive`, `owner.remove_property` present |
| `ctp/controller/upgrade.py` | Upgrade logic: stub luôn upgrade nếu đủ tiền | VERIFIED | 63 lines; `resolve_upgrades` exported; `building_level >= 5` max check present |
| `ctp/tiles/game.py` | GameStrategy MiniGame (overwritten from stub) | VERIFIED | Full 3-round implementation; `increaseRate` present |
| `ctp/controller/fsm.py` | FSM với ACQUIRE và UPGRADE phases | VERIFIED | 7-phase FSM confirmed; `ACQUIRE = auto()`, `UPGRADE = auto()`, `_do_acquire`, `_do_upgrade` present |
| `tests/test_acquisition.py` | Tests cho acquisition flow | VERIFIED | 286 lines (min_lines=60 met) |
| `tests/test_minigame.py` | Tests cho MiniGame | VERIFIED | 162 lines (min_lines=40 met) |
| `tests/test_game_loop.py` | Integration test full game loop | VERIFIED | 347 lines |

---

### Key Link Verification

#### Plan 02-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ctp/tiles/land.py` | `ctp/core/constants.py` | `from ctp.core.constants import BASE_UNIT, calc_invested_build_cost` | WIRED | Pattern confirmed line 7 of land.py |
| `ctp/tiles/tax.py` | `ctp/core/constants.py` | `import calc_invested_build_cost` | WIRED | Pattern confirmed line 7 of tax.py |
| `ctp/tiles/__init__.py` | `ctp/core/board.py` | `SpaceId.CITY, SpaceId.CHANCE, SpaceId.GAME, SpaceId.GOD, SpaceId.WATER_SLIDE` | WIRED | TileRegistry resolves all 6 strategies at runtime |

#### Plan 02-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ctp/controller/fsm.py` | `ctp/controller/acquisition.py` | `import resolve_acquisition`, called in `_do_acquire()` | WIRED | Lazy import confirmed; `resolve_acquisition` called with correct args |
| `ctp/controller/fsm.py` | `ctp/controller/upgrade.py` | `import resolve_upgrades`, called in `_do_upgrade()` | WIRED | Lazy import confirmed; `resolve_upgrades` called |
| `ctp/controller/acquisition.py` | `ctp/core/constants.py` | `import BASE_UNIT` | WIRED | Line 5 of acquisition.py |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ctp/tiles/land.py` | `rent`, `price` | Board.json via `board.get_land_config()` → `building[level]["build/toll"] * BASE_UNIT` | Yes — reads real config JSON | FLOWING |
| `ctp/controller/acquisition.py` | `acquire_price` | `board.get_land_config(tile.opt)` → `building["1"]["build"] * BASE_UNIT * acquire_rate` | Yes — real config data | FLOWING |
| `ctp/tiles/tax.py` | `tax_amount` | `calc_invested_build_cost` per owned property — reads actual tile state + config | Yes — reflects actual game state | FLOWING |
| `ctp/controller/upgrade.py` | `upgrade_cost` | `board.get_land_config` → `building[next_level]["build"] * BASE_UNIT` | Yes — real config data | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SpaceId all 11 values correct | `python -c "assert SpaceId(40).name=='WATER_SLIDE'..."` | All 11 assertions pass | PASS |
| Board loads 32 tiles from Board.json | ConfigLoader + Board construction | `32 tiles` loaded | PASS |
| TileRegistry resolves all 6 strategies | `TileRegistry.resolve(sid)` for each | All 6 types resolve without error | PASS |
| Rent transfer A→B | LandStrategy.on_land with two players | A.cash -= 1000, B.cash += 1000 | PASS |
| Tax = 10% of invested build cost | TaxStrategy.on_land with 2 props | tax = 2000 (0.1 × 20000) | PASS |
| Acquisition ownership transfer | resolve_acquisition with CITY tile | tile.owner_id = A, cash transferred | PASS |
| MiniGame bet = 50k | costOptions[0] * STARTING_CASH | 50_000 | PASS |
| FSM 7 phases in correct order | `[p.name for p in TurnPhase]` | ROLL→MOVE→RESOLVE_TILE→ACQUIRE→UPGRADE→CHECK_BANKRUPTCY→END_TURN | PASS |
| Full game loop 4 players 15 turns | GameController.step() loop | 262 steps, winner=p1, 12 purchases, 5 rents | PASS |
| All 186 tests pass | `python -m pytest tests/ -x -q` | `186 passed in 0.41s` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROP-01 | 02-01 | Player dừng ở ô đất chưa có chủ → AI quyết định mua | SATISFIED | LandStrategy auto-buys unowned property when player has sufficient cash (stub = always buy if affordable) |
| PROP-02 | 02-01 | Player dừng ở đất đối thủ → trả tiền thuê theo cấp | SATISFIED | LandStrategy pays rent = toll × BASE_UNIT; rent transferred to owner via players list |
| PROP-03 | 02-02 | Property chưa max upgrade → player dừng có thể mua từ chủ theo acquisition price | SATISFIED | `resolve_acquisition` forces buy at build_level1 × BASE_UNIT × acquireRate when not max level |
| PROP-04 | 02-02 | AI quyết định có bán property hay không khi bị offer acquisition | SATISFIED | Stub implementation: owner cannot refuse (per D-14 spec); ownership transfer is forced |
| PROP-05 | 02-02 | Nâng cấp property: AI quyết định upgrade khi đủ tiền và điều kiện | SATISFIED | `resolve_upgrades` upgrades all CITY props when affordable and below level 5 |

**Notes on PROP-04:** The REQUIREMENTS.md description says "AI quyết định" but D-14 (domain spec) explicitly requires forced sale with no right of refusal. The plan's stub interpretation ("owner không có quyền từ chối") is consistent with Phase 2 scope. Full AI decision logic is deferred to Phase 3 (AI-01/AI-02).

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `ctp/controller/fsm.py:223` | `acquire_rate = 1.0` hardcoded, not read from Board.json `General.acquireRate` | Info | Minor — Board.json `acquireRate` is also 1.0, so values match. Acknowledged in SUMMARY as known deviation. |
| `ctp/tiles/god.py` | `on_land` returns `[]` stub | Info | Intentional — GOD tile mechanics not yet specified. Registered correctly in TileRegistry, does not crash. Deferred to post-Phase 4 per design. |
| `ctp/tiles/water_slide.py` | `on_land` returns `[]` stub | Info | Intentional — WATER_SLIDE is Map 3 only, mechanics not yet specified. Deferred to post-Phase 4 per design. |

No blocker anti-patterns found. The two tile stubs are by-design deferred implementations, not accidental placeholders.

---

### Human Verification Required

None — all phase-goal behaviors are verifiable programmatically via the headless game loop. No visual rendering, real-time behavior, or external service integration is involved in Phase 2.

---

### Gaps Summary

No gaps. All 10 observable truths verified, all 13 artifacts exist and are substantive, all 6 key links are wired, all 5 requirement IDs (PROP-01 through PROP-05) are satisfied. The full test suite passes (186 tests). The headless game loop runs to completion with real economic activity (purchases, rent, acquisition events).

The phase delivers on its stated goal: property economics work end-to-end in a deterministic headless game loop.

---

_Verified: 2026-04-02_
_Verifier: Claude (gsd-verifier)_
