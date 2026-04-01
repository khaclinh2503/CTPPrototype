# Phase 1: Headless Core - Research

**Researched:** 2026-04-01
**Domain:** Python board game engine -- config loading, game model, FSM controller, tile strategies
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield Python project that builds a complete headless board game simulator. The domain is well-understood: Pydantic v2 for config validation, dataclasses for game state, Strategy pattern for tile behavior, and a simple FSM for turn sequencing. All libraries are stable and compatible with the available Python 3.14 runtime.

The primary complexity lies in correctly parsing the existing Board.json structure, which uses numeric `spaceId` codes (not readable strings) to map tile types, and a nested indexing scheme for LandSpace definitions. The Pydantic schemas must faithfully model this existing data format rather than impose a new one.

**Primary recommendation:** Build bottom-up -- config schemas and loader first, then game model dataclasses, then FSM controller with tile strategies. Each layer is independently testable.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Board 32 tiles, layout from `ctp/config/Board.json` (SpacePosition + LandSpace/ResortSpace/etc.)
- **D-02:** Phase 1 implements exactly 7 tile types: Land, Resort, Prison, Travel, Tax, Start, Festival -- each with its own TileStrategy
- **D-03:** FortuneSpace is a stub in Phase 1 -- records the draw event but applies no effect
- **D-04:** Card effects (EF_X codes from Card.json) not implemented in Phase 1
- **D-05:** Land tile has 5 upgrade levels (building level 1-5), schema preserves Board.json format
- **D-06:** Resort tile separate from Land -- uses ResortSpace config (initCost, tollCost, maxUpgrade: 3, increaseRate)
- **D-07:** Pydantic schema validates both Land and Resort when loading Board.json
- **D-08:** Config files inside package: `ctp/config/Board.json`, `ctp/config/Card.json`
- **D-09:** Phase 1 creates skeleton configs: `ctp/config/skills.yaml`, `ctp/config/pendants.yaml`, `ctp/config/pets.yaml`, `ctp/config/game_rules.yaml` -- skeleton only, data filled in Phase 2
- **D-10:** ConfigLoader class loads all files at startup, raises ConfigError if schema invalid
- **D-11:** General section in Board.json provides: limitTurn (max_turns=25), acquireRate, sellRate, winReward
- **D-12:** Player skeleton: player_id, cash, position, is_bankrupt, owned_properties only -- no buff slots
- **D-13:** GameEvent / EventBus queue pattern -- events publish/subscribe in FSM
- **D-14:** Bankruptcy stub: cash < 0 -> sell properties at sell_rate * build_cost -> if still negative -> is_bankrupt = True
- **D-15:** FSM states: ROLL -> MOVE -> RESOLVE_TILE -> CHECK_BANKRUPTCY -> END_TURN
- **D-16:** Dice roll: 2d6 standard
- **D-17:** max_turns from General.limitTurn (=25), game ends at that turn
- **D-18:** `python main.py --headless` prints console log per turn: player ID, dice result, tile landed, effect applied, cash change
- **D-19:** End-of-game summary: winner, total turns, final cash per player
- **D-20:** Feature folder layout: ctp/config/, ctp/core/, ctp/tiles/, ctp/controller/

### Claude's Discretion
- Specific Pydantic model class names (BoardSchema, LandTileSchema, etc.)
- Internal EventBus implementation (simple list vs. deque)
- Test framework (pytest assumed)
- Logging format details for each turn

