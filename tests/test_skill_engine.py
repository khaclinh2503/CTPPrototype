"""Unit tests for SkillEngine — D-05, D-03, D-04, D-40, D-51.

Tests:
- calc_rate() with A/S rank, different stars (D-05 formula)
- R rank falls back to S config (D-03)
- D-04: rank without config returns rate 0
- fire() dispatches to registered handler
- skills_disabled_this_turn blocks fire()
- fire_pet() decrements stamina (D-40)
- fire_pet() returns None when stamina=0
- fire_pendants() uses pendant_rank for rate lookup (D-31)
- DoS guard: max 10 handlers per fire() call (T-02.5-02)
"""

import pytest
from unittest.mock import MagicMock, patch

from ctp.skills.engine import SkillEngine
from ctp.core.models import Player
from ctp.config.schemas import (
    RankConfig, SkillEntry, SkillsConfig,
    PendantEntry, PendantsConfig, PendantRankRates,
    PetEntry, PetsConfig,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_rank_config(base_rate: float, chance: float, min_star: int = 1) -> RankConfig:
    return RankConfig(min_star=min_star, base_rate=base_rate, chance=chance)


def _make_skill(skill_id: str, trigger: str, rank_config: dict,
                always_active: bool = False, secondary_rate=None) -> SkillEntry:
    return SkillEntry(
        id=skill_id,
        name=skill_id,
        trigger=trigger,
        rank_config=rank_config,
        always_active=always_active,
        secondary_rate=secondary_rate,
    )


def _make_pendant(pendant_id: str, triggers: list, rank_rates: dict,
                  always_active: bool = False) -> PendantEntry:
    rates = PendantRankRates(**rank_rates)
    return PendantEntry(
        id=pendant_id,
        name=pendant_id,
        triggers=triggers,
        rank_rates=rates,
        always_active=always_active,
    )


def _make_pet(pet_id: str, trigger: str, max_stamina: int, tier_rates: list) -> PetEntry:
    return PetEntry(
        id=pet_id,
        name=pet_id,
        trigger=trigger,
        max_stamina=max_stamina,
        tier_rates=tier_rates,
    )


def _make_engine(skills=None, pendants=None, pets=None) -> SkillEngine:
    skills_cfg = SkillsConfig(skills=skills or [])
    pendants_cfg = PendantsConfig(pendants=pendants or [])
    pets_cfg = PetsConfig(pets=pets or [])
    return SkillEngine(skills_cfg, pendants_cfg, pets_cfg)


def _make_player(rank="A", star=3, skills=None, pendants=None, pet=None,
                 pet_stamina=3, pet_tier=1, pendant_rank="B") -> Player:
    p = Player("p1", 1_000_000)
    p.rank = rank
    p.star = star
    p.skills = skills or []
    p.pendants = pendants or []
    p.pet = pet
    p.pet_stamina = pet_stamina
    p.pet_tier = pet_tier
    p.pendant_rank = pendant_rank
    return p


# ---------------------------------------------------------------------------
# calc_rate() tests
# ---------------------------------------------------------------------------

class TestCalcRate:
    """Tests for D-05: rate_at_star = base_rate + (current_star - min_star) * chance"""

    def test_calc_rate_rank_a_star1(self):
        """A rank, min_star=1, star=1 -> base_rate + 0 = 12.0"""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "A": _make_rank_config(base_rate=12, chance=1, min_star=1),
        })
        engine = _make_engine(skills=[skill])
        player = _make_player(rank="A", star=1)
        assert engine.calc_rate(skill, player) == 12.0

    def test_calc_rate_rank_a_star5(self):
        """A rank, min_star=1, star=5, chance=1 -> 12 + (5-1)*1 = 16.0"""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "A": _make_rank_config(base_rate=12, chance=1, min_star=1),
        })
        engine = _make_engine(skills=[skill])
        player = _make_player(rank="A", star=5)
        assert engine.calc_rate(skill, player) == 16.0

    def test_calc_rate_rank_s_star3(self):
        """S rank, min_star=1, star=3, chance=2 -> 17 + (3-1)*2 = 21.0"""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "S": _make_rank_config(base_rate=17, chance=2, min_star=1),
        })
        engine = _make_engine(skills=[skill])
        player = _make_player(rank="S", star=3)
        assert engine.calc_rate(skill, player) == 21.0

    def test_calc_rate_rank_r_uses_s_config(self):
        """D-03: R rank uses S config. S base_rate=17, chance=2, star=5 -> 17+(5-1)*2=25.0"""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "S": _make_rank_config(base_rate=17, chance=2, min_star=1),
        })
        engine = _make_engine(skills=[skill])
        player = _make_player(rank="R", star=5)
        assert engine.calc_rate(skill, player) == 25.0

    def test_calc_rate_no_config_returns_zero(self):
        """D-04: If skill has no config for player's rank, return 0.0"""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "S": _make_rank_config(base_rate=17, chance=2),
        })
        engine = _make_engine(skills=[skill])
        player = _make_player(rank="B", star=3)  # B not in rank_config
        assert engine.calc_rate(skill, player) == 0.0

    def test_calc_rate_b_rank_skill(self):
        """B rank with B config -> correct rate"""
        skill = _make_skill("SK_MU_PHEP", "ON_PASS_START", {
            "B": _make_rank_config(base_rate=41, chance=2, min_star=1),
        })
        engine = _make_engine(skills=[skill])
        player = _make_player(rank="B", star=5)
        # 41 + (5-1)*2 = 49
        assert engine.calc_rate(skill, player) == 49.0


