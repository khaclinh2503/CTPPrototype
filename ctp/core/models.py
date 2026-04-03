"""Player and related data models for CTP game."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Player:
    """Player in the CTP game.

    This is the Phase 1 skeleton - buff slots (Skills, Pendant, Pet)
    will be added in Phase 2.

    Attributes:
        player_id: Unique identifier for this player.
        cash: Current cash amount.
        position: Current position on board (1-32, starts at 1 = START).
        is_bankrupt: Whether player has gone bankrupt.
        owned_properties: List of tile positions owned by this player.
        prison_turns_remaining: Turns remaining in prison (0 = not in prison).
    """

    player_id: str
    cash: float
    position: int = 1  # 1-indexed, start at position 1 (Start tile)
    is_bankrupt: bool = False
    owned_properties: list[int] = field(default_factory=list)  # tile positions (1-32)
    prison_turns_remaining: int = 0  # 0 = not in prison
    pending_travel: bool = False     # True = đầu lượt sau phải xử lý travel
    turns_taken: int = 0              # Số lượt đã hoàn thành (dùng cho God tile)
    held_card: str | None = None      # Card ID đang giữ (vd "IT_CA_21") hoặc None
    accuracy_rate: int = 15           # % cơ hội đổ chính xác (căn lực), default 15%
    virus_turns: int = 0              # Số lượt còn bị virus (EF_7)
    double_toll_turns: int = 0        # Số lượt còn bị tăng gấp đôi thuê (EF_8)

    # Phase 02.1: Card draw + Căn lực fields
    held_card: str | None = None          # card_id đang giữ (ví dụ "IT_CA_3"), per D-09
    accuracy_rate: int = 15               # căn lực base rate (%), per D-10
    virus_turns: int = 0                  # EF_7/8 debuff rounds remaining, per D-11
    double_toll_turns: int = 0            # EF_16 self-debuff rounds remaining, per D-12

    def can_afford(self, amount: float) -> bool:
        """Check if player has enough cash (excluding property value).

        Args:
            amount: Amount to check.

        Returns:
            True if player has at least this much cash.
        """
        return self.cash >= amount

    def receive(self, amount: float) -> None:
        """Add money to player's cash.

        Args:
            amount: Amount to add.
        """
        self.cash += amount

    def pay(self, amount: float) -> bool:
        """Pay amount from player's cash.

        Args:
            amount: Amount to pay.

        Returns:
            True if payment successful (had enough cash).
            False if insufficient funds (cash unchanged).
        """
        if self.cash >= amount:
            self.cash -= amount
            return True
        return False

    def move_to(self, position: int) -> None:
        """Move player to a new position.

        Args:
            position: New position (1-32).
        """
        if not 1 <= position <= 32:
            raise ValueError(f"Position must be 1-32, got {position}")
        self.position = position

    def move_forward(self, spaces: int) -> None:
        """Move player forward by given spaces, wrapping around board.

        Args:
            spaces: Number of spaces to move forward.
        """
        new_pos = ((self.position - 1 + spaces) % 32) + 1
        self.position = new_pos

    def add_property(self, position: int) -> None:
        """Add a property to player's owned properties.

        Args:
            position: Tile position to add.
        """
        if position not in self.owned_properties:
            self.owned_properties.append(position)

    def remove_property(self, position: int) -> None:
        """Remove a property from player's owned properties.

        Args:
            position: Tile position to remove.
        """
        if position in self.owned_properties:
            self.owned_properties.remove(position)

    def enter_prison(self) -> None:
        """Put player in prison for 3 turns."""
        self.prison_turns_remaining = 3

    def exit_prison(self) -> None:
        """Release player from prison."""
        self.prison_turns_remaining = 0

    def decrement_prison_turn(self) -> None:
        """Decrement prison turn counter if in prison."""
        if self.prison_turns_remaining > 0:
            self.prison_turns_remaining -= 1