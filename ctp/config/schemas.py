"""Pydantic schemas for CTP game configuration.

This module provides validation schemas for:
- Board.json: Game board layout, space types, and tile configurations
- Card.json: Card definitions (permissive schema)
- skills.yaml: Skill definitions
- pendants.yaml: Pendant definitions
- pets.yaml: Pet definitions
- game_rules.yaml: Game rules
"""

from pydantic import BaseModel, ConfigDict


# =============================================================================
# Board.json Schemas
# =============================================================================


class BuildingLevel(BaseModel):
    """Building level configuration for land tiles."""

    model_config = ConfigDict(extra="forbid")

    build: int  # Cost to build this level
    toll: int   # Rent when opponent lands


class LandTileConfig(BaseModel):
    """Land tile configuration."""

    model_config = ConfigDict(extra="forbid")

    color: int
    building: dict[str, BuildingLevel]  # keys "1"-"5"


class SpacePositionEntry(BaseModel):
    """Entry in SpacePosition defining a tile on the board."""

    model_config = ConfigDict(extra="forbid")

    spaceId: int
    opt: int


class GeneralConfig(BaseModel):
    """General game configuration from Board.json."""

    model_config = ConfigDict(extra="forbid")

    limitTime: int
    limitTurn: int
    actionTimeout: int
    acquireRate: int | float
    sellRate: float
    winReward: float
    defaultHouse: dict[str, dict] | None = None
    tollMultiply: dict[str, dict[str, int]] | None = None
    cardKeepLimit: dict[str, int] | None = None


class PrisonSpaceConfig(BaseModel):
    """Prison space configuration."""

    model_config = ConfigDict(extra="forbid")

    escapeCostRate: float
    limitTurnByMapId: dict[str, int]


class ResortSpaceConfig(BaseModel):
    """Resort space configuration."""

    model_config = ConfigDict(extra="forbid")

    maxUpgrade: int
    initCostRate: float
    increaseRate: int | float
    initCost: int
    tollCost: int


class StartSpaceConfig(BaseModel):
    """Start space configuration."""

    model_config = ConfigDict(extra="forbid")

    passingBonusRate: float


class TaxSpaceConfig(BaseModel):
    """Tax space configuration."""

    model_config = ConfigDict(extra="forbid")

    taxRate: float


class TravelSpaceConfig(BaseModel):
    """Travel space configuration."""

    model_config = ConfigDict(extra="forbid")

    travelCostRate: float


class FestivalSpaceConfig(BaseModel):
    """Festival space configuration."""

    model_config = ConfigDict(extra="forbid")

    holdCostRate: float
    increaseRate: int | float
    maxFestival: int


class FortuneSpaceConfig(BaseModel):
    """Fortune space configuration."""

    model_config = ConfigDict(extra="forbid")

    deckSet: list[str]


class GodSpaceConfig(BaseModel):
    """God space configuration."""

    model_config = ConfigDict(extra="forbid")

    turnLiftActive: int


class BankSpaceConfig(BaseModel):
    """Bank space configuration."""

    model_config = ConfigDict(extra="forbid")

    tollTaxRate: int | float


class BoardConfig(BaseModel):
    """Complete board configuration from Board.json.

    Uses extra="allow" to accommodate SpacePosition1-7 and other maps
    that may exist in the file but are not used in Phase 1.
    """

    model_config = ConfigDict(extra="allow")

    General: GeneralConfig
    SpacePosition0: dict[str, SpacePositionEntry]
    LandSpace: dict[str, dict[str, LandTileConfig]]
    PrisonSpace: PrisonSpaceConfig
    ResortSpace: ResortSpaceConfig
    StartSpace: StartSpaceConfig
    TaxSpace: TaxSpaceConfig
    TravelSpace: TravelSpaceConfig
    FestivalSpace: FestivalSpaceConfig
    FortuneSpace: FortuneSpaceConfig
    GodSpace: GodSpaceConfig
    BankSpace: BankSpaceConfig
    SpacePositionNote: str | None = None
    LandSpaceNote: str | None = None


# =============================================================================
# Card.json Schemas
# =============================================================================


class CardEffect(BaseModel):
    """Individual card effect definition.

    Uses permissive schema since card effects are complex and not fully
    used in Phase 1 (FortuneSpace is a stub).
    """

    model_config = ConfigDict(extra="allow")

    effectId: str | None = None


class CardEntry(BaseModel):
    """Single card entry in Card.json."""

    model_config = ConfigDict(extra="allow")

    contentId: str | None = None
    effect: str | None = None
    isActive: int | None = None
    rate: int | None = None
    mapNotAvail: list[int] | None = None


class CardConfig(BaseModel):
    """Card configuration from Card.json.

    Uses permissive schema to validate the file loads without error.
    Cards are out of Phase 1 scope.
    """

    model_config = ConfigDict(extra="allow")

    Card: dict[str, CardEntry] | None = None


# =============================================================================
# YAML Config Schemas (skills.yaml, pendants.yaml, pets.yaml, game_rules.yaml)
# =============================================================================


class SkillEntry(BaseModel):
    """Individual skill definition."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    stat_deltas: dict[str, float] = {}


class SkillsConfig(BaseModel):
    """Skills configuration."""

    skills: list[SkillEntry] = []


class PendantEntry(BaseModel):
    """Individual pendant definition."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    stat_deltas: dict[str, float] = {}


class PendantsConfig(BaseModel):
    """Pendants configuration."""

    pendants: list[PendantEntry] = []


class PetEntry(BaseModel):
    """Individual pet definition."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    stat_deltas: dict[str, float] = {}


class PetsConfig(BaseModel):
    """Pets configuration."""

    pets: list[PetEntry] = []


class GameRulesConfig(BaseModel):
    """Game rules configuration."""

    model_config = ConfigDict(extra="forbid")

    starting_cash: int | float = 200
    num_players: int = 4