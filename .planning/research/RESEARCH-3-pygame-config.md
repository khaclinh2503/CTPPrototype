# Research: Pygame Visualization and Config System

**Domain:** Board game UI with speed control + config-driven game data
**Researched:** 2026-04-01
**Confidence:** HIGH (Pygame docs + well-established patterns)

---

## 1. Pygame Game Loop for Speed Control

### The Core Pattern: Decouple Logic from Rendering

```python
LOGIC_FPS = 60        # fixed logical tick rate
RENDER_FPS = 60       # display frame rate (can differ)

clock = pygame.time.Clock()
logic_accumulator = 0.0

while running:
    dt_ms = clock.tick(RENDER_FPS)  # milliseconds since last frame
    logic_accumulator += dt_ms

    handle_events()

    while logic_accumulator >= (1000 / LOGIC_FPS):
        game_controller.step()      # advance one logical tick
        logic_accumulator -= (1000 / LOGIC_FPS)

    game_view.render(game_model)
    pygame.display.flip()
```

This fixed-timestep pattern means game logic runs at a constant rate regardless
of rendering FPS. Crucial for reproducible simulations and replay correctness.

### Speed Control Implementation

Expose a `simulation_speed` multiplier. Do not change the LOGIC_FPS.
Instead, drain the accumulator faster:

```python
class SpeedController:
    def __init__(self):
        self.speed = 1.0      # 1x = real time, 10x = fast, 0 = paused

    def advance(self, dt_ms: float, logic_fps: int) -> int:
        """Returns number of logic ticks to execute this frame."""
        tick_ms = 1000 / logic_fps
        return int((dt_ms * self.speed) / tick_ms)
```

For fast-forward (no rendering): skip `game_view.render()` entirely and
loop `game_controller.step()` without yielding to the display. This is how
200-300 games/sec is achievable.

### Step-by-Step Mode

```python
class StepMode:
    CONTINUOUS = "continuous"
    STEP = "step"        # one game event at a time

# In game loop:
if mode == StepMode.STEP:
    if user_pressed_space():
        game_controller.step_one_event()
        game_view.render(game_model)
```

Implement `step_one_event()` to process exactly one `GameEvent` from the queue
and stop. This gives the "next move" button behavior for inspection.

---

## 2. Board Rendering Architecture

### Layer Stack (draw order)

```
Layer 0: Board background (static, blit once, cache as Surface)
Layer 1: Tile overlays (ownership color, development level) — redraw on change
Layer 2: Player tokens (moving sprites)
Layer 3: Floating UI (event popups, dice result, cash delta indicators)
Layer 4: HUD (player info panel, speed control, turn counter)
```

### Dirty Rect Optimization

For a board game where most of the screen is static between animations:

```python
dirty_rects = []

# Only redraw what changed:
if player_moved:
    dirty_rects.append(draw_token(player, old_pos))  # erase old
    dirty_rects.append(draw_token(player, new_pos))  # draw new

pygame.display.update(dirty_rects)   # not flip() — only update changed areas
```

Use `pygame.sprite.LayeredDirty` group for tokens. It manages dirty tracking
automatically. Fall back to full `display.flip()` during animations.

### Board Coordinate System

Define tile positions as a lookup table built at startup from config:

```python
def build_tile_positions(tiles: list[TileConfig], board_rect: pygame.Rect) -> dict:
    """Maps tile_id -> (x, y) pixel center based on position index."""
    positions = {}
    for tile in tiles:
        positions[tile.id] = index_to_pixel(tile.position, board_rect)
    return positions
```

`index_to_pixel` converts a linear tile index to a coordinate along the board
perimeter. For a custom layout, just hardcode the pixel positions in `board.json`:

```json
{ "id": "start", "position": 0, "pixel_x": 700, "pixel_y": 700 }
```

This is simpler than computing layout from rules and allows irregular shapes.

---

## 3. Animation System

### Event-Driven Animation Queue

Do not animate directly in AI/controller code. Post animation requests to a queue
that the view drains each frame.

```python
@dataclass
class AnimationRequest:
    type: str          # "move_token" | "show_popup" | "highlight_tile"
    player_id: str | None
    from_pos: tuple | None
    to_pos: tuple | None
    duration_ms: int
    payload: dict

class AnimationQueue:
    def __init__(self):
        self._queue: deque[AnimationRequest] = deque()
        self._active: AnimationRequest | None = None
        self._elapsed: float = 0

    def push(self, req: AnimationRequest): ...
    def update(self, dt_ms: float) -> bool:
        """Returns True when current animation completes."""
        ...
```

In fast-forward mode, drain the animation queue without sleeping:
`while not anim_queue.empty(): anim_queue.skip()`.

### Token Movement

Use linear interpolation between tile pixel positions:

