"""Tests for EventType - Phase 02.1 card effect event types."""

import pytest
from ctp.core.events import EventType, GameEvent


class TestEventTypePhase021:
    """Tests for the 20 new EventType values added in Phase 02.1."""

    def test_card_effect_angel_exists(self):
        """Test 1: EventType.CARD_EFFECT_ANGEL tồn tại và là member của EventType."""
        assert EventType.CARD_EFFECT_ANGEL in EventType

    def test_all_20_new_values_have_unique_values(self):
        """Test 2: Tất cả 20 values mới đều có value khác nhau (không collision)."""
        new_events = [
            EventType.CARD_EFFECT_ANGEL,
            EventType.CARD_EFFECT_DISCOUNT_TOLL,
            EventType.CARD_EFFECT_SHIELD_BLOCKED,
            EventType.CARD_EFFECT_ESCAPE_USED,
            EventType.CARD_EFFECT_PINWHEEL_BYPASS,
            EventType.CARD_EFFECT_FORCE_SELL,
            EventType.CARD_EFFECT_SWAP_CITY,
            EventType.CARD_EFFECT_DOWNGRADE,
            EventType.CARD_EFFECT_VIRUS,
            EventType.CARD_EFFECT_GO_TO_START,
            EventType.CARD_EFFECT_GO_TO_PRISON,
            EventType.CARD_EFFECT_DOUBLE_TOLL_DEBUFF,
            EventType.CARD_EFFECT_GO_TO_FESTIVAL,
            EventType.CARD_EFFECT_GO_TO_FESTIVAL_TILE,
            EventType.CARD_EFFECT_GO_TO_TRAVEL,
            EventType.CARD_EFFECT_GO_TO_TAX,
            EventType.CARD_EFFECT_GO_TO_GOD,
            EventType.CARD_EFFECT_HOST_FESTIVAL,
            EventType.CARD_EFFECT_DONATE_CITY,
            EventType.CARD_EFFECT_CHARITY,
        ]
        # All 20 should have unique values
        values = [e.value for e in new_events]
        assert len(values) == len(set(values)), "Duplicate values found among new EventTypes"
        # No collision with old events
        all_values = [e.value for e in EventType]
        assert len(all_values) == len(set(all_values)), "Value collision between old and new EventTypes"

    def test_card_drawn_still_exists(self):
        """Test 3: EventType.CARD_DRAWN vẫn tồn tại (không bị xóa)."""
        assert EventType.CARD_DRAWN in EventType

    def test_game_event_with_card_effect_virus(self):
        """Test 4: GameEvent với CARD_EFFECT_VIRUS khởi tạo OK."""
        event = GameEvent(
            event_type=EventType.CARD_EFFECT_VIRUS,
            player_id="p1",
            data={"target_player": "p2", "duration": 3}
        )
        assert event.event_type == EventType.CARD_EFFECT_VIRUS
        assert event.player_id == "p1"
        assert event.data["target_player"] == "p2"
        assert event.data["duration"] == 3