### Deferred Ideas (OUT OF SCOPE)
- FortuneSpace card effects (EF_2 through EF_29) -- Phase 3
- Buff/passive system (skill, pendant, pet) -- Phase 2
- AI buy/sell/upgrade decisions -- Phase 3
- Multi-map support (Board.json has SpacePosition0-7) -- post Phase 4
- ResortSpace mini-game logic (MiniGame config) -- post Phase 4

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | Game initializes match with 2-4 AI players | GameModel dataclass with players list, configurable player count |
| CORE-02 | Players take turns rolling 2d6 and moving | FSM ROLL->MOVE states, dice module, position wrapping at 32 |
| CORE-03 | Turn loop ends when 1 player not bankrupt or max_turns reached | GameController terminal condition check after each turn |
| CORE-04 | Bankruptcy condition: cash < 0, sell assets insufficient | Bankruptcy resolution in CHECK_BANKRUPTCY FSM state |
| CORE-05 | Support max_turns in config to prevent infinite games | General.limitTurn from Board.json (=25) |
| CONF-01 | Board map read from JSON file | Pydantic schema for Board.json, ConfigLoader.load_board() |
| CONF-02 | Skill definitions from config file, validate schema | Skeleton skills.yaml with Pydantic model, empty data |
| CONF-03 | Pendant definitions from config file | Skeleton pendants.yaml with Pydantic model, empty data |
| CONF-04 | Pet definitions from config file | Skeleton pets.yaml with Pydantic model, empty data |
| CONF-05 | Game rules from config file | General section in Board.json + game_rules.yaml skeleton |
| CONF-06 | Config validation catches schema errors before game start | ConfigLoader raises ConfigError on invalid schema |
| TILE-01 | Land property tile: buy price, upgrade levels 1-5, toll per level | LandStrategy using LandSpace config from Board.json |
| TILE-02 | Prison tile: player loses N turns (N from config per mapId) | PrisonStrategy using PrisonSpace.limitTurnByMapId |
| TILE-03 | Tax tile: pay fixed amount to bank | TaxStrategy using TaxSpace.taxRate |
| TILE-04 | Travel tile: teleport player to destination | TravelStrategy using TravelSpace.travelCostRate |
| TILE-05 | Festival tile: receive bonus or special effect per config | FestivalStrategy using FestivalSpace config (holdCostRate, increaseRate, maxFestival) |
| TILE-06 | Fortune tile: draw random card from deck, apply effect | FortuneStrategy STUB -- records draw, applies no effect in Phase 1 |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Config schema validation | Industry standard for Python data validation; v2 is 5-50x faster than v1 |
| pyyaml | 6.0.3 | YAML config parsing (skills, pendants, pets, game_rules) | De facto Python YAML library |
| pytest | 9.0.2 | Test framework | Claude's discretion -- standard Python test framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib dataclasses | 3.14 built-in | Game model objects (Player, Board, Tile, GameEvent) | All model objects |
| Python stdlib enum | 3.14 built-in | FSM states, tile type enum, spaceId mapping | Type-safe enums |
| Python stdlib argparse | 3.14 built-in | CLI --headless flag | Entry point |
| Python stdlib random | 3.14 built-in | Dice rolls, card shuffling | Game randomness |
| Python stdlib collections.deque | 3.14 built-in | EventBus queue | Event dispatch |
| Python stdlib logging | 3.14 built-in | Turn-by-turn console output | Headless runner |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic | attrs + cattrs | Pydantic is locked decision from STATE.md |
| pyyaml | ruamel.yaml | ruamel preserves comments but is heavier; not needed here |
| pytest | unittest | pytest is simpler syntax, better fixtures |

**Installation:**
```bash
pip install pydantic==2.12.5 pyyaml==6.0.3 pytest==9.0.2
```

## Architecture Patterns

### Recommended Project Structure
```
ctp/
    __init__.py
    config/
        __init__.py
        Board.json              # existing -- 32-tile board layout
        Card.json               # existing -- card definitions
        skills.yaml             # Phase 1 skeleton
        pendants.yaml           # Phase 1 skeleton
        pets.yaml               # Phase 1 skeleton
        game_rules.yaml         # Phase 1 skeleton
        loader.py               # ConfigLoader class
        schemas.py              # All Pydantic models
    core/
        __init__.py
        models.py               # Player, GameState dataclasses
        board.py                # Board, Tile dataclasses
        events.py               # GameEvent, EventBus
    tiles/
        __init__.py
        base.py                 # TileStrategy ABC
        land.py                 # LandStrategy
        resort.py               # ResortStrategy
        prison.py               # PrisonStrategy
        travel.py               # TravelStrategy
        tax.py                  # TaxStrategy
        start.py                # StartStrategy
        festival.py             # FestivalStrategy
        fortune.py              # FortuneStrategy (stub)
        registry.py             # spaceId -> Strategy mapping
    controller/
        __init__.py
        fsm.py                  # GameController FSM
        bankruptcy.py           # Bankruptcy resolution logic
main.py                         # Entry point (--headless)
tests/
    __init__.py
    test_config.py              # Config loading + validation
    test_board.py               # Board construction from config
    test_tiles.py               # Each TileStrategy
    test_fsm.py                 # FSM state transitions
    test_headless.py            # Full game run to completion
```

