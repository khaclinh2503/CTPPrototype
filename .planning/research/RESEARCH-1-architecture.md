# Research: Board Game Simulator Architecture

**Domain:** Monopoly-style board game AI simulator
**Researched:** 2026-04-01
**Confidence:** MEDIUM (verified against multiple open-source projects + Pygame docs)

---

## 1. Recommended Architecture Pattern

**Use MVC + Event Bus.** This is the consensus across Pygame documentation, open-source
Monopoly simulators, and game engine literature.

```
GameModel        <- pure game state, no rendering, no input
   |
EventBus         <- decoupled pub/sub (Pygame custom events or simple observer)
   |
GameView         <- reads model, renders to screen
GameController   <- drives AI turns, updates model, posts events
```

The Pygame wiki's `tut_design` explicitly recommends an `EventManager` (mediator/observer)
that uses weak references so listeners can be added/removed without explicit cleanup.
Do NOT let the model import from the view layer.

---

## 2. Layer Breakdown

### GameModel
Owns all mutable game state. No Pygame dependencies.

```
GameModel
  ├── Board           — tile list, spatial layout, ownership map
  ├── players[]       — Player objects
  ├── bank            — shared resource pool
  ├── deck            — shuffled event/card pool
  ├── turn_state      — whose turn, phase (roll / move / resolve / end)
  └── history         — append-only event log (for AI learning)
```

### Board / Tile
Each tile is a data object loaded from config. Tile types drive behavior via a
**Strategy pattern** — `LandStrategy.execute(player, game_model)`. Avoids a giant
`if tile_type == X` chain.

```python
@dataclass
class Tile:
    id: str
    type: str            # "property" | "tax" | "goto" | "event" | "safe"
    name: str
    position: int
    config: dict         # type-specific fields from JSON

class TileStrategy:
    def on_land(self, player: Player, model: GameModel) -> list[GameEvent]: ...
```

### Player
Holds position, cash, inventory (owned tiles, pets, skills, pendants).
Passive buffs are summed at resolution time — do NOT bake them into base stats.

```python
@dataclass
class Player:
    id: str
    position: int
    cash: int
    owned_tiles: list[str]
    skills: list[Skill]      # loaded from config
    pendant: Pendant | None
    pet: Pet | None

    def effective_stat(self, stat: str) -> float:
        base = BASE_STATS[stat]
        for modifier in (self.skills + [self.pendant, self.pet]):
            if modifier: base += modifier.delta.get(stat, 0)
        return base
```

### EventBus
Use Python's built-in `collections.deque` as a queue. Each game action
produces `GameEvent` objects that are dispatched after the model update.
The view subscribes and animates based on events, not polling.

```python
@dataclass
class GameEvent:
    type: str          # "player_moved" | "tile_resolved" | "player_bankrupt" ...
    payload: dict
    tick: int          # game tick for replay
```

---

## 3. Config-Driven System

**Recommendation: Pydantic v2 models to validate JSON/YAML at load time.**
Fail fast on bad config rather than runtime crashes mid-game.

### File Layout

```
config/
  board.json          — tile list with positions, types, parameters
  skills.yaml         — skill definitions with stat deltas
  pendants.yaml       — pendant definitions
  pets.yaml           — pet definitions
  game_rules.yaml     — starting cash, board size, turn limits, win condition
```

### Load Pattern

```python
from pydantic import BaseModel

class TileConfig(BaseModel):
    id: str
    type: str
    name: str
    position: int
    rent: int | None = None
    tax_amount: int | None = None

class BoardConfig(BaseModel):
    tiles: list[TileConfig]

# At startup:
with open("config/board.json") as f:
    board_cfg = BoardConfig.model_validate_json(f.read())
```

Pydantic generates clear error messages pointing to the bad field. Use
`model_config = ConfigDict(extra='forbid')` to catch typos in config files.

### YAML vs JSON

- Use **JSON** for the board map (machine-edited, precise types).
- Use **YAML** for skills/pendants/pets (human-authored, readability matters).
- PyYAML (`pip install pyyaml`) or `ruamel.yaml` for YAML parsing.
- Feed both through the same Pydantic model; format doesn't matter post-parse.

---

## 4. Class Responsibility Map

| Class | Owns | Does NOT Own |
|-------|------|--------------|
| `GameModel` | all state, event log | rendering, AI logic |
| `TileStrategy` | land resolution logic | player state |
| `Player` | position, cash, inventory | board knowledge |
| `AIAgent` | decision strategy | model mutation |
| `GameController` | turn sequencing, calling AI | rendering |
| `GameView` | sprites, animations, draw calls | game rules |
| `ConfigLoader` | parsing + validation | defaults |

---

## 5. Turn Sequence (Finite State Machine)

Implement the turn as a small FSM, not a long procedural function.
This makes speed control (step-by-step vs fast-forward) trivial.

```
States: ROLL → MOVE → RESOLVE_TILE → CHECK_BANKRUPTCY → END_TURN
```

Each state transition emits a `GameEvent`. The controller advances the FSM.
In step-by-step mode, the controller waits for user input between states.
In fast-forward mode, the controller loops until `END_TURN` with no rendering.

---

## 6. Passive Buff Resolution

Since all player modifiers (skills, pendant, pet) are passive:

- Store them as lists of `StatDelta` objects on the player.
- Compute effective values lazily when needed — no pre-computation.
- Use a single `resolve_modifiers(player, stat_name)` function called from
  within tile strategies and game rules.
- Never store computed totals; always re-derive from the source list.

This makes hot-swapping config (e.g., a pet changing mid-game) safe.

---

## 7. Open-Source Reference Projects

- **giogix2/MonopolySimulator** — modular `monosim` package, strategy pattern
  for player behavior, K-arm bandit for AI learning
- **gamescomputersplay/monopoly** — config-driven player archetypes, 200-300
  games/sec simulation speed, behavioral parameterization in `settings.py`
- **mayankkejriwal/GNOME** — Monopoly simulator for novelty detection research,
  shows how to abstract game rules for testability

---

## 8. Critical Pitfalls

### God Object Anti-Pattern
The most common failure mode: a single `Game` class handles dice rolls, movement,
property resolution, AI decisions, and rendering. Split from day one.

### Mutable Global State
Avoid module-level globals for `current_player`, `board`, etc. Pass the `GameModel`
explicitly through function arguments or dependency injection.

### Tight Coupling of AI and Rendering
If AI logic calls Pygame functions, you cannot run headless simulations (needed for
training). Keep AI in a layer that has no Pygame imports.

### Missing Turn Limit
All Monopoly simulations can stalemate. Implement a `max_turns` rule in `game_rules.yaml`.
Without it, games loop forever and AI training diverges.

---

## Sources

- Pygame design tutorial: https://www.pygame.org/wiki/tut_design
- giogix2/MonopolySimulator: https://github.com/giogix2/MonopolySimulator
- gamescomputersplay/monopoly: https://github.com/gamescomputersplay/monopoly
- Pydantic v2 docs: https://docs.pydantic.dev/latest/concepts/models/
- Game engine architecture patterns: https://generalistprogrammer.com/game-design-patterns
