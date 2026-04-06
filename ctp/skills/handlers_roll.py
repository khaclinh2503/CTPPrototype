"""ROLL-trigger skill handlers: SK_XXCT, SK_XE_DO, SK_MOONWALK.

ON_ROLL_AFTER trigger — runs after dice result is known.
Handlers return modifier dicts consumed by resolve_roll_modifiers() + FSM (Plan 16).

D-46: XXCT + XeĐo do not combine (XeĐo overrides).
      XXCT + Moonwalk: dice±1 × 2 directions = up to 6 choices.
      XeĐo + Moonwalk: parity set × 2 directions.
"""

from ctp.skills.registry import SKILL_HANDLERS


# ---------------------------------------------------------------------------
# Handler: SK_XXCT — Xúc Xắc Chiến Thuật
# ---------------------------------------------------------------------------

def handle_xxct(player, ctx, cfg, engine):
    """ON_ROLL_AFTER handler for SK_XXCT.

    Returns dice_modifier result: options are [dice-1, dice, dice+1].
    dice-1 minimum is 1 (cannot be 0 or negative).

    ctx keys used:
        dice_result (int): Current dice value.
        choose_fn (callable, optional): AI stub for choosing option.

    Returns:
        dict with type="dice_modifier" and options list.
    """
    dice_result = ctx.get("dice_result", 1)
    minus_one = max(1, dice_result - 1)
    options = sorted({minus_one, dice_result, dice_result + 1})
    return {"type": "dice_modifier", "options": options}


SKILL_HANDLERS["SK_XXCT"] = handle_xxct


# ---------------------------------------------------------------------------
# Handler: SK_XE_DO — Xế Độ
# ---------------------------------------------------------------------------

def handle_xe_do(player, ctx, cfg, engine):
    """ON_ROLL_AFTER handler for SK_XE_DO.

    Returns dice_replace result: same-parity options from 1-12.
    Even dice → {2,4,6,8,10,12}; odd dice → {1,3,5,7,9,11}.

    ctx keys used:
        dice_result (int): Current dice value.

    Returns:
        dict with type="dice_replace" and options list.
    """
    dice_result = ctx.get("dice_result", 1)
    if dice_result % 2 == 0:
        options = [2, 4, 6, 8, 10, 12]
    else:
        options = [1, 3, 5, 7, 9, 11]
    return {"type": "dice_replace", "options": options}


SKILL_HANDLERS["SK_XE_DO"] = handle_xe_do


# ---------------------------------------------------------------------------
# Handler: SK_MOONWALK
# ---------------------------------------------------------------------------

def handle_moonwalk(player, ctx, cfg, engine):
    """ON_ROLL_AFTER handler for SK_MOONWALK.

    Returns direction_choice result: forward or backward movement.
    Backward movement wraps around board and does NOT receive START passing bonus.

    Returns:
        dict with type="direction_choice" and options list.
    """
    return {"type": "direction_choice", "options": ["forward", "backward"]}


SKILL_HANDLERS["SK_MOONWALK"] = handle_moonwalk


# ---------------------------------------------------------------------------
# Combo Resolution — D-46
# ---------------------------------------------------------------------------

def resolve_roll_modifiers(results: list, dice_result: int, choose_fn) -> dict:
    """Merge all active roll modifier results into a single choice pool.

    D-46 combo rules:
    - XXCT + XeĐo: XeĐo overrides XXCT (they do NOT combine).
    - XXCT + Moonwalk: (dice-1/dice/dice+1) x (forward/backward) = up to 6 choices.
    - XeĐo + Moonwalk: parity set x (forward/backward).
    - XeĐo + XXCT: XeĐo wins, XXCT ignored.

    Args:
        results: List of handler result dicts from fire() on ON_ROLL_AFTER.
        dice_result: Original dice value rolled.
        choose_fn: Callable for AI to select from the final pool.

    Returns:
        dict with keys:
            steps (list[int]): Available step counts to choose from.
            directions (list[str]): Available directions ("forward", "backward").
            choose_fn (callable): AI choice function passed through.
    """
    has_xxct = any(r["type"] == "dice_modifier" for r in results)
    has_xe_do = any(r["type"] == "dice_replace" for r in results)
    has_moonwalk = any(r["type"] == "direction_choice" for r in results)

    # Build step pool — XeĐo overrides XXCT per D-46 / GD notes
    if has_xe_do:
        steps = next(r["options"] for r in results if r["type"] == "dice_replace")
    elif has_xxct:
        steps = next(r["options"] for r in results if r["type"] == "dice_modifier")
    else:
        steps = [dice_result]

    directions = ["forward"]
    if has_moonwalk:
        directions = ["forward", "backward"]

    return {"steps": steps, "directions": directions, "choose_fn": choose_fn}