### Pattern 1: SpaceId Enum Mapping

**What:** Board.json uses numeric `spaceId` codes. Map them to a Python Enum for type safety.
**When to use:** Everywhere tile type is referenced.

```python
from enum import IntEnum

class SpaceId(IntEnum):
    TAX = 1
    FORTUNE_CARD = 2      # Fortune tile (card draw)
    LAND = 3
    PRISON = 4
    FESTIVAL = 5
    FORTUNE_EVENT = 6     # Fortune tile (event variant, opt=101/102)
    START = 7
    TRAVEL = 8
    RESORT = 9
    # spaceId 10 exists in other maps (God space?) -- not in Phase 1 scope
```

**Critical insight:** SpacePosition0 (map 1) has the following distribution across 32 tiles:
- spaceId=3 (Land): 19 tiles -- `opt` field indexes into LandSpace["1"][str(opt)]
- spaceId=6 (Fortune event): 5 tiles -- opt=101 or opt=102
- spaceId=2 (Fortune card): 3 tiles
- spaceId=7 (Start): 1 tile (position 1)
- spaceId=4 (Prison): 1 tile (position 3)
- spaceId=5 (Festival): 1 tile (position 9)
- spaceId=1 (Tax): 1 tile (position 17)
- spaceId=9 (Resort): 1 tile (position 25)
- spaceId=8 (Travel): 1 tile (position 31)

Both spaceId=2 and spaceId=6 are Fortune-related. In Phase 1 both are stubs.

### Pattern 2: Board.json Indexing Scheme

**What:** LandSpace uses a two-level key: `LandSpace[mapId][landIndex]`. The `opt` field in SpacePosition maps to `landIndex`.
**When to use:** ConfigLoader must resolve each tile's data by cross-referencing SpacePosition with the space-type config sections.

```python
# SpacePosition0 is map index 0, which means mapId = "1" (GAME_CUSTOM = mapIndex + 1)
# For tile at position 2: spaceId=3 (Land), opt=1
# -> Look up LandSpace["1"]["1"] -> {color: 1, building: {1: {build: 10, toll: 1}, ...}}

# For PrisonSpace, the limitTurnByMapId uses the same mapId
# Map 1 -> PrisonSpace.limitTurnByMapId["1"] = 2 turns
```

### Pattern 3: TileStrategy with Registry

**What:** Strategy pattern with a registry that maps SpaceId to the correct strategy class.
**When to use:** When resolving what happens when a player lands on a tile.

```python
from abc import ABC, abstractmethod

class TileStrategy(ABC):
    @abstractmethod
    def on_land(self, player: "Player", tile: "Tile", game_state: "GameState") -> list["GameEvent"]:
        """Resolve what happens when player lands on this tile."""
        ...

class TileRegistry:
    _strategies: dict[SpaceId, TileStrategy] = {}

    @classmethod
    def register(cls, space_id: SpaceId, strategy: TileStrategy):
        cls._strategies[space_id] = strategy

    @classmethod
    def resolve(cls, space_id: SpaceId) -> TileStrategy:
        return cls._strategies[space_id]
```

### Pattern 4: FSM as Enum + Controller

**What:** Turn states as an Enum, controller advances through them.
**When to use:** GameController drives each turn.

