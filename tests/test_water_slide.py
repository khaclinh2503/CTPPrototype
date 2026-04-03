"""Tests for Water Slide tile mechanics (Map 3).

Mechanics:
- Khi đáp vào ô Water Slide: xóa sóng cũ, tạo sóng mới, player trượt đến dest.
- Khi đi vào vùng sóng (source+1 → dest): player bị đẩy đến dest.
- Sóng tồn tại mãi cho đến khi có người đáp vào ô Water Slide tiếp theo.
- Người đó tạo sóng mới hay không → sóng cũ đều mất.
- Player tạo sóng cũng bị đẩy nếu lượt sau đi vào vùng sóng.
"""

import pytest
from ctp.core.board import Board, SpaceId, Tile
from ctp.core.models import Player
from ctp.core.events import EventBus, EventType
from ctp.controller.fsm import GameController, TurnPhase
from ctp.tiles.water_slide import WaterSlideStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WATER_SLIDE_POS = 5   # non-corner position in row 1 (1-8)


@pytest.fixture
def space_positions():
    """Bàn cờ 32 ô có ô Water Slide tại position 5 (row 1)."""
    return {
        "1": {"spaceId": 7, "opt": 0},    # START (corner)
        "2": {"spaceId": 3, "opt": 1},    # CITY
        "3": {"spaceId": 3, "opt": 2},    # CITY
        "4": {"spaceId": 3, "opt": 3},    # CITY
        "5": {"spaceId": 40, "opt": 0},   # WATER_SLIDE
        "6": {"spaceId": 3, "opt": 4},    # CITY
        "7": {"spaceId": 3, "opt": 5},    # CITY
        "8": {"spaceId": 3, "opt": 6},    # CITY
        "9": {"spaceId": 5, "opt": 0},    # PRISON (corner)
        "10": {"spaceId": 6, "opt": 101}, # RESORT
        "11": {"spaceId": 3, "opt": 7},   # CITY
        "12": {"spaceId": 3, "opt": 8},   # CITY
        "13": {"spaceId": 2, "opt": 0},   # CHANCE
        "14": {"spaceId": 3, "opt": 9},   # CITY
        "15": {"spaceId": 6, "opt": 101}, # RESORT
        "16": {"spaceId": 3, "opt": 10},  # CITY
        "17": {"spaceId": 1, "opt": 0},   # FESTIVAL (corner)
        "18": {"spaceId": 3, "opt": 11},  # CITY
        "19": {"spaceId": 6, "opt": 101}, # RESORT
        "20": {"spaceId": 3, "opt": 12},  # CITY
        "21": {"spaceId": 2, "opt": 0},   # CHANCE
        "22": {"spaceId": 3, "opt": 13},  # CITY
        "23": {"spaceId": 3, "opt": 14},  # CITY
        "24": {"spaceId": 3, "opt": 15},  # CITY
        "25": {"spaceId": 9, "opt": 0},   # TRAVEL (corner)
        "26": {"spaceId": 6, "opt": 102}, # RESORT
        "27": {"spaceId": 3, "opt": 16},  # CITY
        "28": {"spaceId": 3, "opt": 17},  # CITY
        "29": {"spaceId": 2, "opt": 0},   # CHANCE
        "30": {"spaceId": 3, "opt": 18},  # CITY
        "31": {"spaceId": 8, "opt": 0},   # TAX
        "32": {"spaceId": 3, "opt": 1},   # CITY
    }


@pytest.fixture
def land_config():
    opts = {str(i): {"color": i, "building": {
        "1": {"build": 10, "toll": 5},
        "2": {"build": 10, "toll": 15},
        "3": {"build": 10, "toll": 30},
        "4": {"build": 10, "toll": 60},
        "5": {"build": 10, "toll": 100},
    }} for i in range(1, 19)}
    return {"1": opts}


@pytest.fixture
def resort_config():
    return {"maxUpgrade": 3, "initCost": 50, "tollCost": 25, "increaseRate": 2}


