# Research: AI Strategy for Monopoly-Style Game

**Domain:** Fully automated multi-agent board game AI
**Researched:** 2026-04-01
**Confidence:** HIGH for heuristic + MCTS (well-documented); MEDIUM for RL (complex setup)

---

## 1. Approach Comparison

| Approach | Suitability | Complexity | Training Required | Notes |
|----------|-------------|------------|-------------------|-------|
| Heuristic / Rule-Based | HIGH | Low | No | Fast, debuggable, good baseline |
| Monte Carlo Simulation | HIGH | Low-Medium | No | Best for property decisions |
| MCTS (UCT) | MEDIUM | Medium | No | Works; branching factor is large |
| Q-Learning / Tabular RL | LOW | High | Yes, many games | State space too large |
| Deep RL (PPO/DDQN) | LOW | Very High | Yes, millions of games | Overkill for 2-4 player AI |
| Hybrid RL (academic) | MEDIUM | Very High | Yes | 91% win rate vs fixed-policy — but 6+ months to implement |

**Recommendation: Heuristic core + lightweight Monte Carlo rollouts.**

For a custom Monopoly-style game with 2-4 AI players, this gives strong behavior,
runs in real time, and lets you tune AI personality per agent via config.

Full deep RL is not warranted unless you need adaptive learning against human opponents
over thousands of sessions. The academic hybrid PPO approach (arxiv 2103.00683) achieves
91% win rate, but requires defining a reward function, training loop, and policy network —
months of work beyond core simulation.

---

## 2. Heuristic Agent Design

### Decision Points in a Monopoly-Style Turn

Map each decision to a heuristic function:

```
1. Jail decision     — pay to leave vs. roll for doubles
2. Tile landing      — buy / skip / trigger (properties, events)
3. Build decision    — when to develop owned tiles
4. Mortgage decision — liquidity vs. income tradeoff
5. Bankruptcy check  — sell order when cash < 0
```

### Heuristic Rules (evidence-based from simulations)

```python
def should_buy(player, tile, game_model) -> bool:
    # Buy if: affordable (keep min cash reserve) + tile not overpriced vs. rent ROI
    cost = tile.config["price"]
    reserve = player.effective_stat("min_cash_reserve")  # from skill/pet modifiers
    if player.cash - cost < reserve:
        return False
    roi_turns = cost / max(tile.config["rent"], 1)
    return roi_turns < game_model.rules["buy_roi_threshold"]  # config-tunable

def jail_strategy(player, game_model) -> str:
    # Stay in jail if monopolies are fully developed (reduce landing risk)
    # Leave jail if early game (maximize position coverage)
    threat = compute_opponent_threat(game_model)
    return "pay" if threat > THREAT_THRESHOLD else "roll"
```

### Personality Parameters (per-agent in config)

```yaml
# config/agents.yaml
agents:
  - id: aggressive
    buy_roi_threshold: 20     # buys almost everything
    min_cash_reserve: 200
    risk_tolerance: 0.8
  - id: conservative
    buy_roi_threshold: 10     # only high-ROI tiles
    min_cash_reserve: 500
    risk_tolerance: 0.3
```

This allows varied gameplay between AI agents without separate codepaths.

---

## 3. Monte Carlo Rollouts (Where to Use Them)

Use Monte Carlo rollouts for decisions with **multi-turn consequences** where the
immediate heuristic is uncertain. Specifically:

- **Property buy/skip decision**: Simulate N games from current state; compare
  win rate with vs. without the purchase.
- **Jail timing**: Simulate leaving jail now vs. waiting one turn.

```python
def monte_carlo_buy_eval(player, tile, game_model, n_rollouts=200) -> float:
    """Returns estimated win probability increase from buying this tile."""
    wins_if_buy = 0
    wins_if_skip = 0
    for _ in range(n_rollouts):
        snapshot = game_model.clone()  # deep copy, no Pygame state
        snapshot.players[player.id].buy_tile(tile)
        wins_if_buy += simulate_to_end(snapshot)

    for _ in range(n_rollouts):
        snapshot = game_model.clone()
        wins_if_skip += simulate_to_end(snapshot)

    return (wins_if_buy - wins_if_skip) / n_rollouts
```

For 200 rollouts this runs in under 100ms if `simulate_to_end` is a fast headless
loop (no Pygame, no rendering). **The model must be clonable without Pygame state.**
This is why keeping AI layer separate from rendering is not optional.

---

## 4. Game History Persistence for AI Learning

### What to Store

Store **events, not full state snapshots**. Events are smaller and enable replay.