```python
from enum import Enum, auto

class TurnPhase(Enum):
    ROLL = auto()
    MOVE = auto()
    RESOLVE_TILE = auto()
    CHECK_BANKRUPTCY = auto()
    END_TURN = auto()

class GameController:
    def __init__(self, game_state: GameState):
        self.state = game_state
        self.phase = TurnPhase.ROLL

    def step(self) -> list[GameEvent]:
        """Advance one FSM step. Returns events produced."""
        match self.phase:
            case TurnPhase.ROLL:
                events = self._do_roll()
                self.phase = TurnPhase.MOVE
            case TurnPhase.MOVE:
                events = self._do_move()
                self.phase = TurnPhase.RESOLVE_TILE
            # ... etc
        return events
```

### Anti-Patterns to Avoid
- **Giant if/else for tile types:** Use Strategy pattern (locked decision). Each tile type is its own class.
- **Pygame imports in core/tiles/controller:** Phase 1 is headless. Zero rendering dependencies in game logic.
- **Storing computed values:** Never store "effective rent" -- always derive from building level + config at resolution time. This makes future buff stacking (Phase 2) safe.
- **Hardcoded spaceId numbers:** Use the SpaceId enum everywhere, not magic numbers.
- **Mutable global state:** Pass GameState explicitly. No module-level singletons for board/players.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON/YAML schema validation | Custom validation loops | Pydantic v2 BaseModel | Handles nested types, clear error messages, `extra='forbid'` catches typos |
| CLI argument parsing | Manual sys.argv parsing | argparse (stdlib) | --headless flag, future --map-id, --players flags |
| YAML parsing | Custom parser | PyYAML safe_load | Battle-tested, handles all YAML edge cases |
| Enum with integer mapping | Dict lookups with string keys | IntEnum (stdlib) | Type-safe, works in match statements, self-documenting |
| Event queue | Custom linked list | collections.deque (stdlib) | O(1) append/popleft, thread-safe for future use |

**Key insight:** This phase has zero external complexity. Every "don't hand-roll" item is a stdlib or single well-known library. The real work is modeling the Board.json structure correctly.

## Common Pitfalls

### Pitfall 1: Board.json Indexing Off-by-One
**What goes wrong:** SpacePosition keys are "1"-"32" (1-indexed strings), not 0-indexed integers. LandSpace keys are also string-indexed. Mixing up int vs str keys causes KeyError at runtime.
**Why it happens:** Python developers default to 0-indexed int thinking.
**How to avoid:** Pydantic schema should model keys as `dict[str, ...]` not `dict[int, ...]`. Convert to 0-indexed internally only after loading.
**Warning signs:** KeyError during config loading tests.

### Pitfall 2: Position Wrapping at Board Boundary
**What goes wrong:** Player at position 30 rolls 7, should land on position 5 (wraps around 32-tile board). Naive addition gives position 37.
**Why it happens:** Forgetting modular arithmetic.
**How to avoid:** `new_position = (current_position + dice_roll - 1) % board_size + 1` (if 1-indexed) or `new_position = (current_position + dice_roll) % board_size` (if 0-indexed). Also must detect passing Start for bonus.
**Warning signs:** IndexError or player position > 32.

### Pitfall 3: Start Tile Passing Bonus vs Landing Bonus
**What goes wrong:** passingBonusRate (0.15) should apply when a player passes through position 1, not just when they land on it. Landing might have a different effect or the same.
**Why it happens:** Only implementing on_land for StartStrategy but not checking during MOVE phase.
**How to avoid:** Check for passing Start in the MOVE phase (before RESOLVE_TILE). The passing bonus is `cash * passingBonusRate` -- note this is a percentage of current cash, not a flat amount.
**Warning signs:** Players never gain money from passing Start.

