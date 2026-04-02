"""Tile strategies for CTP game."""
from ctp.tiles.base import TileStrategy
from ctp.tiles.registry import TileRegistry
from ctp.tiles.land import LandStrategy
from ctp.tiles.resort import ResortStrategy
from ctp.tiles.prison import PrisonStrategy
from ctp.tiles.travel import TravelStrategy
from ctp.tiles.tax import TaxStrategy
from ctp.tiles.start import StartStrategy
from ctp.tiles.festival import FestivalStrategy
from ctp.tiles.fortune import FortuneStrategy
from ctp.tiles.game import GameStrategy
from ctp.tiles.god import GodStrategy
from ctp.tiles.water_slide import WaterSlideStrategy

# Register all strategies using updated SpaceId enum (Phase 2)
from ctp.core.board import SpaceId
TileRegistry.register(SpaceId.CITY, LandStrategy())
TileRegistry.register(SpaceId.RESORT, ResortStrategy())
TileRegistry.register(SpaceId.PRISON, PrisonStrategy())
TileRegistry.register(SpaceId.TRAVEL, TravelStrategy())
TileRegistry.register(SpaceId.TAX, TaxStrategy())
TileRegistry.register(SpaceId.START, StartStrategy())
TileRegistry.register(SpaceId.FESTIVAL, FestivalStrategy())
TileRegistry.register(SpaceId.CHANCE, FortuneStrategy())
TileRegistry.register(SpaceId.GAME, GameStrategy())
TileRegistry.register(SpaceId.GOD, GodStrategy())
TileRegistry.register(SpaceId.WATER_SLIDE, WaterSlideStrategy())

__all__ = [
    "TileStrategy", "TileRegistry",
    "LandStrategy", "ResortStrategy", "PrisonStrategy",
    "TravelStrategy", "TaxStrategy", "StartStrategy",
    "FestivalStrategy", "FortuneStrategy",
    "GameStrategy", "GodStrategy", "WaterSlideStrategy",
]
