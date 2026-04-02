---
phase: 02-player-property-rules
plan: "01"
subsystem: core-foundation
tags: [spaceid-fix, constants, tile-stubs, rent-transfer, tax-fix, base-unit, tdd]
dependency_graph:
  requires: [01-03]
  provides: [SpaceId-enum-correct, BASE_UNIT-constants, rent-transfer, tax-fix, 3-tile-stubs]
  affects: [02-02, all-tile-strategies, bankruptcy-handler]
tech_stack:
  added: [ctp/core/constants.py]
  patterns: [BASE_UNIT-scaling, calc_invested_build_cost-helper, players-param-in-TileStrategy]
key_files:
  created:
    - ctp/core/constants.py
    - ctp/tiles/game.py
    - ctp/tiles/god.py
    - ctp/tiles/water_slide.py
    - tests/test_foundation_fix.py
  modified:
    - ctp/core/board.py
    - ctp/tiles/base.py
    - ctp/tiles/__init__.py
    - ctp/tiles/land.py
    - ctp/tiles/resort.py
    - ctp/tiles/tax.py
    - ctp/tiles/start.py
    - ctp/tiles/festival.py
    - ctp/tiles/fortune.py
    - ctp/tiles/prison.py
    - ctp/tiles/travel.py
    - ctp/controller/bankruptcy.py
    - ctp/core/events.py
    - ctp/config/game_rules.yaml
    - tests/test_tiles.py
    - tests/test_game_model.py
    - tests/test_config.py
decisions:
  - "SpaceId enum reordered to match Board.json semantics: FESTIVAL=1,CHANCE=2,CITY=3,GAME=4,PRISON=5,RESORT=6,START=7,TAX=8,TRAVEL=9,GOD=10,WATER_SLIDE=40"
  - "BASE_UNIT=1000 and STARTING_CASH=1_000_000 defined in constants.py as single source of truth"
  - "TileStrategy.on_land/on_pass accept players=None for rent transfer without breaking existing callers"
  - "Bankruptcy uses calc_invested_build_cost (invested levels only), not sum of all 5 level configs"
  - "Tax calculation: 10% of total invested property value, not percentage of player cash"
metrics:
  duration_seconds: 832
  completed_date: "2026-04-02"
  tasks_completed: 2
  files_modified: 17
requirements: [PROP-01, PROP-02]
---

# Phase 2 Plan 01: Foundation Fix + Constants Summary

**One-liner:** Fixed SpaceId enum mismatch with Board.json, established BASE_UNIT=1000 scaling, wired rent transfer to owner, fixed tax as 10% of invested property value, fixed start bonus as fixed 150k, and added 3 tile stubs (Game/God/WaterSlide).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix SpaceId enum, constants.py, 3 tile stubs, registry update | b272a2c | board.py, constants.py, base.py, __init__.py, game.py, god.py, water_slide.py, festival.py, fortune.py, prison.py, travel.py, game_rules.yaml, test_foundation_fix.py, test_tiles.py, test_game_model.py |
| 2 | Fix LandStrategy, ResortStrategy, TaxStrategy, StartStrategy, BankruptcyHandler, EventTypes | 0999b99 | land.py, resort.py, tax.py, start.py, bankruptcy.py, events.py, test_config.py |

## What Was Built

### SpaceId Enum Fix (Critical)
The Phase 1 `SpaceId` enum had wrong numeric mappings. All 11 values now match the actual Board.json `spaceId` integers:
- `FESTIVAL=1, CHANCE=2, CITY=3, GAME=4, PRISON=5, RESORT=6, START=7, TAX=8, TRAVEL=9, GOD=10, WATER_SLIDE=40`
- Old names (`LAND`, `FORTUNE_CARD`, `FORTUNE_EVENT`, `TAX=1` etc.) removed entirely

### Constants Module
New `ctp/core/constants.py`:
- `BASE_UNIT = 1_000` — multiplier for all config values (build costs, toll costs, initCost)
- `STARTING_CASH = 1_000_000` — single source of truth for game starting cash
- `calc_invested_build_cost(board, position)` — returns sum of build costs for levels 1..building_level, already scaled by BASE_UNIT

### Tile Strategy Updates
- `TileStrategy.on_land/on_pass` now accept `players: list | None = None`
- All 8 existing strategies updated with new param (no behavioral change for those not needing it)