### Pitfall 4: Bankruptcy Sell Order and Partial Recovery
**What goes wrong:** Player goes bankrupt when they could have sold properties to cover debt. Or sells properties but doesn't account for the sell rate correctly.
**Why it happens:** Bankruptcy resolution is non-trivial: must sell at `sellRate * total_build_cost` (0.5x), check if that covers the debt, repeat for each property.
**How to avoid:** Implement as a loop: while cash < 0 and has_properties, sell cheapest property. Mark bankrupt only when no properties remain and cash still < 0.
**Warning signs:** Players go bankrupt with unsold properties, or recovered cash doesn't match expected sell values.

### Pitfall 5: TaxSpace and TravelSpace Use Rate-Based Costs
**What goes wrong:** Treating tax and travel costs as flat amounts when they are actually rates (percentages).
**Why it happens:** Misreading config field names.
**How to avoid:** TaxSpace.taxRate = 0.1 means player pays `cash * 0.1`. TravelSpace.travelCostRate = 0.02 means player pays `cash * 0.02` when teleported. PrisonSpace.escapeCostRate = 0.1 means escape costs `cash * 0.1`.
**Warning signs:** All players pay the same tax regardless of wealth.

### Pitfall 6: Festival Space State Tracking
**What goes wrong:** FestivalSpace has `holdCostRate`, `increaseRate`, `maxFestival` -- this implies festival state is tracked on the board (not just per-player). Missing this means festival effects don't accumulate.
**Why it happens:** Treating Festival as a simple "collect money" tile.
**How to avoid:** Board needs a `festival_level` or similar state that increments each time a player lands on the festival tile (up to maxFestival). The holdCostRate is the cost rate, increaseRate multiplies the effect.
**Warning signs:** Festival tile always gives the same reward regardless of how many times it's been visited.

### Pitfall 7: Resort vs Land Confusion
**What goes wrong:** Treating Resort like Land with different numbers. Resort has fundamentally different upgrade mechanics: maxUpgrade=3 (not 5), uses initCost/tollCost/increaseRate (not building tiers).
**Why it happens:** Both are "property" tiles you can buy.
**How to avoid:** Separate ResortStrategy and LandStrategy classes. Separate Pydantic schemas for ResortSpace and LandSpace. Resort toll = `tollCost * (increaseRate ^ upgrade_level)`. Land toll = `building[level].toll`.
**Warning signs:** Resort upgrade goes to level 5, or resort toll doesn't scale exponentially.

### Pitfall 8: tollMultiply Special Case
**What goes wrong:** Board.json General section has `tollMultiply: {"3": {"11": 2}}` -- on map 3, land tile index 11 has a 2x toll multiplier. Ignoring this produces incorrect rent.
**Why it happens:** Easy to miss in the General config.
**How to avoid:** After computing base toll for a land tile, check `tollMultiply[mapId][landIndex]` for a multiplier. Apply it. For Phase 1 using map 1, there is no tollMultiply entry (only map 3 has one), but the code should still support it.
**Warning signs:** N/A for map 1, but architecture should accommodate it.

## Code Examples

### Config Schema for Board.json (verified against actual file)

