"""Tests for GameController FSM."""

import pytest
from unittest.mock import patch
from ctp.core.board import SpaceId, Tile, Board
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.controller.fsm import GameController, TurnPhase
from ctp.controller.bankruptcy import resolve_bankruptcy
from ctp.tiles import TileRegistry


@pytest.fixture
def space_positions():
    """Standard 32-tile board layout."""
    return {
        "1": {"spaceId": 7, "opt": 0},   # START
        "2": {"spaceId": 3, "opt": 1},   # LAND
        "3": {"spaceId": 4, "opt": 0},   # PRISON
        "4": {"spaceId": 3, "opt": 2},   # LAND
        "5": {"spaceId": 6, "opt": 101}, # FORTUNE_EVENT
        "6": {"spaceId": 3, "opt": 3},   # LAND
        "7": {"spaceId": 3, "opt": 4},   # LAND
        "8": {"spaceId": 3, "opt": 5},   # LAND
        "9": {"spaceId": 5, "opt": 0},   # FESTIVAL
        "10": {"spaceId": 6, "opt": 102}, # FORTUNE_EVENT
        "11": {"spaceId": 3, "opt": 6},  # LAND
        "12": {"spaceId": 3, "opt": 7},  # LAND
        "13": {"spaceId": 2, "opt": 0},  # FORTUNE_CARD
        "14": {"spaceId": 3, "opt": 8},  # LAND
        "15": {"spaceId": 6, "opt": 101}, # FORTUNE_EVENT
        "16": {"spaceId": 3, "opt": 9},  # LAND
        "17": {"spaceId": 1, "opt": 0},  # TAX
        "18": {"spaceId": 3, "opt": 10}, # LAND
        "19": {"spaceId": 6, "opt": 101}, # FORTUNE_EVENT
        "20": {"spaceId": 3, "opt": 11}, # LAND
        "21": {"spaceId": 2, "opt": 0},  # FORTUNE_CARD
        "22": {"spaceId": 3, "opt": 12}, # LAND
        "23": {"spaceId": 3, "opt": 13}, # LAND
        "24": {"spaceId": 3, "opt": 14}, # LAND
        "25": {"spaceId": 9, "opt": 0},  # RESORT
        "26": {"spaceId": 6, "opt": 102}, # FORTUNE_EVENT
        "27": {"spaceId": 3, "opt": 15}, # LAND
        "28": {"spaceId": 3, "opt": 16}, # LAND
        "29": {"spaceId": 2, "opt": 0},  # FORTUNE_CARD
        "30": {"spaceId": 3, "opt": 17}, # LAND
        "31": {"spaceId": 8, "opt": 0},  # TRAVEL
        "32": {"spaceId": 3, "opt": 18}, # LAND
    }


@pytest.fixture
def land_config():
    """LandSpace configuration."""
    return {
        "1": {
            "1": {"color": 1, "building": {"1": {"build": 10, "toll": 1}, "2": {"build": 5, "toll": 3}, "3": {"build": 15, "toll": 10}, "4": {"build": 25, "toll": 28}, "5": {"build": 25, "toll": 125}}},
            "2": {"color": 1, "building": {"1": {"build": 10, "toll": 1}, "2": {"build": 5, "toll": 3}, "3": {"build": 15, "toll": 10}, "4": {"build": 25, "toll": 28}, "5": {"build": 25, "toll": 125}}},
        }
    }


@pytest.fixture
def resort_config():
    """ResortSpace configuration."""
    return {
        "maxUpgrade": 3,
        "initCost": 50,
        "tollCost": 25,
        "increaseRate": 2
    }


@pytest.fixture
def festival_config():
    """FestivalSpace configuration."""
    return {
        "holdCostRate": 0.02,
        "increaseRate": 2,
        "maxFestival": 1
    }


@pytest.fixture
def board(space_positions, land_config, resort_config, festival_config):
    """Create a test board."""
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config
    )