# ---------------------------------------------------------------------------
# fire() tests
# ---------------------------------------------------------------------------

class TestFire:
    """Tests for SkillEngine.fire() dispatch."""

    def test_fire_dispatches_to_registered_handler(self):
        """fire() calls registered handler when trigger matches and rate check passes."""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "A": _make_rank_config(base_rate=100, chance=0),  # 100% rate
        })
        engine = _make_engine(skills=[skill])
        handler = MagicMock(return_value={"result": "ok"})
        engine.register_skill("SK_TEST", handler)

        player = _make_player(rank="A", star=1, skills=["SK_TEST"])
        ctx = {"board": None, "players": [], "is_player_turn": True}

        results = engine.fire("ON_ROLL_AFTER", player, ctx)
        assert len(results) == 1
        assert results[0] == {"result": "ok"}
        handler.assert_called_once()

    def test_fire_does_not_dispatch_wrong_trigger(self):
        """fire() does not call handler when trigger doesn't match."""
        skill = _make_skill("SK_TEST", "ON_LAND", {
            "A": _make_rank_config(base_rate=100, chance=0),
        })
        engine = _make_engine(skills=[skill])
        handler = MagicMock(return_value="activated")
        engine.register_skill("SK_TEST", handler)

        player = _make_player(rank="A", star=1, skills=["SK_TEST"])
        ctx = {}

        results = engine.fire("ON_ROLL_AFTER", player, ctx)
        assert results == []
        handler.assert_not_called()

    def test_fire_blocked_when_skills_disabled(self):
        """D-51: skills_disabled_this_turn=True blocks all fire() calls."""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "A": _make_rank_config(base_rate=100, chance=0),
        })
        engine = _make_engine(skills=[skill])
        handler = MagicMock(return_value="activated")
        engine.register_skill("SK_TEST", handler)

        player = _make_player(rank="A", star=1, skills=["SK_TEST"])
        player.skills_disabled_this_turn = True
        ctx = {}

        results = engine.fire("ON_ROLL_AFTER", player, ctx)
        assert results == []
        handler.assert_not_called()

    def test_fire_rate_zero_handler_not_called(self):
        """fire() does not call handler when rate=0 (D-04 no config)."""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "S": _make_rank_config(base_rate=100, chance=0),
        })
        engine = _make_engine(skills=[skill])
        handler = MagicMock(return_value="activated")
        engine.register_skill("SK_TEST", handler)

        player = _make_player(rank="B", star=3, skills=["SK_TEST"])  # B not in config
        ctx = {}

        results = engine.fire("ON_ROLL_AFTER", player, ctx)
        assert results == []

    def test_fire_always_active_skips_rate_check(self):
        """always_active=True skill always fires regardless of rate formula."""
        skill = _make_skill("SK_MU_PHEP", "ON_PASS_START", {
            "B": _make_rank_config(base_rate=0, chance=0),  # rate=0 but always_active
        }, always_active=True)
        engine = _make_engine(skills=[skill])
        handler = MagicMock(return_value="always_fired")
        engine.register_skill("SK_MU_PHEP", handler)

        player = _make_player(rank="B", star=1, skills=["SK_MU_PHEP"])
        ctx = {}

        results = engine.fire("ON_PASS_START", player, ctx)
        assert len(results) == 1
        handler.assert_called_once()

    def test_fire_handler_returns_none_excluded(self):
        """Handler returning None is excluded from results list."""
        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "A": _make_rank_config(base_rate=100, chance=0),
        })
        engine = _make_engine(skills=[skill])
        handler = MagicMock(return_value=None)
        engine.register_skill("SK_TEST", handler)

        player = _make_player(rank="A", star=1, skills=["SK_TEST"])
        ctx = {}

        results = engine.fire("ON_ROLL_AFTER", player, ctx)
        assert results == []

    def test_fire_dos_guard_max_10_handlers(self):
        """T-02.5-02: Max 10 handlers fired per fire() call."""
        # Create 15 skills, all with 100% rate
        skills = [
            _make_skill(f"SK_{i}", "ON_ROLL_AFTER", {
                "A": _make_rank_config(base_rate=100, chance=0),
            })
            for i in range(15)
        ]
        engine = _make_engine(skills=skills)
        call_count = [0]

        def handler(player, ctx, cfg, eng):
            call_count[0] += 1
            return "fired"

        for sk in skills:
            engine.register_skill(sk.id, handler)

        # Player has all 15 skills (via direct list, bypassing 5-slot limit)
        player = _make_player(rank="A", star=1, skills=[f"SK_{i}" for i in range(15)])
        ctx = {}

        results = engine.fire("ON_ROLL_AFTER", player, ctx)
        assert call_count[0] == 10, f"Expected 10, got {call_count[0]}"
        assert len(results) == 10