```python
from pydantic import BaseModel, ConfigDict

class BuildingLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    build: int    # cost to build this level
    toll: int     # rent when opponent lands

class LandTileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color: int
    building: dict[str, BuildingLevel]  # keys "1"-"5"

class GeneralConfig(BaseModel):
    limitTime: int
    limitTurn: int          # max_turns = 25
    actionTimeout: int
    acquireRate: int | float
    sellRate: float         # 0.5
    winReward: float        # 0.9
    defaultHouse: dict[str, dict] | None = None
    tollMultiply: dict[str, dict[str, int]] | None = None
    cardKeepLimit: dict[str, int] | None = None

class SpacePositionEntry(BaseModel):
    spaceId: int
    opt: int

class PrisonSpaceConfig(BaseModel):
    escapeCostRate: float
    limitTurnByMapId: dict[str, int]

class ResortSpaceConfig(BaseModel):
    maxUpgrade: int         # 3
    initCostRate: float
    increaseRate: int | float
    initCost: int
    tollCost: int

class StartSpaceConfig(BaseModel):
    passingBonusRate: float  # 0.15

class TaxSpaceConfig(BaseModel):
    taxRate: float           # 0.1

class TravelSpaceConfig(BaseModel):
    travelCostRate: float    # 0.02

class FestivalSpaceConfig(BaseModel):
    holdCostRate: float
    increaseRate: int | float
    maxFestival: int

class FortuneSpaceConfig(BaseModel):
    deckSet: list[str]       # list of card IDs

class BoardConfig(BaseModel):
    General: GeneralConfig
    SpacePosition0: dict[str, SpacePositionEntry]  # map 1
    LandSpace: dict[str, dict[str, LandTileConfig]]  # LandSpace[mapId][landIndex]
    PrisonSpace: PrisonSpaceConfig
    ResortSpace: ResortSpaceConfig
    StartSpace: StartSpaceConfig
    TaxSpace: TaxSpaceConfig
    TravelSpace: TravelSpaceConfig
    FestivalSpace: FestivalSpaceConfig
    FortuneSpace: FortuneSpaceConfig
    # SpacePosition1-7 and other maps exist but are out of Phase 1 scope
    model_config = ConfigDict(extra="allow")  # allow other SpacePosition keys
```

### Game Model Dataclasses

```python
from dataclasses import dataclass, field

@dataclass
class Player:
    player_id: str
    cash: float
    position: int = 1          # 1-indexed, start at position 1
    is_bankrupt: bool = False
    owned_properties: list[int] = field(default_factory=list)  # tile positions
    prison_turns_remaining: int = 0  # 0 = not in prison

@dataclass
class Tile:
    position: int              # 1-32
    space_id: SpaceId
    opt: int                   # type-specific index
    config: dict | None = None # resolved config data for this tile
    owner_id: str | None = None
    building_level: int = 0    # for Land/Resort

@dataclass
class GameState:
    board: list[Tile]          # 32 tiles, index 0 = position 1
    players: list[Player]
    current_player_index: int = 0
    current_turn: int = 1
    max_turns: int = 25
    map_id: str = "1"
    sell_rate: float = 0.5
    acquire_rate: float = 1.0
    festival_level: int = 0   # board-level festival state
```

### Bankruptcy Resolution

```python
def resolve_bankruptcy(player: Player, game_state: GameState) -> list[GameEvent]:
    events = []
    while player.cash < 0 and player.owned_properties:
        # Sell cheapest property first
        prop_pos = min(player.owned_properties,
                       key=lambda p: _total_build_cost(game_state, p))
        tile = game_state.board[prop_pos - 1]
        sell_value = _total_build_cost(game_state, prop_pos) * game_state.sell_rate
        player.cash += sell_value
        player.owned_properties.remove(prop_pos)
        tile.owner_id = None
        tile.building_level = 0
        events.append(GameEvent("property_sold", {
            "player": player.player_id,
            "position": prop_pos,
            "value": sell_value
        }))
    if player.cash < 0:
        player.is_bankrupt = True
        events.append(GameEvent("player_bankrupt", {
            "player": player.player_id
        }))
    return events
```

### Dice and Movement with Start Passing Detection