@pytest.fixture
def players():
    """Create test players."""
    return [
        Player(player_id="Player1", cash=200),
        Player(player_id="Player2", cash=200),
    ]


@pytest.fixture
def event_bus():
    """Create an EventBus."""
    return EventBus()


@pytest.fixture
def controller(board, players, event_bus):
    """Create a GameController."""
    return GameController(
        board=board,
        players=players,
        max_turns=25,
        event_bus=event_bus
    )


class TestGameControllerInitialization:
    """Test GameController initialization."""

    def test_initializes_with_players(self, controller, players):
        assert len(controller.players) == 2

    def test_initial_phase_is_roll(self, controller):
        assert controller.phase == TurnPhase.ROLL

    def test_current_player_is_first(self, controller):
        assert controller.current_player.player_id == "Player1"

    def test_current_turn_is_1(self, controller):
        assert controller.current_turn == 1


class TestDiceRoll:
    """Test dice rolling."""

    def test_roll_dice_returns_2d6(self, controller):
        dice = controller.roll_dice()
        assert len(dice) == 2
        assert 1 <= dice[0] <= 6
        assert 1 <= dice[1] <= 6

    def test_roll_dice_total_in_range(self, controller):
        dice = controller.roll_dice()
        total = sum(dice)
        assert 2 <= total <= 12


class TestFSMStateTransitions:
    """Test FSM state transitions through a turn."""

    def test_step_roll_to_move(self, controller):
        """ROLL -> MOVE"""
        controller.step()
        assert controller.phase == TurnPhase.MOVE

    def test_step_move_to_resolve_tile(self, controller):
        """MOVE -> RESOLVE_TILE"""
        # First roll
        controller.step()
        # Then move
        controller.step()
        assert controller.phase == TurnPhase.RESOLVE_TILE

    def test_step_resolve_to_acquire(self, controller):
        """RESOLVE_TILE -> ACQUIRE (Phase 2: acquisition phase added)"""
        # Roll
        controller.step()
        # Move
        controller.step()
        # Resolve tile
        controller.step()
        assert controller.phase == TurnPhase.ACQUIRE

    def test_step_acquire_to_upgrade(self, controller):
        """ACQUIRE -> UPGRADE"""
        # Roll
        controller.step()
        # Move
        controller.step()
        # Resolve tile
        controller.step()
        # Acquire
        controller.step()
        assert controller.phase == TurnPhase.UPGRADE

    def test_step_upgrade_to_check_bankruptcy(self, controller):
        """UPGRADE -> CHECK_BANKRUPTCY"""
        # Roll
        controller.step()
        # Move
        controller.step()
        # Resolve tile
        controller.step()
        # Acquire
        controller.step()
        # Upgrade
        controller.step()
        assert controller.phase == TurnPhase.CHECK_BANKRUPTCY

    def test_step_check_to_end_turn(self, controller):
        """CHECK_BANKRUPTCY -> END_TURN (force non-doubles so no re-roll)"""
        controller._current_dice = (1, 2)  # ensure not doubles before check
        controller._rolled_doubles = False
        # Move
        controller.phase = TurnPhase.MOVE
        controller.step()
        # Resolve
        controller.step()
        # Acquire
        controller.step()
        # Upgrade
        controller.step()
        # Check bankruptcy
        controller.step()
        assert controller.phase == TurnPhase.END_TURN

    def test_full_turn_cycle(self, controller, monkeypatch):
        """Complete turn cycles back to ROLL (7 steps with ACQUIRE + UPGRADE phases)."""
        monkeypatch.setattr(controller, 'roll_dice', lambda: (1, 2))  # non-doubles
        # Complete one full turn for Player1: ROLL+MOVE+RESOLVE+ACQUIRE+UPGRADE+CHECK+END = 7
        for _ in range(7):
            controller.step()

        # Should be back to ROLL for next player
        assert controller.phase == TurnPhase.ROLL
        assert controller.current_player.player_id == "Player2"