# ---------------------------------------------------------------------------
# fire_pet() tests
# ---------------------------------------------------------------------------

class TestFirePet:
    """Tests for SkillEngine.fire_pet() — D-40."""

    def test_fire_pet_decrements_stamina(self):
        """D-40: pet_stamina decrements by 1 on activation."""
        pet = _make_pet("PET_TEST", "ON_CANT_AFFORD_TOLL", max_stamina=3, tier_rates=[100, 100, 100, 100, 100])
        engine = _make_engine(pets=[pet])
        handler = MagicMock(return_value="pet_fired")
        engine.register_pet("PET_TEST", handler)

        player = _make_player(pet="PET_TEST", pet_stamina=3, pet_tier=1)
        ctx = {}

        result = engine.fire_pet("ON_CANT_AFFORD_TOLL", player, ctx)
        assert result == "pet_fired"
        assert player.pet_stamina == 2  # decremented

    def test_fire_pet_returns_none_when_stamina_zero(self):
        """D-40: pet does not fire when stamina=0."""
        pet = _make_pet("PET_TEST", "ON_CANT_AFFORD_TOLL", max_stamina=3, tier_rates=[100, 100, 100, 100, 100])
        engine = _make_engine(pets=[pet])
        handler = MagicMock(return_value="pet_fired")
        engine.register_pet("PET_TEST", handler)

        player = _make_player(pet="PET_TEST", pet_stamina=0, pet_tier=1)
        ctx = {}

        result = engine.fire_pet("ON_CANT_AFFORD_TOLL", player, ctx)
        assert result is None
        handler.assert_not_called()

    def test_fire_pet_wrong_trigger_returns_none(self):
        """fire_pet() returns None if trigger doesn't match pet's trigger."""
        pet = _make_pet("PET_TEST", "ON_CANT_AFFORD_TOLL", max_stamina=3, tier_rates=[100, 100, 100, 100, 100])
        engine = _make_engine(pets=[pet])
        handler = MagicMock(return_value="pet_fired")
        engine.register_pet("PET_TEST", handler)

        player = _make_player(pet="PET_TEST", pet_stamina=3, pet_tier=1)
        ctx = {}

        result = engine.fire_pet("ON_ROLL_AFTER", player, ctx)
        assert result is None
        handler.assert_not_called()

    def test_fire_pet_uses_tier_rate(self):
        """D-39: Pet uses tier_rates[pet_tier - 1] for rate check."""
        # tier_rates[2] = 0% (tier 3)
        pet = _make_pet("PET_TEST", "ON_CANT_AFFORD_TOLL", max_stamina=3, tier_rates=[0, 0, 0, 0, 0])
        engine = _make_engine(pets=[pet])
        handler = MagicMock(return_value="pet_fired")
        engine.register_pet("PET_TEST", handler)

        player = _make_player(pet="PET_TEST", pet_stamina=3, pet_tier=3)
        ctx = {}

        result = engine.fire_pet("ON_CANT_AFFORD_TOLL", player, ctx)
        assert result is None
        handler.assert_not_called()
        assert player.pet_stamina == 3  # no decrement when rate=0

    def test_fire_pet_no_pet_returns_none(self):
        """fire_pet() returns None if player has no pet."""
        engine = _make_engine()
        player = _make_player(pet=None)
        ctx = {}

        result = engine.fire_pet("ON_CANT_AFFORD_TOLL", player, ctx)
        assert result is None


