---
phase: 01-headless-core
plan: 03
subsystem: tiles, controller, headless
tags: [tiles, fsm, strategy-pattern, headless]
dependency_graph:
  requires:
    - 01-01 (config loader and schemas)
    - 01-02 (game model: board, player, events)
  provides:
    - TileStrategy pattern with 7 tile types
    - GameController FSM with turn phases
    - Headless runner via main.py
  affects:
    - Phase 2 (AI decision logic will extend strategies)
    - Phase 4 (visualization will wrap GameController)
tech_stack:
  added: []
  patterns:
    - Strategy pattern for tile resolution
    - FSM (Finite State Machine) for turn management
    - Event-driven architecture with EventBus
key_files:
  created:
    - ctp/tiles/__init__.py
    - ctp/tiles/base.py
    - ctp/tiles/registry.py
    - ctp/tiles/land.py
    - ctp/tiles/resort.py
    - ctp/tiles/prison.py
    - ctp/tiles/travel.py
    - ctp/tiles/tax.py
    - ctp/tiles/start.py
    - ctp/tiles/festival.py
    - ctp/tiles/fortune.py
    - ctp/controller/__init__.py
    - ctp/controller/fsm.py
    - ctp/controller/bankruptcy.py
    - main.py
    - tests/test_tiles.py
    - tests/test_fsm.py
    - tests/test_headless.py
  modified: []
decisions:
  - "TileStrategy uses abstract base class with on_land/on_pass methods"
  - "TileRegistry maps SpaceId to strategy instances"
  - "FSM states: ROLL -> MOVE -> RESOLVE_TILE -> CHECK_BANKRUPTCY -> END_TURN"
  - "Bankruptcy resolution sells cheapest properties first at 50% value"
  - "FortuneStrategy is stub (creates CARD_DRAWN event, no effect applied)"
metrics:
  duration: ~5 minutes
  completed_date: "2026-04-02"
  tasks: 3
  files: 18
  tests: 112
---

# Phase 01 Plan 03: Tile Strategies, FSM, and Headless Runner Summary

## One-Liner

TileStrategy pattern with all 7 tile types, GameController FSM with turn phases, and headless runner for AI-only game execution.

## Overview

This plan completes Phase 1 by implementing:
1. **TileStrategy Pattern**: Abstract base class and 7 implementations for all tile types
2. **GameController FSM**: Turn state machine with 5 phases
3. **Headless Runner**: main.py entry point that runs full game with console output

## Implementation Details

### Task 1: TileStrategy Base Class and 7 Implementations

Created `ctp/tiles/` package with:
- `base.py`: Abstract `TileStrategy` class with `on_land()` and `on_pass()` methods
- `registry.py`: `TileRegistry` class mapping `SpaceId` to strategy instances
- 7 concrete strategy implementations:
  - **LandStrategy**: Property purchase, rent payment (5 building levels)
  - **ResortStrategy**: Resort property (3 max upgrade, exponential toll)
  - **PrisonStrategy**: Sets prison_turns_remaining
  - **TravelStrategy**: Teleports to Start, charges 2% travel cost
  - **TaxStrategy**: Charges 10% tax on cash
  - **StartStrategy**: 15% passing bonus, no landing effect
  - **FestivalStrategy**: Pot mechanics with level tracking
  - **FortuneStrategy**: STUB - creates CARD_DRAWN event, no effect

### Task 2: GameController FSM

Created `ctp/controller/` package with:
- `fsm.py`: `GameController` class with FSM states:
  - `ROLL`: Roll 2d6 dice
  - `MOVE`: Move player, detect passing Start
  - `RESOLVE_TILE`: Apply tile effect via TileRegistry
  - `CHECK_BANKRUPTCY`: Detect and resolve bankruptcy
  - `END_TURN`: Advance to next player, check terminal conditions
- `bankruptcy.py`: `resolve_bankruptcy()` function that sells properties at 50% rate

### Task 3: Headless Runner

Created `main.py`:
- `--headless` flag for headless execution
- `--players` flag (2-4 players)
- `--turns` flag to override max turns
- Event-driven console logging
- End-game summary with winner, total turns, final standings

## Verification

All success criteria met:
- `python main.py --headless --turns 10` runs without unhandled exceptions
- All 7 tile types resolve correctly when player lands on them
- Game ends at max_turns or when 1 player remains
- Player bankruptcy is detected and marked is_bankrupt=True
- Console output shows: player ID, dice, tile, effect, cash
- End-game summary shows winner, total turns, final cash per player
- All 112 tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

1. **FortuneStrategy**: Creates CARD_DRAWN event but applies no effect (per D-03). Card effects (EF_X codes) will be implemented in Phase 3.

2. **TravelStrategy**: Teleports to Start (position 1) - could be enhanced to random unowned property in future.

3. **Rent recipient**: Rent is recorded in events but not automatically credited to property owner (simplified for Phase 1).

## Test Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| tests/test_tiles.py | 28 | PASS |
| tests/test_fsm.py | 19 | PASS |
| tests/test_headless.py | 9 | PASS |
| tests/test_config.py | 28 | PASS |
| tests/test_game_model.py | 28 | PASS |
| **Total** | **112** | **PASS** |

## Commit History

- `1468c1f` feat(01-03): implement TileStrategy pattern with all 7 tile types
- `0e321c8` feat(01-03): implement GameController FSM with turn phases
- `672a892` feat(01-03): implement headless runner and main.py entry point

## Self-Check: PASSED

- All created files exist
- All commits verified in git log
- All 112 tests pass
- Headless runner executes successfully to completion