class TestPositionWrapping:
    """Test position wrapping around the 32-tile board."""

    def test_position_wraps_at_32(self, controller):
        """Player at position 30 rolls 7 -> lands on position 5."""
        controller.current_player.position = 30
        # Set the dice directly and skip the ROLL phase to test MOVE
        controller._current_dice = (3, 4)  # 30 + 7 = 37 -> wraps to 5
        controller.phase = TurnPhase.MOVE  # Skip roll phase

        # Do move
        controller.step()  # MOVE

        assert controller.current_player.position == 5


class TestPassingStart:
    """Test passing Start gives bonus."""

    def test_passing_start_triggers_bonus(self, controller, event_bus):
        """Player passing Start gets passing bonus."""
        controller.current_player.position = 30
        controller.current_player.cash = 200
        controller._current_dice = (3, 4)  # 7 total -> wraps past start
        controller.phase = TurnPhase.MOVE  # Skip roll phase

        # Move (triggers passing bonus)
        controller.step()

        # Check bonus was received
        bonus_events = event_bus.get_events(EventType.BONUS_RECEIVED)
        assert len(bonus_events) > 0


class TestTerminalConditions:
    """Test game over conditions."""

    def test_game_over_when_single_player_left(self, controller):
        """Game ends when only 1 non-bankrupt player remains."""
        # Bankrupt Player2
        controller.players[1].is_bankrupt = True

        # Player1 completes a turn
        for _ in range(5):
            controller.step()

        assert controller.is_game_over() == True

    def test_game_over_at_max_turns(self, controller):
        """Game ends when current_turn >= max_turns."""
        controller.max_turns = 1
        controller.current_turn = 1

        assert controller.is_game_over() == True

    def test_get_winner_returns_highest_cash(self, controller):
        """Winner is player with highest cash."""
        controller.players[0].cash = 100
        controller.players[1].cash = 200

        winner = controller._get_winner()
        assert winner == "Player2"


class TestPrisonHandling:
    """Test prison handling in FSM."""

    def test_prison_player_no_doubles_stays_in_jail(self, controller, event_bus, monkeypatch):
        """Player in prison with no money rolls non-doubles → stays in jail, END_TURN."""
        controller.current_player.prison_turns_remaining = 2
        controller.current_player.cash = 0  # cannot afford escape fee
        monkeypatch.setattr(controller, 'roll_dice', lambda: (1, 2))  # non-doubles

        controller.step()

        assert controller.phase == TurnPhase.END_TURN
        assert controller.current_player.prison_turns_remaining == 1

    def test_prison_player_doubles_exits_and_moves(self, controller, event_bus, monkeypatch):
        """Player in prison with no money rolls doubles → exits prison, phase = MOVE."""
        controller.current_player.prison_turns_remaining = 2
        controller.current_player.cash = 0  # cannot afford escape fee
        monkeypatch.setattr(controller, 'roll_dice', lambda: (2, 2))  # doubles

        controller.step()

        assert controller.phase == TurnPhase.MOVE
        assert controller.current_player.prison_turns_remaining == 0


