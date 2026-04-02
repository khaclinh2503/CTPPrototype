"""TileRegistry maps SpaceId to TileStrategy instances."""

from ctp.core.board import SpaceId


class TileRegistry:
    """Maps SpaceId to TileStrategy instances.

    This registry allows the game controller to resolve tile effects
    by looking up the appropriate strategy for each tile type.
    """

    _strategies: dict[SpaceId, 'TileStrategy'] = {}

    @classmethod
    def register(cls, space_id: SpaceId, strategy: 'TileStrategy') -> None:
        """Register a strategy for a space type.

        Args:
            space_id: The SpaceId to register for.
            strategy: The TileStrategy instance to use.
        """
        cls._strategies[space_id] = strategy

    @classmethod
    def resolve(cls, space_id: SpaceId) -> 'TileStrategy':
        """Get the strategy for a space type.

        Args:
            space_id: The SpaceId to resolve.

        Returns:
            The TileStrategy for that space type.

        Raises:
            ValueError: If no strategy is registered for the given space_id.
        """
        if space_id not in cls._strategies:
            raise ValueError(f"No strategy registered for SpaceId {space_id}")
        return cls._strategies[space_id]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered strategies. Useful for testing."""
        cls._strategies.clear()