# ---------------------------------------------------------------------------
# fire_pendants() tests
# ---------------------------------------------------------------------------

class TestFirePendants:
    """Tests for SkillEngine.fire_pendants() — D-31."""

    def test_fire_pendants_uses_pendant_rank(self):
        """D-31: Pendants use pendant_rank for rate lookup."""
        pendant = _make_pendant("PT_TEST", ["ON_LAND_OPPONENT"], {
            "B": 100, "A": 0, "S": 0, "R": 0, "SR": 0
        })
        engine = _make_engine(pendants=[pendant])
        handler = MagicMock(return_value="pendant_fired")
        engine.register_pendant("PT_TEST", handler)

        # pendant_rank="B" -> rate=100 -> should fire
        player = _make_player(pendants=["PT_TEST"], pendant_rank="B")
        ctx = {}

        results = engine.fire_pendants("ON_LAND_OPPONENT", player, ctx)
        assert len(results) == 1

    def test_fire_pendants_wrong_rank_not_fire(self):
        """Pendant with rate=0 at player's pendant_rank does not fire."""
        pendant = _make_pendant("PT_TEST", ["ON_LAND_OPPONENT"], {
            "B": 0, "A": 0, "S": 0, "R": 0, "SR": 100  # only SR fires
        })
        engine = _make_engine(pendants=[pendant])
        handler = MagicMock(return_value="pendant_fired")
        engine.register_pendant("PT_TEST", handler)

        player = _make_player(pendants=["PT_TEST"], pendant_rank="B")
        ctx = {}

        results = engine.fire_pendants("ON_LAND_OPPONENT", player, ctx)
        assert results == []

    def test_fire_pendants_blocked_when_skills_disabled(self):
        """D-51: skills_disabled_this_turn blocks fire_pendants() too."""
        pendant = _make_pendant("PT_TEST", ["ON_LAND_OPPONENT"], {
            "B": 100, "A": 100, "S": 100, "R": 100, "SR": 100
        })
        engine = _make_engine(pendants=[pendant])
        handler = MagicMock(return_value="pendant_fired")
        engine.register_pendant("PT_TEST", handler)

        player = _make_player(pendants=["PT_TEST"], pendant_rank="SR")
        player.skills_disabled_this_turn = True
        ctx = {}

        results = engine.fire_pendants("ON_LAND_OPPONENT", player, ctx)
        assert results == []
        handler.assert_not_called()

    def test_fire_pendants_wrong_trigger_not_fire(self):
        """fire_pendants() skips pendant if trigger doesn't match."""
        pendant = _make_pendant("PT_TEST", ["ON_LAND_TRAVEL"], {
            "B": 100, "A": 100, "S": 100, "R": 100, "SR": 100
        })
        engine = _make_engine(pendants=[pendant])
        handler = MagicMock(return_value="pendant_fired")
        engine.register_pendant("PT_TEST", handler)

        player = _make_player(pendants=["PT_TEST"], pendant_rank="SR")
        ctx = {}

        results = engine.fire_pendants("ON_LAND_OPPONENT", player, ctx)
        assert results == []


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestRegistry:
    """Tests for ctp.skills.registry module."""

    def test_register_all(self):
        """register_all() populates engine with all handlers from registry dicts."""
        from ctp.skills.registry import SKILL_HANDLERS, PENDANT_HANDLERS, PET_HANDLERS, register_all

        skill = _make_skill("SK_TEST", "ON_ROLL_AFTER", {
            "A": _make_rank_config(base_rate=50, chance=1),
        })
        engine = _make_engine(skills=[skill])

        # Temporarily add to registry
        original_skills = dict(SKILL_HANDLERS)
        try:
            SKILL_HANDLERS["SK_TEST"] = lambda p, c, cfg, e: "ok"
            register_all(engine)
            assert "SK_TEST" in engine._skill_handlers
        finally:
            SKILL_HANDLERS.clear()
            SKILL_HANDLERS.update(original_skills)