```python
def lerp_pos(start, end, t):
    return (start[0] + (end[0] - start[0]) * t,
            start[1] + (end[1] - start[1]) * t)

# In update:
t = elapsed_ms / animation.duration_ms
token.rect.center = lerp_pos(from_pos, to_pos, min(t, 1.0))
```

For longer moves (crossing many tiles), tween through intermediate positions.

---

## 4. Config System Implementation

### Directory Layout

```
config/
  board.json          — tile definitions with pixel positions
  skills.yaml         — skill id, name, stat deltas
  pendants.yaml
  pets.yaml
  game_rules.yaml     — turn limits, starting cash, win conditions, etc.
  agents.yaml         — AI personality parameters

assets/
  tiles/              — tile artwork (named by tile id)
  tokens/             — player token sprites
  ui/                 — HUD elements, fonts
```

### Config Loading Pipeline

```python
# config_loader.py

import json, yaml
from pathlib import Path
from pydantic import BaseModel

class ConfigLoader:
    BASE = Path("config")

    def load_board(self) -> BoardConfig:
        return BoardConfig.model_validate_json(
            (self.BASE / "board.json").read_text()
        )

    def load_yaml(self, name: str, model_cls):
        raw = yaml.safe_load((self.BASE / name).read_text())
        return model_cls.model_validate(raw)
```

Always load and validate all configs at application startup before entering the
game loop. A `ConfigError` at startup is recoverable; a `KeyError` mid-game is not.

### Pydantic Validation

```python
from pydantic import BaseModel, ConfigDict, field_validator

class StatDelta(BaseModel):
    cash_bonus: int = 0
    rent_reduction: int = 0
    move_bonus: int = 0
    min_cash_reserve: int = 0

class SkillConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    name: str
    description: str
    delta: StatDelta

    @field_validator('id')
    def id_must_be_snake_case(cls, v):
        assert v == v.lower().replace(' ', '_'), "id must be snake_case"
        return v
```

Use `extra='forbid'` on all config models. This catches typos like `rnet_reduction`
that would otherwise silently produce no buff.

---

## 5. Pygame Asset Management

### Simple Asset Cache

```python
class AssetCache:
    def __init__(self):
        self._surfaces: dict[str, pygame.Surface] = {}
        self._fonts: dict[tuple, pygame.font.Font] = {}

    def surface(self, path: str) -> pygame.Surface:
        if path not in self._surfaces:
            self._surfaces[path] = pygame.image.load(path).convert_alpha()
        return self._surfaces[path]

    def font(self, name: str, size: int) -> pygame.font.Font:
        key = (name, size)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont(name, size)
        return self._fonts[key]
```

Call `.convert_alpha()` immediately after loading. Never call it in the render loop.
Tile artwork is loaded once, cached, and reused.

---

## 6. HUD Elements for Speed Control

### Speed Control Widget

```python
class SpeedWidget:
    SPEEDS = [0, 0.5, 1, 2, 5, 10, 50, 0]  # 0 at end = headless
    labels = ["PAUSE", "0.5x", "1x", "2x", "5x", "10x", "FF", "HEADLESS"]

    def draw(self, surface, speed_index):
        # Draw slider or button row with highlight on current index
        ...

    def handle_click(self, pos) -> float | None:
        # Returns new speed multiplier or None if not clicked
        ...
```

Keyboard shortcuts: Space = pause/resume, Right arrow = step, +/- = speed up/down.

---

## 7. Performance Notes

| Scenario | Frames | Approach |
|----------|--------|----------|
| Real-time (1x) | 60 FPS | Normal game loop, animate all events |
| Fast-forward (10x) | 60 FPS | Skip animation lerp, show final positions |
| Headless (training) | N/A | No Pygame display, pure Python loop |

For headless training, wrap rendering behind a flag:

```python
class GameView:
    def __init__(self, headless=False):
        self.headless = headless

    def render(self, model):
        if self.headless:
            return
        # ... normal rendering
```

Do not `pygame.init()` in headless mode. This allows AI training runs without
a display server.

---

## 8. Dependency Stack

```
pygame >= 2.5.0       — rendering, event loop, clock
pydantic >= 2.0       — config validation
pyyaml >= 6.0         — YAML config parsing
```

No additional libraries required for the core system. SQLite (stdlib) for history.

```bash
pip install pygame pydantic pyyaml
```

---

## Sources

- Pygame clock and speed: https://www.pygame.org/docs/ref/time.html
- Constant game speed pattern: https://www.pygame.org/wiki/ConstantGameSpeed
- Pygame design patterns (MVC/Mediator): https://www.pygame.org/wiki/tut_design
- DirtySprite optimization: https://n0nick.github.io/blog/2012/06/03/quick-dirty-using-pygames-dirtysprite-layered/
- Pygame sprite docs: https://www.pygame.org/docs/ref/sprite.html
- Pydantic v2 models: https://docs.pydantic.dev/latest/concepts/models/
- PyYAML: https://python.land/data-processing/python-yaml