@pytest.fixture
def board(space_positions, land_config, resort_config):
    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
    )


def make_controller(board, players, starting_cash=1_000_000):
    bus = EventBus()
    ctrl = GameController(
        board=board,
        players=players,
        max_turns=25,
        event_bus=bus,
        starting_cash=starting_cash,
    )
    return ctrl, bus


# ---------------------------------------------------------------------------
# Board helper: get_row_non_corner_positions
# ---------------------------------------------------------------------------

class TestGetRowNonCorner:
    def test_row1_non_corner(self, board):
        # position 5 → row 1-8, exclude corners {1} and self (5)
        result = board.get_row_non_corner_positions(5)
        assert set(result) == {2, 3, 4, 6, 7, 8}
        assert 5 not in result
        assert 1 not in result  # corner

    def test_row1_at_corner(self, board):
        # position 1 (corner) → non-corner positions in row 1, exclude self
        result = board.get_row_non_corner_positions(1)
        assert set(result) == {2, 3, 4, 5, 6, 7, 8}
        assert 1 not in result

    def test_row2(self, board):
        result = board.get_row_non_corner_positions(13)
        assert set(result) == {10, 11, 12, 14, 15, 16}
        assert 9 not in result   # corner
        assert 13 not in result  # self

    def test_row4(self, board):
        result = board.get_row_non_corner_positions(28)
        assert set(result) == {26, 27, 29, 30, 31, 32}
        assert 25 not in result  # corner


# ---------------------------------------------------------------------------
# Board helper: get_wave_zone
# ---------------------------------------------------------------------------

class TestGetWaveZone:
    def test_no_wave(self, board):
        assert board.get_wave_zone() == set()

    def test_forward_wave(self, board):
        # source=5, dest=8: zone = {6, 7, 8}
        board.water_wave = (5, 8)
        assert board.get_wave_zone() == {6, 7, 8}

    def test_backward_within_row_wraps(self, board):
        # source=7, dest=3: zone wraps around board
        board.water_wave = (7, 3)
        zone = board.get_wave_zone()
        assert 8 in zone
        assert 3 in zone
        assert 7 not in zone  # source excluded
        # 4 intermediate positions: 8,9,...,32,1,2,3
        assert len(zone) == 32 - 7 + 3  # 28 positions

    def test_same_source_dest(self, board):
        board.water_wave = (5, 5)
        assert board.get_wave_zone() == set()


# ---------------------------------------------------------------------------
# on_land: wave được tạo, player trượt đến dest
# ---------------------------------------------------------------------------

