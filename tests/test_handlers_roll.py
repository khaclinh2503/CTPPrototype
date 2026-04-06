"""Tests for ROLL-trigger skill handlers: SK_XXCT, SK_XE_DO, SK_MOONWALK.

Covers:
- Individual handler outputs (solo activation)
- D-46 combo resolution: XXCT+Moonwalk, XeĐo+Moonwalk, XeĐo overrides XXCT
"""

import pytest
from unittest.mock import MagicMock

from ctp.skills.handlers_roll import (
    handle_xxct,
    handle_xe_do,
    handle_moonwalk,
    resolve_roll_modifiers,
    SKILL_HANDLERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_player(**kwargs):
    """Create a minimal player mock for handler tests."""
    p = MagicMock()
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


def _noop_choose(pool):
    """Stub choose_fn that just returns the pool unchanged."""
    return pool


# ---------------------------------------------------------------------------
# SK_XXCT tests
# ---------------------------------------------------------------------------

class TestHandleXxct:
    def test_dice5_gives_4_5_6(self):
        player = _make_player()
        ctx = {"dice_result": 5}
        result = handle_xxct(player, ctx, MagicMock(), MagicMock())
        assert result["type"] == "dice_modifier"
        assert result["options"] == [4, 5, 6]

    def test_dice2_gives_1_2_3(self):
        """dice-1 should be 1 (no less), dice+1 = 3."""
        player = _make_player()
        ctx = {"dice_result": 2}
        result = handle_xxct(player, ctx, MagicMock(), MagicMock())
        assert result["type"] == "dice_modifier"
        assert result["options"] == [1, 2, 3]

    def test_dice1_minimum_is_1(self):
        """dice_result=1 -> dice-1=max(1,0)=1, so options=[1,2]."""
        player = _make_player()
        ctx = {"dice_result": 1}
        result = handle_xxct(player, ctx, MagicMock(), MagicMock())
        assert result["type"] == "dice_modifier"
        assert 1 in result["options"]
        assert min(result["options"]) >= 1

    def test_registered_in_skill_handlers(self):
        assert "SK_XXCT" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_XXCT"] is handle_xxct


# ---------------------------------------------------------------------------
# SK_XE_DO tests
# ---------------------------------------------------------------------------

class TestHandleXeDo:
    def test_even_dice_gives_even_options(self):
        player = _make_player()
        ctx = {"dice_result": 4}
        result = handle_xe_do(player, ctx, MagicMock(), MagicMock())
        assert result["type"] == "dice_replace"
        assert result["options"] == [2, 4, 6, 8, 10, 12]

    def test_odd_dice_gives_odd_options(self):
        player = _make_player()
        ctx = {"dice_result": 7}
        result = handle_xe_do(player, ctx, MagicMock(), MagicMock())
        assert result["type"] == "dice_replace"
        assert result["options"] == [1, 3, 5, 7, 9, 11]

    def test_dice6_even(self):
        player = _make_player()
        ctx = {"dice_result": 6}
        result = handle_xe_do(player, ctx, MagicMock(), MagicMock())
        assert result["options"] == [2, 4, 6, 8, 10, 12]

    def test_dice1_odd(self):
        player = _make_player()
        ctx = {"dice_result": 1}
        result = handle_xe_do(player, ctx, MagicMock(), MagicMock())
        assert result["options"] == [1, 3, 5, 7, 9, 11]

    def test_registered_in_skill_handlers(self):
        assert "SK_XE_DO" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_XE_DO"] is handle_xe_do


# ---------------------------------------------------------------------------
# SK_MOONWALK tests
# ---------------------------------------------------------------------------

class TestHandleMoonwalk:
    def test_returns_forward_and_backward(self):
        player = _make_player()
        ctx = {"dice_result": 5}
        result = handle_moonwalk(player, ctx, MagicMock(), MagicMock())
        assert result["type"] == "direction_choice"
        assert "forward" in result["options"]
        assert "backward" in result["options"]

    def test_exactly_two_options(self):
        player = _make_player()
        ctx = {"dice_result": 3}
        result = handle_moonwalk(player, ctx, MagicMock(), MagicMock())
        assert len(result["options"]) == 2

    def test_registered_in_skill_handlers(self):
        assert "SK_MOONWALK" in SKILL_HANDLERS
        assert SKILL_HANDLERS["SK_MOONWALK"] is handle_moonwalk


# ---------------------------------------------------------------------------
# resolve_roll_modifiers — D-46 combo tests
# ---------------------------------------------------------------------------

class TestResolveRollModifiers:
    def test_no_modifiers_returns_original_dice(self):
        result = resolve_roll_modifiers([], dice_result=5, choose_fn=_noop_choose)
        assert result["steps"] == [5]
        assert result["directions"] == ["forward"]

    def test_xxct_alone_returns_three_steps(self):
        xxct_result = {"type": "dice_modifier", "options": [4, 5, 6]}
        result = resolve_roll_modifiers([xxct_result], dice_result=5, choose_fn=_noop_choose)
        assert result["steps"] == [4, 5, 6]
        assert result["directions"] == ["forward"]

    def test_moonwalk_alone_keeps_original_dice_adds_backward(self):
        mw_result = {"type": "direction_choice", "options": ["forward", "backward"]}
        result = resolve_roll_modifiers([mw_result], dice_result=5, choose_fn=_noop_choose)
        assert result["steps"] == [5]
        assert result["directions"] == ["forward", "backward"]

    def test_xxct_plus_moonwalk_gives_three_steps_two_dirs(self):
        """D-46: XXCT + Moonwalk → 3 steps × 2 directions = 6 total combos."""
        xxct_result = {"type": "dice_modifier", "options": [4, 5, 6]}
        mw_result = {"type": "direction_choice", "options": ["forward", "backward"]}
        result = resolve_roll_modifiers(
            [xxct_result, mw_result], dice_result=5, choose_fn=_noop_choose
        )
        assert len(result["steps"]) == 3
        assert len(result["directions"]) == 2
        # 6 total combinations
        combos = [(s, d) for s in result["steps"] for d in result["directions"]]
        assert len(combos) == 6

    def test_xe_do_plus_moonwalk_gives_six_steps_two_dirs(self):
        """XeĐo (even) + Moonwalk → 6 steps × 2 directions = 12 total combos."""
        xe_result = {"type": "dice_replace", "options": [2, 4, 6, 8, 10, 12]}
        mw_result = {"type": "direction_choice", "options": ["forward", "backward"]}
        result = resolve_roll_modifiers(
            [xe_result, mw_result], dice_result=4, choose_fn=_noop_choose
        )
        assert len(result["steps"]) == 6
        assert len(result["directions"]) == 2
        # 12 total combinations
        combos = [(s, d) for s in result["steps"] for d in result["directions"]]
        assert len(combos) == 12

    def test_xe_do_overrides_xxct(self):
        """D-46: XeĐo + XXCT → XeĐo wins, XXCT ignored."""
        xxct_result = {"type": "dice_modifier", "options": [3, 4, 5]}
        xe_result = {"type": "dice_replace", "options": [2, 4, 6, 8, 10, 12]}
        result = resolve_roll_modifiers(
            [xxct_result, xe_result], dice_result=4, choose_fn=_noop_choose
        )
        # XeĐo options, not XXCT options
        assert result["steps"] == [2, 4, 6, 8, 10, 12]

    def test_xe_do_overrides_xxct_order_independent(self):
        """XeĐo always overrides XXCT regardless of list order."""
        xxct_result = {"type": "dice_modifier", "options": [3, 4, 5]}
        xe_result = {"type": "dice_replace", "options": [1, 3, 5, 7, 9, 11]}
        # XeĐo first
        result_1 = resolve_roll_modifiers(
            [xe_result, xxct_result], dice_result=3, choose_fn=_noop_choose
        )
        # XXCT first
        result_2 = resolve_roll_modifiers(
            [xxct_result, xe_result], dice_result=3, choose_fn=_noop_choose
        )
        assert result_1["steps"] == result_2["steps"] == [1, 3, 5, 7, 9, 11]

    def test_choose_fn_passed_through(self):
        """choose_fn should be passed through in result."""
        custom_fn = lambda x: x
        result = resolve_roll_modifiers([], dice_result=5, choose_fn=custom_fn)
        assert result["choose_fn"] is custom_fn