```python
@dataclass
class TurnRecord:
    game_id: str
    turn: int
    player_id: str
    position_before: int
    position_after: int
    dice_roll: tuple[int, int]
    tile_id: str
    decision: str          # "bought" | "skipped" | "paid_rent" | "drew_card"
    cash_before: int
    cash_after: int
    outcome: str | None    # "won" | "bankrupt" | None (filled at game end)
```

### Storage Backend

Use **SQLite** via Python's built-in `sqlite3`. No external dependencies, portable,
queryable. Do not use pickle — it breaks across Python version upgrades.

```sql
CREATE TABLE turn_log (
    game_id TEXT,
    turn INTEGER,
    player_id TEXT,
    tile_id TEXT,
    decision TEXT,
    cash_before INTEGER,
    cash_after INTEGER,
    outcome TEXT,           -- NULL until game ends
    timestamp REAL
);

CREATE INDEX idx_game_outcome ON turn_log(game_id, outcome);
CREATE INDEX idx_tile_decision ON turn_log(tile_id, decision, outcome);
```

### Learning Query Example

"How often does buying this tile type lead to a win?"

```sql
SELECT decision, outcome, COUNT(*) as freq
FROM turn_log
WHERE tile_id = 'red_district_3'
GROUP BY decision, outcome;
```

Feed these win-rate estimates back into heuristic weights. This is **simple
statistical learning** — no neural network required for meaningful improvement.

### JSON Lines Alternative

If SQLite feels heavy for an initial prototype, append to a `.jsonl` file:

```python
with open("history/games.jsonl", "a") as f:
    f.write(json.dumps(asdict(turn_record)) + "\n")
```

Migrate to SQLite when querying becomes necessary. Start with JSONL, upgrade later.

---

## 5. MCTS Implementation (Optional Upgrade Path)

If heuristic + MC rollouts are not satisfying enough, implement full MCTS.

**Four phases:**
1. **Selection** — walk the tree using UCB1: `wi/ni + C * sqrt(ln(N)/ni)`
2. **Expansion** — add an unvisited child node
3. **Simulation** — fast random playout to game end
4. **Backpropagation** — update win counts up the tree

**Python libraries:**
- `mctspy` (PyPI) — basic implementation, works for small trees
- `jbradberry/mcts` (GitHub) — UCT-based, supports custom game state interfaces

**Branching factor warning:** Standard Monopoly has a high branching factor due to
dice randomness + multiple decision points per turn. Cap tree depth at 3-5 turns and
use `max_rollouts` to bound computation time (e.g., 500ms per AI turn).

---

## 6. Critical AI Pitfalls

### Infinite Game / Stalemate
All Monopoly simulations can loop forever without trading. Mitigation:
- Set `max_turns` in game rules config (e.g., 200 turns).
- Declare winner by highest net worth at turn limit.
- Log stalemate count in history for tuning.

### Action Frequency Imbalance
Rolling dice happens every turn. Buying a property happens ~10% of turns.
Bankruptcy happens ~1% of turns. If you use a single learning mechanism for
all decisions, rare events will be underweighted. Fix: separate decision models
per action type, or use outcome-conditioned win-rate queries per action type.

### Negative Cash Mid-Turn
A player's cash can go negative during an opponent's turn (e.g., collecting from
a card draw). Implement a `resolve_debt(player, game_model)` function that sells
assets in order (buildings → unmortgaged tiles → mortgaged tiles → bankrupt).
Do not assume cash is always >= 0.

### Monopoly Detection
Track whether any player owns all tiles of a group. This changes the rent multiplier
and the AI's jail timing heuristic. Without monopoly detection, AI never learns to
hold jail strategically.

```python
def has_monopoly(player: Player, group_id: str, board: Board) -> bool:
    group_tiles = board.tiles_by_group(group_id)
    return all(t.owner_id == player.id for t in group_tiles)
```

### Passive Buff Stacking Edge Cases
If skills/pendants/pets can stack unbounded, a player may become effectively
immune to rent or have negative rent — guard all resolved values with floor/ceiling:

```python
rent_paid = max(0, base_rent - player.effective_stat("rent_reduction"))
```

---

## Sources

- Hybrid Deep RL for Monopoly (arxiv 2103.00683): https://arxiv.org/abs/2103.00683
- Goldsmith RL approach: https://www.doc.gold.ac.uk/aisb50/AISB50-S02/AISB50-S2-Bailis-paper.pdf
- Intro to MCTS (Jeff Bradberry): https://jeffbradberry.com/posts/2015/09/intro-to-monte-carlo-tree-search/
- mctspy library: https://pypi.org/project/mctspy/
- Monte Carlo Monopoly simulations: https://github.com/edenau/monopoly-monte-carlo
- giogix2/MonopolySimulator: https://github.com/giogix2/MonopolySimulator
