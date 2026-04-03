"""Tests for Player data model - Phase 02.1 fields."""

import pytest
from ctp.core.models import Player


class TestPlayerPhase021Fields:
    """Tests for the 4 new Player fields added in Phase 02.1."""

    def test_player_default_init_has_new_fields(self):
        """Test 1: Player() khởi tạo không arg vẫn OK, new fields có giá trị mặc định."""
        player = Player(player_id="p1", cash=1_000_000)
        assert player.held_card is None
        assert player.accuracy_rate == 15
        assert player.virus_turns == 0
        assert player.double_toll_turns == 0

    def test_player_backward_compatible(self):
        """Test 2: Player(player_id="p1", cash=1_000_000) vẫn OK — backward compatible."""
        player = Player(player_id="p1", cash=1_000_000)
        assert player.player_id == "p1"
        assert player.cash == 1_000_000
        assert player.position == 1
        assert player.is_bankrupt is False

    def test_player_held_card_can_be_set_and_read(self):
        """Test 3: Có thể set player.held_card = "IT_CA_3" và đọc lại đúng."""
        player = Player(player_id="p1", cash=1_000_000)
        player.held_card = "IT_CA_3"
        assert player.held_card == "IT_CA_3"

    def test_player_accuracy_rate_can_be_overridden(self):
        """Test 4: accuracy_rate có thể override khi khởi tạo."""
        player = Player(player_id="p1", cash=0, accuracy_rate=25)
        assert player.accuracy_rate == 25
