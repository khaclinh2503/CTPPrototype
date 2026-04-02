---
phase: 01-headless-core
plan: 02
subsystem: core
tags: [core, models, board, player, events]
dependency_graph:
  requires: [01-01]
  provides: [core-models, board-tiles, event-system]
  affects: [game-loop, fsm, tiles]
tech_stack:
  added: [IntEnum, dataclass, deque]
  patterns: [Strategy-enum, publish-subscribe, TDD]
key_files:
  created:
    - ctp/core/__init__.py
    - ctp/core/board.py
    - ctp/core/models.py
    - ctp/core/events.py
    - tests/test_game_model.py
  modified: []
decisions:
  - "SpaceId uses IntEnum for natural numeric comparison with Board.json values"
  - "Tile dataclass includes optional owner_id and building_level for Phase 2+ features"
  - "EventBus uses deque for queue and list for history (simpler than full queue implementation)"
---

# Phase 01 Plan 02: Core Game Model Summary

## Objective

Create the core game model: Player dataclass, Board/Tile objects, and EventBus system.

## One-Liner

Core game model with SpaceId enum, Board/Tile structures, Player dataclass, and EventBus for FSM event flow.

## Implementation Summary

### Task 1: SpaceId enum and Board/Tile core structures

**Created:**
- `ctp/core/board.py` with:
  - `SpaceId(IntEnum)`: TAX=1, FORTUNE_CARD=2, LAND=3, PRISON=4, FESTIVAL=5, FORTUNE_EVENT=6, START=7, TRAVEL=8, RESORT=9
  - `Tile` dataclass: position, space_id, opt, owner_id, building_level
  - `Board` class: constructs 32 tiles from SpacePosition0 config, provides get_tile(), get_land_config(), get_resort_config(), get_festival_config()

**Tests:** 22 tests covering SpaceId, Tile, and Board

### Task 2: Player dataclass

**Created:**
- `ctp/core/models.py` with:
  - `Player` dataclass: player_id, cash, position, is_bankrupt, owned_properties, prison_turns_remaining
  - Methods: can_afford(), receive(), pay(), move_to(), move_forward(), add_property(), remove_property(), enter_prison(), exit_prison(), decrement_prison_turn()

**Tests:** 5 tests covering Player creation and money operations

### Task 3: GameEvent and EventBus

**Created:**
- `ctp/core/events.py` with:
  - `EventType(Enum)`: 17 event types for game actions (DICE_ROLL, PLAYER_MOVE, TILE_LANDED, etc.)
  - `GameEvent` dataclass: event_type, player_id, data, timestamp
  - `EventBus` class: subscribe(), unsubscribe(), publish(), get_events(), clear(), event_count

**Tests:** 6 tests covering EventBus subscribe/publish and history

## Verification

```
python -m pytest tests/test_game_model.py -x -v
============================= 33 passed in 0.05s ==============================
```

## Deviation Documentation

### Auto-fixed Issues

None - plan executed exactly as written.

## Dependencies Satisfied

- CORE-01: Core data structures (SpaceId, Tile, Board) - COMPLETE
- CORE-02: Player model with basic operations - COMPLETE

## Known Stubs

None - all components are fully functional.

## Self-Check: PASSED

- [x] ctp/core/__init__.py exists
- [x] ctp/core/board.py contains SpaceId, Tile, Board
- [x] ctp/core/models.py contains Player
- [x] ctp/core/events.py contains GameEvent, EventBus
- [x] tests/test_game_model.py exists with 33 tests
- [x] All tests pass
- [x] Commit 148f702 exists