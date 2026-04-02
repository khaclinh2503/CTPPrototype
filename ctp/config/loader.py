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