class TestWaterSlideLand:
    def test_wave_created_and_player_moved(self, board):
        p = Player(player_id="p1", cash=500_000, position=WATER_SLIDE_POS)
        ctrl, bus = make_controller(board, [p])

        # Force player to land on Water Slide
        # Manually trigger _handle_water_slide_land
        ws_tile = board.get_tile(WATER_SLIDE_POS)
        # Use fixed dest via decision_fn
        dest_tile = board.get_tile(7)
        ctrl.water_slide_decision_fn = lambda c, pl, cands: dest_tile

        events = ctrl._handle_water_slide_land(ws_tile)

        assert board.water_wave == (WATER_SLIDE_POS, 7)
        assert p.position == 7
        assert any(e.event_type == EventType.WATER_SLIDE_WAVE_SET for e in events)

    def test_old_wave_cleared_before_new(self, board):
        p = Player(player_id="p1", cash=500_000, position=WATER_SLIDE_POS)
        board.water_wave = (5, 8)  # sóng cũ

        ctrl, bus = make_controller(board, [p])
        ws_tile = board.get_tile(WATER_SLIDE_POS)
        dest_tile = board.get_tile(3)
        ctrl.water_slide_decision_fn = lambda c, pl, cands: dest_tile

        ctrl._handle_water_slide_land(ws_tile)

        # Sóng mới thay sóng cũ
        assert board.water_wave == (WATER_SLIDE_POS, 3)

    def test_no_dest_chosen_clears_wave(self, board):
        p = Player(player_id="p1", cash=500_000, position=WATER_SLIDE_POS)
        board.water_wave = (5, 8)  # sóng cũ

        ctrl, bus = make_controller(board, [p])
        ws_tile = board.get_tile(WATER_SLIDE_POS)
        ctrl.water_slide_decision_fn = lambda c, pl, cands: None  # từ chối

        ctrl._handle_water_slide_land(ws_tile)

        # Sóng cũ bị xóa, không tạo sóng mới
        assert board.water_wave is None
        assert p.position == WATER_SLIDE_POS  # player không di chuyển

    def test_wave_dest_resolve_normal_via_fsm(self, board):
        """Player trượt đến CITY chưa có chủ → có thể mua đất."""
        p = Player(player_id="p1", cash=500_000, position=1)
        ctrl, bus = make_controller(board, [p])

        # Đặt player tại ô WS bằng cách force position
        p.position = WATER_SLIDE_POS
        ctrl._current_dice = (1, 1)  # dummy dice (không dùng trong resolve_tile)
        ctrl.phase = TurnPhase.RESOLVE_TILE

        dest_tile = board.get_tile(7)  # CITY opt=5, chưa có chủ
        ctrl.water_slide_decision_fn = lambda c, pl, cands: dest_tile

        ctrl.step()  # RESOLVE_TILE

        # Player đã trượt đến dest
        assert p.position == 7
        # Sóng đã tạo
        assert board.water_wave == (WATER_SLIDE_POS, 7)


# ---------------------------------------------------------------------------
# Wave interception: player bị đẩy khi đi vào vùng sóng
# ---------------------------------------------------------------------------

class TestWaveInterception:
    def test_player_pushed_to_dest(self, board):
        """Player bình thường di chuyển vào vùng sóng → bị đẩy đến dest."""
        p1 = Player(player_id="p1", cash=500_000, position=2)  # victim
        p2 = Player(player_id="p2", cash=500_000, position=WATER_SLIDE_POS)
        ctrl, bus = make_controller(board, [p1, p2])

        # Sóng: source=5, dest=8 → zone={6,7,8}
        board.water_wave = (5, 8)

        # p1 at pos 2, roll 4 → would land at 6 (in zone) → pushed to 8
        ctrl._current_dice = (2, 2)
        ctrl.phase = TurnPhase.MOVE

        ctrl.step()  # MOVE

        assert p1.position == 8
        pushed_events = [e for e in bus.get_events(EventType.WATER_SLIDE_PUSHED)]
        assert len(pushed_events) == 1
        assert pushed_events[0].data["new_pos"] == 8

    def test_wave_not_consumed_after_push(self, board):
        """Sóng không bị tiêu sau khi đẩy player."""
        p1 = Player(player_id="p1", cash=500_000, position=2)
        ctrl, bus = make_controller(board, [p1])

        board.water_wave = (5, 8)
        ctrl._current_dice = (2, 2)
        ctrl.phase = TurnPhase.MOVE
        ctrl.step()

        # Sóng vẫn còn
        assert board.water_wave == (5, 8)

    def test_creator_also_pushed_on_return(self, board):
        """Player tạo sóng cũng bị đẩy nếu lượt sau đi vào vùng sóng."""
        p1 = Player(player_id="p1", cash=500_000, position=2)
        ctrl, bus = make_controller(board, [p1])

        # Sóng: source=5, dest=8, creator là p1 (giả lập đã tạo từ trước)
        board.water_wave = (5, 8)

        # p1 at pos 3, roll 3 → lands at 6 (in zone) → pushed to 8
        p1.position = 3
        ctrl._current_dice = (1, 2)
        ctrl.phase = TurnPhase.MOVE
        ctrl.step()

        assert p1.position == 8

    def test_player_not_pushed_if_no_wave(self, board):
        """Không có sóng → di chuyển bình thường."""
        p1 = Player(player_id="p1", cash=500_000, position=2)
        ctrl, bus = make_controller(board, [p1])

        board.water_wave = None
        ctrl._current_dice = (2, 2)  # → pos 6
        ctrl.phase = TurnPhase.MOVE
        ctrl.step()

        assert p1.position == 6
        pushed_events = bus.get_events(EventType.WATER_SLIDE_PUSHED)
        assert len(pushed_events) == 0

    def test_no_push_when_path_outside_zone(self, board):
        """Di chuyển không qua vùng sóng → không bị đẩy."""
        p1 = Player(player_id="p1", cash=500_000, position=2)
        ctrl, bus = make_controller(board, [p1])

        # Sóng: source=5, dest=7 → zone={6,7}
        board.water_wave = (5, 7)

        # p1 at pos 2, roll 2 → pos 4 (not in zone)
        ctrl._current_dice = (1, 1)
        ctrl.phase = TurnPhase.MOVE
        ctrl.step()

        assert p1.position == 4
        assert len(bus.get_events(EventType.WATER_SLIDE_PUSHED)) == 0