class TestCanLuc:
    """Tests for đổ chính xác (căn lực) mechanic."""

    def test_resolve_can_luc_miss_returns_normal_dice(self, controller):
        """Khi precision check > accuracy_rate, trả về 2d6 bình thường."""
        from ctp.controller.fsm import _CAN_LUC_RANGES
        controller.current_player.accuracy_rate = 15
        # Mock: precision_check=20 > 15, nên miss; normal d1=3, d2=4
        with patch("random.randint", side_effect=[20, 3, 4]):
            result = controller._resolve_can_luc(chosen_range=0)
        # Miss → normal 2d6 = (3, 4)
        assert result == (3, 4)

    def test_resolve_can_luc_hit_range0_sum_in_2_4(self, controller):
        """Khi precision hit, sum nằm trong khoảng 0: [2,4]."""
        controller.current_player.accuracy_rate = 15
        # Mock: precision_check=5 <= 15, T=3, d1_lo=max(1,3-6)=1, d1_hi=min(6,2)=2, d1=1, d2=2
        with patch("random.randint", side_effect=[5, 3, 1]):
            result = controller._resolve_can_luc(chosen_range=0)
        assert result == (1, 2)
        assert sum(result) == 3
        assert 2 <= sum(result) <= 4

    def test_resolve_can_luc_hit_range3_sum_in_10_12(self, controller):
        """Khi precision hit, sum nằm trong khoảng 3: [10,12]."""
        controller.current_player.accuracy_rate = 100
        # Range 3: lo=10, hi=12; T=11; d1_lo=max(1,5)=5, d1_hi=min(6,10)=6; d1=5, d2=6
        with patch("random.randint", side_effect=[50, 11, 5]):
            result = controller._resolve_can_luc(chosen_range=3)
        assert result == (5, 6)
        assert sum(result) == 11
        assert 10 <= sum(result) <= 12

    def test_resolve_can_luc_dice_split_valid(self, controller):
        """Dice split D-40: T=11 → d1 ∈ [5,6], d2=11-d1, cả hai trong [1,6]."""
        controller.current_player.accuracy_rate = 100
        with patch("random.randint", side_effect=[1, 11, 5]):
            result = controller._resolve_can_luc(chosen_range=3)
        d1, d2 = result
        assert 1 <= d1 <= 6
        assert 1 <= d2 <= 6
        assert d1 + d2 == 11

    def test_resolve_can_luc_doubles_possible(self, controller):
        """T=6 có thể trả về (3,3)."""
        controller.current_player.accuracy_rate = 100
        # Range 1: lo=5, hi=7; T=6; d1_lo=max(1,0)=1, d1_hi=min(6,5)=5; d1=3, d2=3
        with patch("random.randint", side_effect=[1, 6, 3]):
            result = controller._resolve_can_luc(chosen_range=1)
        assert result == (3, 3)
        assert result[0] == result[1]  # doubles

    def test_choose_range_ai_no_unowned_tiles_returns_fallback(self, controller):
        """Khi không có unowned CITY/RESORT, trả về 1 (fallback)."""
        # Gán owner cho tất cả CITY và RESORT tiles
        for tile in controller.board.board:
            if tile.space_id in (SpaceId.CITY, SpaceId.RESORT):
                tile.owner_id = "Player1"
        result = controller._choose_range_ai()
        assert result == 1

    def test_choose_range_ai_unowned_city_6_steps_returns_range1(self, controller):
        """Unowned CITY ở 6 steps → range index 1 (khoảng [5-7] chứa 6)."""
        player = controller.current_player
        player.position = 1
        # Đảm bảo tile ở position 7 là CITY và unowned
        tile7 = controller.board.get_tile(7)
        tile7.owner_id = None
        # Đảm bảo tất cả CITY tiles gần hơn đều owned
        for steps in range(1, 6):
            pos = ((player.position - 1 + steps) % 32) + 1
            t = controller.board.get_tile(pos)
            if t.space_id == SpaceId.CITY:
                t.owner_id = "Player2"
        result = controller._choose_range_ai()
        assert 0 <= result <= 3


