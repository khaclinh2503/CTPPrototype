"""SkillEngine — dispatches skill/pendant/pet triggers with rate-based activation.

D-05: rate_at_star = base_rate + (current_star - min_star) * chance
D-06: random(0, 100) < rate_at_star -> active
D-03: Rank R uses S config
D-40: Pet stamina decrements on activation
D-51: skills_disabled_this_turn blocks all fire() calls
T-02.5-02: Max 10 handlers per fire() call (DoS guard)
"""

import random
from ctp.core.models import Player

_MAX_HANDLERS_PER_FIRE = 10  # T-02.5-02: DoS guard


class SkillEngine:
    """Dispatches skill/pendant/pet triggers for a game session.

    Handler signature: handler(player, ctx, cfg, engine) -> result | None
    - player: the Player whose skill/pendant/pet is firing
    - ctx: dict with board, players, is_player_turn, and any trigger-specific data
    - cfg: the SkillEntry / PendantEntry / PetEntry config object
    - engine: this SkillEngine instance (for cross-skill calls)
    - return None to indicate no effect (skipped from results list)
    """

    def __init__(self, skill_configs, pendant_configs, pet_configs):
        """Initialize SkillEngine with loaded configs.

        Args:
            skill_configs: SkillsConfig instance.
            pendant_configs: PendantsConfig instance.
            pet_configs: PetsConfig instance.
        """
        self.skill_configs = {s.id: s for s in skill_configs.skills}
        self.pendant_configs = {p.id: p for p in pendant_configs.pendants}
        self.pet_configs = {p.id: p for p in pet_configs.pets}
        self._skill_handlers: dict = {}    # skill_id -> handler_fn
        self._pendant_handlers: dict = {}  # pendant_id -> handler_fn
        self._pet_handlers: dict = {}      # pet_id -> handler_fn

    def register_skill(self, skill_id: str, handler) -> None:
        """Register a handler function for a skill.

        Args:
            skill_id: Skill ID (e.g., 'SK_XE_DO').
            handler: Callable(player, ctx, cfg, engine) -> result | None.
        """
        self._skill_handlers[skill_id] = handler

    def register_pendant(self, pendant_id: str, handler) -> None:
        """Register a handler function for a pendant.

        Args:
            pendant_id: Pendant ID (e.g., 'PT_DKXX2').
            handler: Callable(player, ctx, cfg, engine) -> result | None.
        """
        self._pendant_handlers[pendant_id] = handler

    def register_pet(self, pet_id: str, handler) -> None:
        """Register a handler function for a pet.

        Args:
            pet_id: Pet ID (e.g., 'PET_THIEN_THAN').
            handler: Callable(player, ctx, cfg, engine) -> result | None.
        """
        self._pet_handlers[pet_id] = handler

    def calc_rate(self, skill_cfg, player: Player) -> float:
        """Calculate activation rate for a skill at player's current rank/star.

        D-05: rate_at_star = base_rate + (current_star - min_star) * chance
        D-03: Rank R uses S config.
        D-04: If skill has no config for player's rank, return 0.

        Args:
            skill_cfg: SkillEntry config object.
            player: Player to calculate rate for.

        Returns:
            Activation rate as float (0-100 scale).
        """
        rank = player.rank
        if rank == "R":
            rank = "S"  # D-03: R uses S config
        rc = skill_cfg.rank_config.get(rank)
        if rc is None:
            return 0.0  # D-04: no config for this rank
        return rc.base_rate + (player.star - rc.min_star) * rc.chance

    def fire(self, trigger: str, player: Player, ctx: dict) -> list:
        """Fire all skill handlers matching trigger for player.

        D-51: If skills_disabled_this_turn is True, returns empty list.
        T-02.5-02: Max 10 handlers per fire() call (DoS guard).

        Args:
            trigger: Trigger name (e.g., 'ON_ROLL_AFTER').
            player: Player whose skills are being checked.
            ctx: Context dict with board, players, is_player_turn, etc.

        Returns:
            List of non-None results from activated handlers.
        """
        if player.skills_disabled_this_turn:
            return []

        results = []
        fired_count = 0

        for skill_id in player.skills:
            if fired_count >= _MAX_HANDLERS_PER_FIRE:
                break

            cfg = self.skill_configs.get(skill_id)
            if cfg is None:
                continue

            triggers = cfg.trigger if isinstance(cfg.trigger, list) else [cfg.trigger]
            if trigger not in triggers:
                continue

            handler = self._skill_handlers.get(skill_id)
            if handler is None:
                continue

            fired_count += 1

            # Rate check (D-06)
            if cfg.always_active:
                result = handler(player, ctx, cfg, self)
            else:
                rate = self.calc_rate(cfg, player)
                if random.randint(0, 99) < rate:
                    result = handler(player, ctx, cfg, self)
                else:
                    result = None

            if result is not None:
                results.append(result)

        return results

    def fire_pendants(self, trigger: str, player: Player, ctx: dict) -> list:
        """Fire all pendant handlers matching trigger for player.

        Pendants use pendant_rank for rate lookup (D-31).
        D-51: If skills_disabled_this_turn is True, returns empty list.
        T-02.5-02: Max 10 handlers per fire() call (DoS guard).

        Args:
            trigger: Trigger name (e.g., 'ON_LAND_OPPONENT').
            player: Player whose pendants are being checked.
            ctx: Context dict.

        Returns:
            List of non-None results from activated handlers.
        """
        if player.skills_disabled_this_turn:
            return []

        results = []
        fired_count = 0

        for pendant_id in player.pendants:
            if fired_count >= _MAX_HANDLERS_PER_FIRE:
                break

            cfg = self.pendant_configs.get(pendant_id)
            if cfg is None:
                continue
            if trigger not in cfg.triggers:
                continue

            handler = self._pendant_handlers.get(pendant_id)
            if handler is None:
                continue

            fired_count += 1

            if cfg.always_active:
                result = handler(player, ctx, cfg, self)
            else:
                rank = player.pendant_rank
                rate = getattr(cfg.rank_rates, rank, 0)
                if random.randint(0, 99) < rate:
                    result = handler(player, ctx, cfg, self)
                else:
                    result = None

            if result is not None:
                results.append(result)

        return results

    def fire_pet(self, trigger: str, player: Player, ctx: dict):
        """Fire pet handler if trigger matches and stamina > 0.

        D-40: Decrement stamina on activation.
        D-39: Rate based on pet tier.

        Args:
            trigger: Trigger name (e.g., 'ON_CANT_AFFORD_TOLL').
            player: Player whose pet is being checked.
            ctx: Context dict.

        Returns:
            Handler result if pet activated, None otherwise.
        """
        if player.pet is None or player.pet_stamina <= 0:
            return None

        cfg = self.pet_configs.get(player.pet)
        if cfg is None or cfg.trigger != trigger:
            return None

        handler = self._pet_handlers.get(player.pet)
        if handler is None:
            return None

        rate = cfg.tier_rates[player.pet_tier - 1]
        if random.randint(0, 99) < rate:
            player.pet_stamina -= 1  # D-40: decrement on activation
            return handler(player, ctx, cfg, self)

        return None