### New Tile Stubs
- `GameStrategy` (spaceId=4): returns `[]` — mini-game mechanics deferred to Plan 02
- `GodStrategy` (spaceId=10): returns `[]` — Map 2/3, mechanics deferred post-Phase 4
- `WaterSlideStrategy` (spaceId=40): returns `[]` — Map 3 only, mechanics deferred post-Phase 4
- All three registered in TileRegistry

### Economic Fixes
- **LandStrategy**: price = `build_level_1 * BASE_UNIT`; rent = `toll * BASE_UNIT`; rent transfers to owner via `players` list
- **ResortStrategy**: price = `initCost * BASE_UNIT`; toll = `int(tollCost * rate^level) * BASE_UNIT`; rent transfers to owner
- **TaxStrategy**: tax = `0.1 * sum(calc_invested_build_cost for each property)` (not % of cash)
- **StartStrategy**: bonus = `STARTING_CASH * 0.15 = 150_000` fixed (not % of current cash)
- **BankruptcyHandler**: sell value = `calc_invested_build_cost * 0.5` (invested levels only), cheapest property first

### New EventTypes
`PROPERTY_ACQUIRED`, `PROPERTY_UPGRADED`, `MINIGAME_RESULT` added to `EventType` for Plan 02 use.

## Test Results

160 tests pass (0 failures):
- `tests/test_foundation_fix.py`: 45 tests (32 Task-1 + 13 Task-2), all green
- `tests/test_tiles.py`: 29 tests, all green (updated for new SpaceId names)
- `tests/test_game_model.py`: updated for new SpaceId enum values
- `tests/test_config.py`: updated starting_cash assertion from 200 to 1_000_000

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_config.py starting_cash assertion**
- **Found during:** Task 2 verification
- **Issue:** `test_config.py` asserted `starting_cash == 200` but game_rules.yaml was updated to 1_000_000
- **Fix:** Updated two test assertions to expect 1_000_000
- **Files modified:** tests/test_config.py
- **Commit:** 0999b99

**2. [Rule 1 - Bug] Updated test_game_model.py for new SpaceId values**
- **Found during:** Task 1 execution
- **Issue:** `test_game_model.py` tested old SpaceId values (`TAX==1`, `LAND==3`, etc.) and old Board position expectations
- **Fix:** Updated all SpaceId assertions and Board position assertions to reflect new enum
- **Files modified:** tests/test_game_model.py
- **Commit:** b272a2c

**3. [Rule 2 - Missing] Added players=None to all tile strategies**
- **Found during:** Task 1 execution
- **Issue:** Plan said to update base.py signature but also all concrete implementations needed updating (festival, fortune, prison, travel) to stay compatible with ABC
- **Fix:** Added `players: list | None = None` to all on_land/on_pass implementations
- **Files modified:** ctp/tiles/festival.py, fortune.py, prison.py, travel.py
- **Commit:** b272a2c

## Known Stubs

| File | Stub | Reason |
|------|------|--------|
| ctp/tiles/game.py | `on_land` returns `[]` | MiniGame mechanics (red/black 3-round betting) deferred to Plan 02 |
| ctp/tiles/god.py | `on_land` returns `[]` | GOD space mechanics not yet specified, deferred post-Phase 4 |
| ctp/tiles/water_slide.py | `on_land` returns `[]` | WATER_SLIDE mechanics not yet specified, Map 3 only, deferred post-Phase 4 |

These stubs are intentional per D-08 — GOD and WATER_SLIDE mechanics will be described later. GameStrategy will be implemented in Plan 02.

## Self-Check: PASSED

Files verified:
- ctp/core/board.py: `FESTIVAL = 1` ✓, `CITY = 3` ✓, `WATER_SLIDE = 40` ✓
- ctp/core/constants.py: `BASE_UNIT`, `STARTING_CASH`, `calc_invested_build_cost` ✓
- ctp/tiles/land.py: `owner.receive` ✓, `BASE_UNIT` ✓
- ctp/tiles/tax.py: `calc_invested_build_cost` ✓
- ctp/tiles/game.py: `class GameStrategy` ✓
- ctp/tiles/god.py: `class GodStrategy` ✓
- ctp/tiles/water_slide.py: `class WaterSlideStrategy` ✓
- ctp/tiles/__init__.py: `SpaceId.CITY` ✓, `SpaceId.CHANCE` ✓, `SpaceId.GAME` ✓
- ctp/config/game_rules.yaml: `starting_cash: 1000000` ✓

Commits verified:
- b272a2c ✓ (Task 1)
- 0999b99 ✓ (Task 2)

All 160 tests pass.
