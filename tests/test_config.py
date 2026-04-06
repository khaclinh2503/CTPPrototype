"""Tests for CTP configuration loading and validation."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

# Get the ctp/config directory path
CONFIG_DIR = Path(__file__).parent.parent / "ctp" / "config"


# =============================================================================
# Task 1: Pydantic Schema Tests
# =============================================================================


class TestBoardConfigSchemas:
    """Test Board.json validation against Pydantic schemas."""

    def test_board_config_loads_successfully(self):
        """BoardConfig.model_validate(json.load(Board.json)) succeeds without error."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should not raise
        config = BoardConfig.model_validate(data)
        assert config is not None
        assert config.General is not None

    def test_general_config_fields(self):
        """BoardConfig validates General section fields."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = BoardConfig.model_validate(data)

        assert config.General.limitTurn == 25
        assert config.General.sellRate == 0.5
        assert config.General.acquireRate == 1
        assert config.General.winReward == 0.9

    def test_space_position_count(self):
        """BoardConfig validates SpacePosition0 has 32 entries."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = BoardConfig.model_validate(data)

        assert len(config.SpacePosition0) == 32

        # Check first entry has spaceId and opt
        entry1 = config.SpacePosition0["1"]
        assert entry1.spaceId == 7  # Start space
        assert entry1.opt == 0

    def test_land_space_structure(self):
        """BoardConfig validates LandSpace structure with colors and buildings."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = BoardConfig.model_validate(data)

        # Check LandSpace["1"]["1"] has color and building dict with keys "1"-"5"
        land1 = config.LandSpace["1"]["1"]
        assert land1.color == 1
        assert "1" in land1.building
        assert "2" in land1.building
        assert "3" in land1.building
        assert "4" in land1.building
        assert "5" in land1.building

        # Check building level has build and toll
        bld1 = land1.building["1"]
        assert bld1.build == 10
        assert bld1.toll == 1

    def test_prison_space_config(self):
        """BoardConfig validates PrisonSpace has escapeCostRate and limitTurnByMapId."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = BoardConfig.model_validate(data)

        assert config.PrisonSpace.escapeCostRate == 0.05
        assert config.PrisonSpace.limitTurnByMapId["1"] == 3

    def test_resort_space_config(self):
        """BoardConfig validates ResortSpace has maxUpgrade=3 and other fields."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = BoardConfig.model_validate(data)

        assert config.ResortSpace.maxUpgrade == 3
        assert config.ResortSpace.initCostRate == 0.1
        assert config.ResortSpace.increaseRate == 2
        assert config.ResortSpace.initCost == 50
        assert config.ResortSpace.tollCost == 40


class TestBoardConfigValidation:
    """Test Board.json validation errors."""

    def test_missing_general_raises_validation_error(self):
        """A modified Board.json missing 'General' raises ValidationError."""
        from ctp.config.schemas import BoardConfig

        # Create invalid data without General
        invalid_data = {
            "SpacePosition0": {"1": {"spaceId": 7, "opt": 0}},
            "LandSpace": {},
            "PrisonSpace": {"escapeCostRate": 0.1, "limitTurnByMapId": {}},
            "ResortSpace": {"maxUpgrade": 3, "initCostRate": 0.1, "increaseRate": 2, "initCost": 50, "tollCost": 40},
            "StartSpace": {"passingBonusRate": 0.15},
            "TaxSpace": {"taxRate": 0.1},
            "TravelSpace": {"travelCostRate": 0.02},
            "FestivalSpace": {"holdCostRate": 0.02, "increaseRate": 2, "maxFestival": 1},
            "FortuneSpace": {"deckSet": []},
            "GodSpace": {"turnLiftActive": 2},
            "BankSpace": {"tollTaxRate": 10},
        }

        with pytest.raises(ValidationError) as exc_info:
            BoardConfig.model_validate(invalid_data)

        assert "General" in str(exc_info.value)

    def test_invalid_limit_turn_type_raises_validation_error(self):
        """A modified Board.json with limitTurn as string raises ValidationError."""
        from ctp.config.schemas import BoardConfig

        board_path = CONFIG_DIR / "Board.json"
        with open(board_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Corrupt limitTurn to be a string
        data["General"]["limitTurn"] = "not_a_number"

        with pytest.raises(ValidationError) as exc_info:
            BoardConfig.model_validate(data)

        assert "limitTurn" in str(exc_info.value)


class TestCardConfig:
    """Test Card.json validation."""

    def test_card_config_loads_successfully(self):
        """CardConfig.model_validate(json.load(Card.json)) succeeds without error."""
        from ctp.config.schemas import CardConfig

        card_path = CONFIG_DIR / "Card.json"
        with open(card_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should not raise
        config = CardConfig.model_validate(data)
        assert config is not None
        assert config.Card is not None


class TestYamlConfigs:
    """Test skeleton YAML configs validation."""

    def test_skills_config_validates(self):
        """SkillsConfig.model_validate(yaml.safe_load(skills.yaml)) succeeds with 26 skills."""
        from ctp.config.schemas import SkillsConfig

        skills_path = CONFIG_DIR / "skills.yaml"
        with open(skills_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = SkillsConfig.model_validate(data)
        assert config is not None
        assert len(config.skills) == 26, f"Expected 26 skills, got {len(config.skills)}"
        skill_ids = {s.id for s in config.skills}
        assert "SK_XE_DO" in skill_ids
        assert "SK_XXCT" in skill_ids
        assert "SK_MU_PHEP" in skill_ids

    def test_pendants_config_validates(self):
        """PendantsConfig.model_validate(yaml.safe_load(pendants.yaml)) succeeds with 12 pendants."""
        from ctp.config.schemas import PendantsConfig

        pendants_path = CONFIG_DIR / "pendants.yaml"
        with open(pendants_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = PendantsConfig.model_validate(data)
        assert config is not None
        assert len(config.pendants) == 12, f"Expected 12 pendants, got {len(config.pendants)}"
        pendant_ids = {p.id for p in config.pendants}
        assert "PT_DKXX2" in pendant_ids
        assert "PT_CUOP_NHA" in pendant_ids

    def test_pets_config_validates(self):
        """PetsConfig.model_validate(yaml.safe_load(pets.yaml)) succeeds with 4 pets."""
        from ctp.config.schemas import PetsConfig

        pets_path = CONFIG_DIR / "pets.yaml"
        with open(pets_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = PetsConfig.model_validate(data)
        assert config is not None
        assert len(config.pets) == 4, f"Expected 4 pets, got {len(config.pets)}"
        pet_ids = {p.id for p in config.pets}
        assert "PET_THIEN_THAN" in pet_ids
        assert "PET_TROI_CHAN" in pet_ids

    def test_game_rules_config_validates(self):
        """GameRulesConfig.model_validate(yaml.safe_load(game_rules.yaml)) succeeds."""
        from ctp.config.schemas import GameRulesConfig

        rules_path = CONFIG_DIR / "game_rules.yaml"
        with open(rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = GameRulesConfig.model_validate(data)
        assert config is not None
        assert config.starting_cash == 1_000_000  # Updated in Phase 2 (was 200)
        assert config.num_players == 4


# =============================================================================
# Task 2: ConfigLoader Tests
# =============================================================================


class TestConfigLoader:
    """Test ConfigLoader class functionality."""

    def test_config_loader_loads_all(self):
        """ConfigLoader().load_all() succeeds, loader.board is not None."""
        from ctp.config import ConfigLoader

        loader = ConfigLoader()
        loader.load_all()

        assert loader.board is not None
        assert loader.game_rules is not None
        assert loader.skills is not None
        assert loader.pendants is not None
        assert loader.pets is not None

    def test_config_loader_max_turns(self):
        """After load_all, loader.max_turns == 25."""
        from ctp.config import ConfigLoader

        loader = ConfigLoader()
        loader.load_all()

        assert loader.max_turns == 25

    def test_config_loader_sell_rate(self):
        """After load_all, loader.sell_rate == 0.5."""
        from ctp.config import ConfigLoader

        loader = ConfigLoader()
        loader.load_all()

        assert loader.sell_rate == 0.5

    def test_config_loader_acquire_rate(self):
        """After load_all, loader.acquire_rate == 1.0."""
        from ctp.config import ConfigLoader

        loader = ConfigLoader()
        loader.load_all()

        assert loader.acquire_rate == 1.0

    def test_config_loader_starting_cash(self):
        """After load_all, loader.starting_cash == 1_000_000 (updated Phase 2)."""
        from ctp.config import ConfigLoader

        loader = ConfigLoader()
        loader.load_all()

        assert loader.starting_cash == 1_000_000

    def test_config_loader_num_players(self):
        """After load_all, loader.num_players == 4."""
        from ctp.config import ConfigLoader

        loader = ConfigLoader()
        loader.load_all()

        assert loader.num_players == 4


class TestConfigLoaderErrors:
    """Test ConfigLoader error handling."""

    def test_config_loader_missing_board(self):
        """Create a ConfigLoader pointing to empty tmpdir, call load_all(),
        assert raises ConfigError with 'not found' in message."""
        from ctp.config import ConfigError, ConfigLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(tmpdir)

            with pytest.raises(ConfigError) as exc_info:
                loader.load_all()

            assert "not found" in str(exc_info.value).lower()

    def test_config_loader_invalid_board_json(self):
        """Write invalid JSON to tmpdir/Board.json, assert raises ConfigError."""
        from ctp.config import ConfigError, ConfigLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write invalid JSON
            board_path = Path(tmpdir) / "Board.json"
            board_path.write_text("{ invalid json }")

            # Also create minimal YAML files to avoid those errors
            (Path(tmpdir) / "game_rules.yaml").write_text("starting_cash: 200\nnum_players: 4")
            (Path(tmpdir) / "skills.yaml").write_text("skills: []")
            (Path(tmpdir) / "pendants.yaml").write_text("pendants: []")
            (Path(tmpdir) / "pets.yaml").write_text("pets: []")

            loader = ConfigLoader(tmpdir)

            with pytest.raises(ConfigError) as exc_info:
                loader.load_all()

            assert "json" in str(exc_info.value).lower() or "decode" in str(exc_info.value).lower()

    def test_config_loader_invalid_board_schema(self):
        """Write valid JSON but missing required fields, assert raises ConfigError."""
        from ctp.config import ConfigError, ConfigLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write minimal valid JSON but missing required fields
            invalid_board = {
                "SpacePosition0": {"1": {"spaceId": 7, "opt": 0}},
                # Missing: General, LandSpace, PrisonSpace, etc.
            }
            board_path = Path(tmpdir) / "Board.json"
            with open(board_path, "w") as f:
                json.dump(invalid_board, f)

            # Also create minimal YAML files
            (Path(tmpdir) / "game_rules.yaml").write_text("starting_cash: 200\nnum_players: 4")
            (Path(tmpdir) / "skills.yaml").write_text("skills: []")
            (Path(tmpdir) / "pendants.yaml").write_text("pendants: []")
            (Path(tmpdir) / "pets.yaml").write_text("pets: []")

            loader = ConfigLoader(tmpdir)

            with pytest.raises(ConfigError) as exc_info:
                loader.load_all()

            assert "validation" in str(exc_info.value).lower() or "general" in str(exc_info.value).lower()

    def test_config_loader_invalid_yaml(self):
        """Write invalid YAML for game_rules, assert raises ConfigError."""
        from ctp.config import ConfigError, ConfigLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid Board.json
            board_path = Path(tmpdir) / "Board.json"
            board_data = {
                "General": {
                    "limitTime": 1500,
                    "limitTurn": 25,
                    "actionTimeout": 15,
                    "acquireRate": 1,
                    "sellRate": 0.5,
                    "winReward": 0.9
                },
                "SpacePosition0": {},
                "LandSpace": {},
                "PrisonSpace": {"escapeCostRate": 0.1, "limitTurnByMapId": {}},
                "ResortSpace": {"maxUpgrade": 3, "initCostRate": 0.1, "increaseRate": 2, "initCost": 50, "tollCost": 40},
                "StartSpace": {"passingBonusRate": 0.15},
                "TaxSpace": {"taxRate": 0.1},
                "TravelSpace": {"travelCostRate": 0.02},
                "FestivalSpace": {"holdCostRate": 0.02, "increaseRate": 2, "maxFestival": 1},
                "FortuneSpace": {"deckSet": []},
                "GodSpace": {"turnLiftActive": 2},
                "BankSpace": {"tollTaxRate": 10},
            }
            with open(board_path, "w") as f:
                json.dump(board_data, f)

            # Write invalid YAML
            rules_path = Path(tmpdir) / "game_rules.yaml"
            rules_path.write_text("starting_cash: !!invalid yaml")

            # Create other valid YAMLs
            (Path(tmpdir) / "skills.yaml").write_text("skills: []")
            (Path(tmpdir) / "pendants.yaml").write_text("pendants: []")
            (Path(tmpdir) / "pets.yaml").write_text("pets: []")

            # Create valid Card.json
            card_path = Path(tmpdir) / "Card.json"
            card_data = {"Card": {}}
            with open(card_path, "w") as f:
                json.dump(card_data, f)

            loader = ConfigLoader(tmpdir)

            with pytest.raises(ConfigError) as exc_info:
                loader.load_all()

            assert "yaml" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()