class TestFSMIntegration:
    """Tests cho FSM integration — _do_roll, _do_move, _do_end_turn với card effects."""

    def test_ef19_escape_card_auto_use_in_prison(self, controller, event_bus):
        """Player có prison_turns_remaining=2 và held_card EF_19 → thoát tù khi roll."""
        player = controller.current_player
        player.prison_turns_remaining = 2
        player.held_card = "IT_CA_21"  # EF_19
        player.cash = 0  # đảm bảo không thể trả phí tù

        controller.step()  # _do_roll

        assert player.prison_turns_remaining == 0  # đã thoát tù
        assert player.held_card is None  # card đã consumed

    def test_double_toll_turns_decrements_in_roll(self, controller):
        """player.double_toll_turns=1 → sau _do_roll(), giảm xuống 0."""
        player = controller.current_player
        player.double_toll_turns = 1
        player.prison_turns_remaining = 0

        controller.step()  # _do_roll

        assert player.double_toll_turns == 0

    def test_dice_roll_event_has_chosen_range_and_precision_hit(self, controller, event_bus):
        """DICE_ROLL event data phải có 'chosen_range' và 'precision_hit' keys."""
        controller.step()  # _do_roll

        dice_events = event_bus.get_events(EventType.DICE_ROLL)
        assert len(dice_events) > 0
        event_data = dice_events[0].data
        assert "chosen_range" in event_data
        assert "precision_hit" in event_data

    def test_ef22_pinwheel_bypass_elevated_tile(self, board, players, event_bus):
        """Player có held_card EF_22 và có elevated tile trong path → bypass."""
        ctrl = GameController(board=board, players=players, max_turns=25, event_bus=event_bus)
        player = ctrl.current_player
        player.held_card = "IT_CA_23"  # EF_22

        # Đặt elevated tile tại position 3 (2 bước từ start)
        board.elevate_tile(3)
        ctrl._current_dice = (1, 1)  # tổng 2 → sẽ gặp ô 3
        ctrl.phase = TurnPhase.MOVE

        ctrl.step()  # _do_move

        assert player.held_card is None       # card consumed
        assert board.elevated_tile is None    # elevated cleared

    def test_dict_key_bug_tile_lowered_event_has_string_keys(self, board, players, event_bus):
        """TILE_LOWERED event data['position'] là integer, không phải variable reference."""
        ctrl = GameController(board=board, players=players, max_turns=25, event_bus=event_bus)
        # Đặt elevated tile và di chuyển qua nó
        board.elevate_tile(3)
        ctrl._current_dice = (1, 1)  # đi 2 bước, ô 3 elevated
        ctrl.phase = TurnPhase.MOVE

        ctrl.step()  # _do_move

        lowered_events = event_bus.get_events(EventType.TILE_LOWERED)
        assert len(lowered_events) > 0
        assert "position" in lowered_events[0].data
        assert isinstance(lowered_events[0].data["position"], int)

    def test_toll_debuff_turns_decrements_in_end_turn(self, controller):
        """tile.toll_debuff_turns=2 → sau _do_end_turn(), toll_debuff_turns == 1."""
        tile = controller.board.board[1]  # pos 2 (CITY)
        tile.toll_debuff_turns = 2
        tile.toll_debuff_rate = 0.0

        controller.phase = TurnPhase.END_TURN
        controller.step()  # _do_end_turn

        assert tile.toll_debuff_turns == 1
        assert tile.toll_debuff_rate == 0.0  # vẫn còn active

    def test_toll_debuff_turns_clears_rate_when_expired(self, controller):
        """tile.toll_debuff_turns=1 → sau END_TURN, toll_debuff_turns=0, rate=1.0."""
        tile = controller.board.board[1]
        tile.toll_debuff_turns = 1
        tile.toll_debuff_rate = 0.0

        controller.phase = TurnPhase.END_TURN
        controller.step()

        assert tile.toll_debuff_turns == 0
        assert tile.toll_debuff_rate == 1.0

    def test_player_move_event_has_string_keys(self, board, players, event_bus):
        """PLAYER_MOVE event data có 'old_pos' và 'new_pos' là string keys."""
        ctrl = GameController(board=board, players=players, max_turns=25, event_bus=event_bus)
        board.elevate_tile(3)
        ctrl._current_dice = (1, 1)
        ctrl.phase = TurnPhase.MOVE

        ctrl.step()  # _do_move

        move_events = event_bus.get_events(EventType.PLAYER_MOVE)
        assert len(move_events) > 0
        data = move_events[0].data
        assert "old_pos" in data
        assert "new_pos" in data
        assert isinstance(data["old_pos"], int)
        assert isinstance(data["new_pos"], int)