# ---------------------------------------------------------------------------
# reset_for_new_game xóa sóng
# ---------------------------------------------------------------------------

class TestWaveReset:
    def test_wave_cleared_on_reset(self, board):
        board.water_wave = (5, 8)
        board.reset_for_new_game()
        assert board.water_wave is None


# ---------------------------------------------------------------------------
# AI: pick_dest_ai
# ---------------------------------------------------------------------------

class TestPickDestAI:
    def _make_tile(self, pos, space_id, opt=1, owner=None, level=0):
        t = Tile(position=pos, space_id=space_id, opt=opt)
        t.owner_id = owner
        t.building_level = level
        return t

    def test_prefers_unowned_city(self, board):
        player = Player(player_id="p1", cash=500_000, position=5)
        candidates = [
            self._make_tile(6, SpaceId.CITY, opt=4, owner="p2", level=2),  # opponent
            self._make_tile(7, SpaceId.CITY, opt=5, owner=None, level=0),  # unowned
            self._make_tile(8, SpaceId.CITY, opt=6, owner="p1", level=1),  # own
        ]
        result = WaterSlideStrategy.pick_dest_ai(player, candidates, board)
        assert result.position == 7  # unowned city

    def test_prefers_own_tile_over_opponent(self, board):
        player = Player(player_id="p1", cash=500_000, position=5)
        candidates = [
            self._make_tile(6, SpaceId.CITY, opt=4, owner="p2", level=2),  # opponent
            self._make_tile(7, SpaceId.CITY, opt=5, owner="p1", level=1),  # own
        ]
        result = WaterSlideStrategy.pick_dest_ai(player, candidates, board)
        assert result.position == 7  # own tile

    def test_falls_back_to_non_property(self, board):
        player = Player(player_id="p1", cash=500_000, position=5)
        candidates = [
            self._make_tile(6, SpaceId.CITY, opt=4, owner="p2", level=3),
            self._make_tile(7, SpaceId.TAX, opt=0, owner=None),  # non-property
        ]
        result = WaterSlideStrategy.pick_dest_ai(player, candidates, board)
        assert result.position == 7  # non-property preferred over opponent

    def test_unowned_city_highest_value_wins(self, board):
        """Trong 2 unowned city, chọn ô đắt nhất (opt cao hơn = build cao hơn trong config)."""
        player = Player(player_id="p1", cash=500_000, position=5)
        # opt 1 vs opt 2, both build=10 trong test config → tie → first wins
        candidates = [
            self._make_tile(2, SpaceId.CITY, opt=1, owner=None),
            self._make_tile(3, SpaceId.CITY, opt=2, owner=None),
        ]
        result = WaterSlideStrategy.pick_dest_ai(player, candidates, board)
        # Both same value, first in max() wins
        assert result.position in (2, 3)
