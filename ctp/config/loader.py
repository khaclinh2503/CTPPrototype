"""ConfigLoader - loads and validates all CTP configuration files.

This module provides the ConfigLoader class that loads Board.json, Card.json,
and all YAML config files at startup. It validates each file against its
Pydantic schema and raises ConfigError if any validation fails.
"""

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from ctp.config.exceptions import ConfigError
from ctp.config.schemas import (
    BoardConfig,
    CardConfig,
    GameRulesConfig,
    PetsConfig,
    PendantsConfig,
    SkillsConfig,
)


class ConfigLoader:
    """Loads and validates all config files at startup.

    Raises ConfigError if any schema validation fails.

    Attributes:
        config_dir: Path to the configuration directory.
        board: Loaded BoardConfig instance.
        card: Loaded CardConfig instance (optional, for future use).
        game_rules: Loaded GameRulesConfig instance.
        skills: Loaded SkillsConfig instance.
        pendants: Loaded PendantsConfig instance.
        pets: Loaded PetsConfig instance.
    """

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize ConfigLoader.

        Args:
            config_dir: Path to the config directory. Defaults to ctp/config/.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent  # ctp/config/
        self.config_dir = Path(config_dir)
        self.board: BoardConfig | None = None
        self.card: CardConfig | None = None
        self.game_rules: GameRulesConfig | None = None
        self.skills: SkillsConfig | None = None
        self.pendants: PendantsConfig | None = None
        self.pets: PetsConfig | None = None

    def load_all(self) -> None:
        """Load and validate all config files.

        Raises ConfigError on the first failure.

        This method loads:
        - Board.json: Game board configuration
        - game_rules.yaml: General game rules
        - skills.yaml: Skill definitions
        - pendants.yaml: Pendant definitions
        - pets.yaml: Pet definitions
        """
        self.board = self._load_board()
        self.card = self._load_card()
        self.game_rules = self._load_yaml("game_rules.yaml", GameRulesConfig)
        self.skills = self._load_yaml("skills.yaml", SkillsConfig)
        self.pendants = self._load_yaml("pendants.yaml", PendantsConfig)
        self.pets = self._load_yaml("pets.yaml", PetsConfig)

    def _load_board(self) -> BoardConfig:
        """Load and validate Board.json."""
        board_path = self.config_dir / "Board.json"
        try:
            with open(board_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return BoardConfig.model_validate(data)
        except FileNotFoundError:
            raise ConfigError(f"Board config not found: {board_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {board_path}: {e}")
        except ValidationError as e:
            raise ConfigError(f"Board config validation failed: {e}")

    def _load_card(self) -> CardConfig:
        """Load and validate Card.json.

        Note: Card.json uses a permissive schema since card effects
        are not implemented in Phase 1.
        """
        card_path = self.config_dir / "Card.json"
        try:
            with open(card_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CardConfig.model_validate(data)
        except FileNotFoundError:
            raise ConfigError(f"Card config not found: {card_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {card_path}: {e}")
        except ValidationError as e:
            raise ConfigError(f"Card config validation failed: {e}")

    def _load_yaml(self, filename: str, schema_class) -> BaseModel:
        """Load and validate a YAML config file."""
        yaml_path = self.config_dir / filename
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return schema_class.model_validate(data)
        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {yaml_path}")
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {yaml_path}: {e}")
        except ValidationError as e:
            raise ConfigError(f"Config validation failed for {filename}: {e}")

    @property
    def board_config(self) -> "BoardConfig":
        """Get BoardConfig (alias for self.board)."""
        assert self.board is not None, "Call load_all() first"
        return self.board

    @property
    def skills_config(self) -> "SkillsConfig":
        """Get SkillsConfig."""
        assert self.skills is not None, "Call load_all() first"
        return self.skills

    @property
    def pendants_config(self) -> "PendantsConfig":
        """Get PendantsConfig."""
        assert self.pendants is not None, "Call load_all() first"
        return self.pendants

    @property
    def pets_config(self) -> "PetsConfig":
        """Get PetsConfig."""
        assert self.pets is not None, "Call load_all() first"
        return self.pets

    @property
    def max_turns(self) -> int:
        """Get General.limitTurn from Board.json (max turns per game)."""
        assert self.board is not None, "Call load_all() first"
        return self.board.General.limitTurn

    @property
    def sell_rate(self) -> float:
        """Get General.sellRate from Board.json (property sell discount)."""
        assert self.board is not None, "Call load_all() first"
        return self.board.General.sellRate

    @property
    def acquire_rate(self) -> float:
        """Get General.acquireRate from Board.json (property acquisition rate)."""
        assert self.board is not None, "Call load_all() first"
        return float(self.board.General.acquireRate)

    @property
    def starting_cash(self) -> float:
        """Get starting_cash from game_rules.yaml."""
        assert self.game_rules is not None, "Call load_all() first"
        return float(self.game_rules.starting_cash)

    @property
    def num_players(self) -> int:
        """Get num_players from game_rules.yaml."""
        assert self.game_rules is not None, "Call load_all() first"
        return self.game_rules.num_players


def assign_random_loadout(players, skills_cfg, pendants_cfg, pets_cfg, rng=None):
    """D-16/D-34/D-41: Random assignment with replacement.

    D-20: SK_TEDDY and SK_GAY_NHU_Y mutually exclusive — re-roll on conflict.

    Args:
        players: List of Player objects to assign loadout to.
        skills_cfg: SkillsConfig instance.
        pendants_cfg: PendantsConfig instance.
        pets_cfg: PetsConfig instance.
        rng: Optional random module (default: stdlib random).
    """
    import random as _rng_module
    if rng is None:
        rng = _rng_module

    for p in players:
        # Skills: 5 slots, with replacement, mutual exclusion D-20
        # D-04: only include skills that have rank_config for player's rank
        # D-03: R rank uses S config
        effective_rank = "S" if p.rank == "R" else p.rank
        pool = [
            s.id for s in skills_cfg.skills
            if effective_rank in s.rank_config
        ]
        if not pool:
            p.skills = []
        else:
            p.skills = []
            for _ in range(5):
                candidate = rng.choice(pool)
                # D-20 mutual exclusion: SK_TEDDY and SK_GAY_NHU_Y cannot coexist
                if candidate == "SK_TEDDY" and "SK_GAY_NHU_Y" in p.skills:
                    non_teddy = [x for x in pool if x != "SK_TEDDY"]
                    candidate = rng.choice(non_teddy) if non_teddy else candidate
                elif candidate == "SK_GAY_NHU_Y" and "SK_TEDDY" in p.skills:
                    non_gay_nhu_y = [x for x in pool if x != "SK_GAY_NHU_Y"]
                    candidate = rng.choice(non_gay_nhu_y) if non_gay_nhu_y else candidate
                p.skills.append(candidate)

        # Pendants: 3 slots, with replacement
        pendant_pool = [pt.id for pt in pendants_cfg.pendants]
        if pendant_pool:
            p.pendants = [rng.choice(pendant_pool) for _ in range(3)]
        else:
            p.pendants = []
        p.pendant_rank = rng.choice(["B", "A", "S", "R", "SR"])

        # Pet: 1 slot, random tier
        if pets_cfg.pets:
            pet = rng.choice(pets_cfg.pets)
            p.pet = pet.id
            p.pet_tier = rng.randint(1, 5)
            p.pet_stamina = pet.max_stamina
        else:
            p.pet = None
            p.pet_tier = 1
            p.pet_stamina = 0