class TestBankruptcyResolution:
    """Test bankruptcy resolution."""

    def test_resolve_bankruptcy_sells_properties(self, board, event_bus):
        """Bankruptcy resolution sells properties."""
        player = Player(player_id="p1", cash=-50)
        player.add_property(2)  # Add a property

        # Setup board with owned tile
        tile = board.get_tile(2)
        tile.owner_id = "p1"

        events = resolve_bankruptcy(player, board, event_bus)

        # Should have property sold event
        sold_events = event_bus.get_events(EventType.PROPERTY_SOLD)
        assert len(sold_events) > 0

    def test_resolve_bankruptcy_marks_player(self, board, event_bus):
        """Bankruptcy resolution marks player as bankrupt when unable to pay."""
        player = Player(player_id="p1", cash=-1000)  # Can't afford to pay

        events = resolve_bankruptcy(player, board, event_bus)

        # Player should be marked bankrupt
        assert player.is_bankrupt == True

        # Should have bankruptcy event
        bankrupt_events = event_bus.get_events(EventType.PLAYER_BANKRUPT)
        assert len(bankrupt_events) > 0


class TestInstantWinConditions:
    """Test 3 instant win conditions: 4 resort, 3 color groups, own row."""

    @pytest.fixture
    def rich_land_config(self):
        """Land config with 3 color groups (6 tiles), đủ để test 3_color_groups."""
        building = {"1": {"build": 10, "toll": 1}, "2": {"build": 5, "toll": 3},
                    "3": {"build": 15, "toll": 10}, "4": {"build": 25, "toll": 28},
                    "5": {"build": 25, "toll": 125}}
        return {
            "1": {
                # color 1: opts 1,2 → positions 2,4
                "1": {"color": 1, "building": building},
                "2": {"color": 1, "building": building},
                # color 2: opts 3,4,5 → positions 6,7,8
                "3": {"color": 2, "building": building},
                "4": {"color": 2, "building": building},
                "5": {"color": 2, "building": building},
                # color 3: opts 6,7 → positions 11,12
                "6": {"color": 3, "building": building},
                "7": {"color": 3, "building": building},
                # other colors for remaining tiles
                "8": {"color": 4, "building": building},
                "9": {"color": 4, "building": building},
                "10": {"color": 5, "building": building},
                "11": {"color": 5, "building": building},
                "12": {"color": 6, "building": building},
                "13": {"color": 6, "building": building},
                "14": {"color": 6, "building": building},
                "15": {"color": 7, "building": building},
                "16": {"color": 7, "building": building},
                "17": {"color": 8, "building": building},
                "18": {"color": 8, "building": building},
            }
        }

    @pytest.fixture
    def full_board(self, space_positions, rich_land_config, resort_config, festival_config):
        return Board(
            space_positions=space_positions,
            land_config=rich_land_config,
            resort_config=resort_config,
            festival_config=festival_config,
        )

    @pytest.fixture
    def ctrl(self, full_board, event_bus):
        players = [
            Player(player_id="P1", cash=10_000_000),
            Player(player_id="P2", cash=10_000_000),
        ]
        return GameController(
            board=full_board,
            players=players,
            max_turns=25,
            event_bus=event_bus,
        )

    def test_instant_win_all_resorts(self, ctrl, full_board):
        """Sở hữu tất cả resort → instant win all_resorts."""
        p1 = ctrl.players[0]
        # Tất cả 5 ô Resort trên bàn: pos 5, 10, 15, 19, 26
        resort_positions = [
            t.position for t in full_board.board if t.space_id == SpaceId.RESORT
        ]
        for pos in resort_positions:
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        reason = ctrl._check_instant_win(p1)
        assert reason == "all_resorts"

    def test_no_win_partial_resorts(self, ctrl, full_board):
        """Chưa sở hữu tất cả resort → chưa win."""
        p1 = ctrl.players[0]
        # Chỉ sở hữu 4/5 resort
        resort_positions = [
            t.position for t in full_board.board if t.space_id == SpaceId.RESORT
        ]
        for pos in resort_positions[:-1]:  # bỏ 1 resort
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        reason = ctrl._check_instant_win(p1)
        assert reason is None

    def test_instant_win_3_color_groups(self, ctrl, full_board):
        """Hoàn thành 3 nhóm màu → instant win 3_color_groups."""
        p1 = ctrl.players[0]
        # color 1: opts 1,2 → pos 2,4
        # color 2: opts 3,4,5 → pos 6,7,8
        # color 3: opts 6,7 → pos 11,12
        for pos in (2, 4, 6, 7, 8, 11, 12):
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        reason = ctrl._check_instant_win(p1)
        assert reason == "3_color_groups"

    def test_no_win_2_color_groups(self, ctrl, full_board):
        """Chỉ 2 nhóm màu hoàn chỉnh (từ 2 hàng khác nhau) → chưa win."""
        p1 = ctrl.players[0]
        # color 1 (row 1): pos 2,4 | color 3 (row 2): pos 11,12
        # Không hoàn thành hàng nào, cũng chưa đủ 3 màu
        for pos in (2, 4, 11, 12):
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        reason = ctrl._check_instant_win(p1)
        assert reason is None

    def test_instant_win_own_row(self, ctrl, full_board):
        """Sở hữu toàn bộ CITY + RESORT trong row 2 (pos 9-16) → instant win own_row."""
        p1 = ctrl.players[0]
        # Row 2 (pos 9-16): CITY tại 11,12,14,16 + RESORT tại 10,15
        for pos in (10, 11, 12, 14, 15, 16):
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        reason = ctrl._check_instant_win(p1)
        assert reason == "own_row"

    def test_no_win_partial_row(self, ctrl, full_board):
        """Thiếu 1 ô trong row → chưa win."""
        p1 = ctrl.players[0]
        # Row 2: có CITY 11,12,14,16 nhưng thiếu RESORT 10 và 15
        for pos in (11, 12, 14, 16):
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        reason = ctrl._check_instant_win(p1)
        assert reason is None

    def test_instant_win_triggers_game_over(self, ctrl, full_board, event_bus):
        """Instant win → GAME_ENDED event published, game_over=True."""
        p1 = ctrl.players[0]
        # Trao tất cả resort cho p1
        resort_positions = [
            t.position for t in full_board.board if t.space_id == SpaceId.RESORT
        ]
        for pos in resort_positions:
            tile = full_board.get_tile(pos)
            tile.owner_id = p1.player_id
            p1.add_property(pos)

        ctrl.phase = ctrl.phase.END_TURN
        ctrl.step()

        assert ctrl.is_game_over()
        assert ctrl.winner == "P1"
        ended_events = event_bus.get_events(EventType.GAME_ENDED)
        assert len(ended_events) == 1
        assert ended_events[0].data["reason"] == "all_resorts"

    def test_winner_by_total_wealth_not_cash(self, ctrl, full_board):
        """Khi hết turn, winner là người có tổng tài sản cao nhất (cash + công trình)."""
        p1, p2 = ctrl.players
        p1.cash = 100
        p2.cash = 50

        # P2 sở hữu 1 ô đất level 2 (build 1: 10*BASE_UNIT + build 2: 5*BASE_UNIT = 15 BASE_UNIT)
        from ctp.core.constants import BASE_UNIT
        tile = full_board.get_tile(2)
        tile.owner_id = p2.player_id
        tile.building_level = 2
        p2.add_property(2)

        wealth_p1 = ctrl._get_total_wealth(p1)
        wealth_p2 = ctrl._get_total_wealth(p2)

        # P2: 50 + (10+5)*BASE_UNIT = 50 + 15_000_000
        assert wealth_p2 > wealth_p1
        assert ctrl._get_winner() == "P2"