```python
import random

def roll_dice() -> tuple[int, int]:
    return (random.randint(1, 6), random.randint(1, 6))

def move_player(player: Player, dice_total: int, board_size: int = 32) -> tuple[int, bool]:
    """Returns (new_position, passed_start)."""
    old_pos = player.position
    new_pos = old_pos + dice_total
    passed_start = new_pos > board_size
    new_pos = ((new_pos - 1) % board_size) + 1  # 1-indexed wrapping
    player.position = new_pos
    return new_pos, passed_start
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 | Pydantic v2 (2.x) | 2023-06 | 5-50x faster validation, `model_validate_json` replaces `parse_raw` |
| `class Config:` inner class | `model_config = ConfigDict(...)` | Pydantic v2 | Old syntax deprecated |
| Python 3.9 `Optional[X]` | Python 3.10+ `X \| None` | 2021 | Cleaner type annotations |
| `@dataclass` with __post_init__ validation | Pydantic for validated data, dataclass for plain state | Current best practice | Use Pydantic for external data (config), dataclasses for internal state |

## Open Questions

1. **SpaceId mapping verification**
   - What we know: From analyzing SpacePosition0, spaceId values 1-9 are used. Mapping deduced from tile positions and config section names.
   - What is unclear: The exact meaning of spaceId=6 opt=101 vs opt=102 (both appear to be Fortune variants). SpaceId=10 appears in other maps but not map 1.
   - Recommendation: Treat both spaceId=2 and spaceId=6 as Fortune tiles (stub). The opt field for Fortune may indicate draw-from-deck vs event-trigger variants -- does not matter in Phase 1 since both are stubs.

2. **Travel tile destination**
   - What we know: TravelSpace config only has `travelCostRate: 0.02`. No explicit destination defined.
   - What is unclear: Where does the Travel tile teleport the player to? Is it random? Is it a fixed offset? The config does not specify a destination.
   - Recommendation: For Phase 1, implement Travel as "pay cost, move to a random unoccupied tile" or "pay cost, move to Start" -- document the stub behavior and revisit when more game rules are clarified.

3. **Festival space mechanics**
   - What we know: FestivalSpace has holdCostRate=0.02, increaseRate=2, maxFestival=1. This suggests a festival "pot" that grows.
   - What is unclear: Exact mechanics -- does holdCostRate mean each player pays 2% of cash into a pot? Does increaseRate=2 mean the pot doubles? Does maxFestival=1 mean only 1 festival can be active?
   - Recommendation: Implement a simple version: player landing on Festival pays `cash * holdCostRate` into a pot, then receives `pot * increaseRate` back. Cap active festivals at maxFestival. Log behavior for tuning.

4. **Starting cash amount**
   - What we know: Board.json General section does not specify starting cash. game_rules.yaml is a Phase 1 skeleton.
   - What is unclear: How much cash each player starts with.
   - Recommendation: Define starting cash in game_rules.yaml skeleton. Use a reasonable default (e.g., 200 based on Board.json land costs ranging 10-50 for level 1 builds).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | Yes | 3.14.2 | -- |
| pip | Package install | Yes | 26.0.1 | -- |
| pydantic | Config validation | Not installed | 2.12.5 (available) | pip install |
| pyyaml | YAML parsing | Not installed | 6.0.3 (available) | pip install |
| pytest | Testing | Not installed | 9.0.2 (available) | pip install |

**Missing dependencies with no fallback:**
- None -- all dependencies are installable via pip.

**Missing dependencies with fallback:**
- None -- all available.

## Sources

### Primary (HIGH confidence)
- `ctp/config/Board.json` -- actual game data, analyzed structure directly
- `ctp/config/Card.json` -- card definitions, verified format
- `.planning/research/RESEARCH-1-architecture.md` -- MVC+EventBus pattern, Strategy pattern
- `.planning/research/RESEARCH-2-ai-strategy.md` -- AI approach (not Phase 1 scope but informs design)
- `.planning/research/RESEARCH-3-pygame-config.md` -- Pydantic v2 patterns, config loading

### Secondary (MEDIUM confidence)
- pip dry-run output -- verified library versions available for Python 3.14
- Pydantic v2 docs (https://docs.pydantic.dev/latest/) -- ConfigDict, model_validate_json patterns

### Tertiary (LOW confidence)
- SpaceId enum mapping -- deduced from Board.json structure analysis, not from source code or documentation. Mapping is consistent but unverified against original game code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Pydantic v2, PyYAML, pytest are locked decisions with verified availability
- Architecture: HIGH -- MVC+EventBus+Strategy are locked decisions from STATE.md, well-documented patterns
- Config schema: HIGH -- directly analyzed actual Board.json file structure
- SpaceId mapping: MEDIUM -- deduced from data analysis, internally consistent but unverified
- Tile mechanics (Festival, Travel): LOW -- config fields suggest behavior but exact rules unclear

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable domain, no external API dependencies)
