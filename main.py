#!/usr/bin/env python3
"""CTP - Cờ Tỷ Phú AI Simulator.

Run with: python main.py --headless
Output: console + game.log (ghi de moi lan chay)
"""
import argparse
import logging
from ctp.config import ConfigLoader, ConfigError
from ctp.core.board import Board, SpaceId
from ctp.core.models import Player
from ctp.core.events import EventBus, GameEvent, EventType
from ctp.controller import GameController

# Import tiles to register strategies
import ctp.tiles

LOG_FILE = "game.log"

# Root logger: console + file, ca hai deu dung format don gian
_fmt = logging.Formatter("%(message)s")

_console = logging.StreamHandler()
_console.setFormatter(_fmt)

_file = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
_file.setFormatter(_fmt)

logging.root.setLevel(logging.INFO)
logging.root.addHandler(_console)
logging.root.addHandler(_file)

logger = logging.getLogger(__name__)


def create_board(config_loader: ConfigLoader) -> Board:
    """Create Board from ConfigLoader.

    Args:
        config_loader: Loaded configuration.

    Returns:
        Configured Board instance.
    """
    board_config = config_loader.board
    space_positions = {}
    for pos in range(1, 33):
        pos_str = str(pos)
        if pos_str in board_config.SpacePosition0:
            space_data = board_config.SpacePosition0[pos_str]
            space_positions[pos_str] = {
                "spaceId": space_data.spaceId,
                "opt": space_data.opt
            }

    # Build land config for each map
    land_config = {}
    if board_config.LandSpace:
        for map_id, map_data in board_config.LandSpace.items():
            land_config[map_id] = {}
            for land_idx, land_info in map_data.items():
                land_config[map_id][land_idx] = {
                    "color": land_info.color,
                    "building": {
                        k: {"build": v.build, "toll": v.toll}
                        for k, v in land_info.building.items()
                    }
                }

    # Resort config
    resort_config = None
    if board_config.ResortSpace:
        resort_config = {
            "maxUpgrade": board_config.ResortSpace.maxUpgrade,
            "initCost": board_config.ResortSpace.initCost,
            "tollCost": board_config.ResortSpace.tollCost,
            "increaseRate": board_config.ResortSpace.increaseRate
        }

    # Festival config
    festival_config = None
    if board_config.FestivalSpace:
        festival_config = {
            "holdCostRate": board_config.FestivalSpace.holdCostRate,
            "increaseRate": board_config.FestivalSpace.increaseRate,
            "maxFestival": board_config.FestivalSpace.maxFestival
        }

    # Prison config
    prison_config = None
    if board_config.PrisonSpace:
        prison_config = {
            "escapeCostRate": board_config.PrisonSpace.escapeCostRate,
            "limitTurns": board_config.PrisonSpace.limitTurnByMapId.get("1", 3),
        }

    # Travel config
    travel_config = None
    if board_config.TravelSpace:
        travel_config = {
            "travelCostRate": board_config.TravelSpace.travelCostRate,
        }

    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config,
        prison_config=prison_config,
        travel_config=travel_config,
    )


def create_players(config_loader: ConfigLoader, num_players: int = 4) -> list[Player]:
    """Create players with starting cash.

    Args:
        config_loader: Loaded configuration.
        num_players: Number of players to create.

    Returns:
        List of Player instances.
    """
    names = ["A", "B", "C", "D"]
    starting_cash = config_loader.starting_cash
    return [
        Player(player_id=names[i], cash=starting_cash)
        for i in range(num_players)
    ]


def log_event(event: GameEvent, players: list[Player] | None = None):
    """Log game events to console.

    Args:
        event: The game event to log.
        players: Player list for cash lookups on TURN_ENDED.
    """
    pid = event.player_id or ""

    if event.event_type == EventType.DICE_ROLL:
        d = event.data.get('dice', ())
        total = event.data.get('total', 0)
        is_prison_roll = event.data.get('prison_roll', False)
        if is_prison_roll:
            doubles_tag = "  [DOI - THOAT TU!]" if event.data.get('doubles') else "  (khong doi)"
            logger.info(f"  [Dice-Tu] {pid} thu do doi: {d[0]}+{d[1]} = {total}{doubles_tag}")
        else:
            doubles_tag = "  [DOI - duoc do lai!]" if event.data.get('doubles') else ""
            logger.info(f"  [Dice] {pid} tung xuc xac: {d[0]}+{d[1]} = {total}{doubles_tag}")

    elif event.event_type == EventType.PLAYER_MOVE:
        old = event.data.get('old_pos')
        new = event.data.get('new_pos')
        passed = event.data.get("passed_start", False)
        extra = " (qua O xuat phat)" if passed else ""
        logger.info(f"  [Di chuyen] {pid}: o {old} -> o {new}{extra}")

    elif event.event_type == EventType.TILE_LANDED:
        tile_type = event.data.get('tile_type', '?')
        pos = event.data.get('position', '?')
        logger.info(f"  [Dung o] {pid} dung tai o {pos} [{tile_type}]")

    elif event.event_type == EventType.PROPERTY_PURCHASED:
        pos = event.data.get('position', '?')
        price = event.data.get('price', 0)
        prop = event.data.get('property', '')
        if prop == 'Resort':
            logger.info(f"  [Mua Resort] {pid} mua Resort (o {pos}) gia ${int(price):,}")
        else:
            built_levels = event.data.get('built_levels', [1])
            levels_str = ", ".join(_LEVEL_NAMES.get(str(l), str(l)).strip() for l in built_levels)
            logger.info(f"  [Mua dat] {pid} mua {levels_str} (o {pos}) gia ${int(price):,}")

    elif event.event_type == EventType.PROPERTY_ACQUIRED:
        pos = event.data.get('position', '?')
        from_p = event.data.get('from_player', '?')
        price = event.data.get('price', 0)
        logger.info(f"  [Cuop dat] {pid} cuop dat o {pos} tu {from_p}, tra ${int(price):,}")

    elif event.event_type == EventType.PROPERTY_UPGRADED:
        pos = event.data.get('position', '?')
        new_level = event.data.get('new_level', '?')
        cost = event.data.get('cost', 0)
        level_name = _LEVEL_NAMES.get(str(new_level), f"cap {new_level}")
        logger.info(f"  [Nang cap] {pid} nang cap o {pos} -> {level_name.strip()}, chi ${int(cost):,}")

    elif event.event_type == EventType.RENT_OWED:
        amount = event.data.get('amount', 0)
        recipient = event.data.get('recipient', '?')
        pos = event.data.get('position', '?')
        logger.info(f"  [No thue] {pid} phai tra cho {recipient} ${int(amount):,} (o {pos}) — khong du tien")

    elif event.event_type == EventType.DEBT_SETTLED:
        creditor = event.data.get('creditor', '?')
        owed = event.data.get('owed', 0)
        paid = event.data.get('paid', 0)
        logger.info(f"  [Thanh toan no] {creditor} nhan duoc tu {pid}: ${int(paid):,} / ${int(owed):,} (con thieu ${int(owed-paid):,})")

    elif event.event_type == EventType.RENT_PAID:
        amount = event.data.get('amount', 0)
        recipient = event.data.get('recipient', '?')
        pos = event.data.get('position', '?')
        golden_tag = " [DAT VANG x2]" if event.data.get('is_golden') else ""
        logger.info(f"  [Thu tien] {pid} tra tien thue ${int(amount):,} cho {recipient} (o {pos}){golden_tag}")

    elif event.event_type == EventType.TAX_PAID:
        amount = event.data.get('amount', 0)
        reason = event.data.get('reason', '')
        if reason == 'prison_escape':
            logger.info(f"  [Thoat tu] {pid} tra phi ${int(amount):,} de ra tu")
        else:
            logger.info(f"  [Thue] {pid} dong thue ${int(amount):,}")

    elif event.event_type == EventType.BONUS_RECEIVED:
        amount = event.data.get('amount', 0)
        reason = event.data.get('reason', '')
        if reason == 'doubles_reroll':
            logger.info(f"  [Do doi] {pid} do doi - duoc do them 1 lan nua!")
        else:
            reason_str = f" ({reason})" if reason else ""
            logger.info(f"  [Nhan tien] {pid} nhan ${int(amount):,}{reason_str}")

    elif event.event_type == EventType.PRISON_ENTERED:
        turns = event.data.get('turns', 0)
        reason = event.data.get('reason', '')
        if reason == 'triple_doubles':
            logger.info(f"  [Nguc] {pid} do doi 3 lan lien tiep - vao TU NGAY!")
        else:
            logger.info(f"  [Nguc] {pid} bi giam vao tu, ngoi {turns} luot")

    elif event.event_type == EventType.PRISON_EXITED:
        reason = event.data.get('reason', '')
        if reason == 'paid':
            logger.info(f"  [Nguc] {pid} da tra phi - tu do!")
        elif reason == 'served':
            logger.info(f"  [Nguc] {pid} man han tu - tu do!")
        elif reason == 'doubles':
            logger.info(f"  [Nguc] {pid} do doi trong tu - tu do!")
        else:
            logger.info(f"  [Nguc] {pid} ra tu")

    elif event.event_type == EventType.FESTIVAL_UPDATED:
        level = event.data.get('level', 0)
        reward = event.data.get('reward', 0)
        logger.info(f"  [Le hoi] Cap do: {level}, Phan thuong: ${int(reward):,}")

    elif event.event_type == EventType.CARD_DRAWN:
        card_id = event.data.get('card_id', '?')
        effect = event.data.get('effect', '')
        effect_str = f" -> {effect}" if effect else ""
        logger.info(f"  [Rut the] {pid} rut the '{card_id}'{effect_str}")

    elif event.event_type == EventType.PROPERTY_SOLD:
        pos = event.data.get('position', '?')
        value = event.data.get('value', 0)
        logger.info(f"  [Ban dat] {pid} ban dat o {pos} thu ${int(value):,}")

    elif event.event_type == EventType.MINIGAME_RESULT:
        result = event.data.get('result', '?')
        bet = event.data.get('bet', 0)
        gain = event.data.get('result', 0)
        logger.info(f"  [MiniGame] {pid}: {'THANG' if event.data.get('won') else 'THUA'}, cuoc ${int(bet):,}, nhan lai ${int(gain):,}")

    elif event.event_type == EventType.PLAYER_BANKRUPT:
        logger.info(f"  [Pha san] *** {pid} DA PHA SAN ***")

    elif event.event_type == EventType.TURN_STARTED:
        reason = event.data.get("reason", "")
        turn = event.data.get('turn', '?')
        if reason == "in_prison":
            logger.info(f"\n{'─'*50}")
            logger.info(f"  LUOT {turn}: Nguoi choi {pid} (dang ngoi tu)")
            logger.info(f"{'─'*50}")
        else:
            logger.info(f"\n{'─'*50}")
            logger.info(f"  LUOT {turn}: Nguoi choi {pid}")
            logger.info(f"{'─'*50}")
        # Show player state at start of turn
        if players:
            p = next((x for x in players if x.player_id == pid), None)
            if p:
                props = p.owned_properties if p.owned_properties else []
                logger.info(f"  [Trang thai] Vi tri: o {p.position} | Tien: ${int(p.cash):,} | Dat: {props if props else 'chua co'}")

    elif event.event_type == EventType.TURN_ENDED:
        if players:
            p = next((x for x in players if x.player_id == pid), None)
            if p and not p.is_bankrupt:
                props = p.owned_properties if p.owned_properties else []
                logger.info(f"  [Ket thuc luot] Tien: ${int(p.cash):,} | Dat: {props if props else 'chua co'}")

    elif event.event_type == EventType.GAME_STARTED:
        logger.info(f"[Game] Bat dau voi {len(event.data.get('players', []))} nguoi choi")

    elif event.event_type == EventType.GAME_ENDED:
        reason = event.data.get("reason", "unknown")
        turns = event.data.get("turns", "?")
        if reason == "last_player_standing":
            logger.info(f"\n[Game] Ket thuc: Con 1 nguoi con tien sau {turns} luot")
        elif reason == "max_turns":
            logger.info(f"\n[Game] Ket thuc: Het {turns} luot")
        else:
            logger.info(f"\n[Game] Ket thuc ({reason}) sau {turns} luot")


_SPACE_LABELS = {
    1: "LE HOI",
    2: "RUT THE",
    3: "DAT",
    4: "MINIGAME",
    5: "NHA TU",
    6: "KHU NGHI DUONG",
    7: "XUAT PHAT",
    8: "THUE",
    9: "DU LICH",
    10: "THAN MAY MAN",
    40: "CON TRUOT NUOC",
}

_COLOR_NAMES = {
    1: "Vang nhat",
    2: "Vang dam",
    3: "Cam",
    4: "Do",
    5: "Tim nhat",
    6: "Tim dam",
    7: "Xanh duong",
    8: "Xanh la",
}

_LEVEL_NAMES = {
    "1": "Cam co  ",
    "2": "Nha L1  ",
    "3": "Nha L2  ",
    "4": "Nha L3  ",
    "5": "Landmark",
}

_SIDES = [
    ("CANH 1 (O 1-8)",   range(1, 9)),
    ("CANH 2 (O 9-16)",  range(9, 17)),
    ("CANH 3 (O 17-24)", range(17, 25)),
    ("CANH 4 (O 25-32)", range(25, 33)),
]


def _land_lines(board: "Board", tile) -> list[str]:
    """Return lines describing a land tile with all 5 building levels."""
    cfg = board.get_land_config(tile.opt)
    if not cfg:
        return [f"    o{tile.position:>2}  DAT #{tile.opt}  (khong co config)"]

    color = cfg.get("color", "?")
    color_name = _COLOR_NAMES.get(color, f"mau {color}")
    buildings = cfg.get("building", {})

    lines = []
    lines.append(f"    o{tile.position:>2}  [DAT #{tile.opt}]  Mau: {color_name} (nhom {color})")
    lines.append(f"          {'Cap':<10} {'Xay them':>10}  {'Tien thue':>10}")
    lines.append(f"          {'─'*10} {'─'*10}  {'─'*10}")
    for lvl in ["1", "2", "3", "4", "5"]:
        b = buildings.get(lvl, {})
        build_cost = int(b.get("build", 0) * 1000)
        toll = int(b.get("toll", 0) * 1000)
        lvl_name = _LEVEL_NAMES[lvl]
        lines.append(f"          {lvl_name:<10} {f'${build_cost:,}':>10}  {f'${toll:,}':>10}")
    return lines


def log_board(board: "Board") -> None:
    """Log toan bo ban do nhom theo 4 canh, tung nhom mau, du 5 cap nha."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("BAN DO - 32 O (4 canh x 8 o)")
    logger.info("=" * 70)

    resort_cfg = board.get_resort_config()

    for side_label, pos_range in _SIDES:
        logger.info("")
        logger.info(f"  ┌─ {side_label} " + "─" * (50 - len(side_label)))

        # collect color groups on this side for summary
        color_groups: dict[int, list] = {}

        for pos in pos_range:
            tile = board.get_tile(pos)
            sid = tile.space_id

            if sid == 3:  # DAT
                cfg = board.get_land_config(tile.opt)
                color = cfg.get("color", 0) if cfg else 0
                color_groups.setdefault(color, []).append(tile)

        # Print color group summary for this side
        for color, tiles in sorted(color_groups.items()):
            cname = _COLOR_NAMES.get(color, f"mau {color}")
            positions = [f"o{t.position}" for t in tiles]
            logger.info(f"  │  Nhom mau {color} ({cname}): {', '.join(positions)}")

        logger.info(f"  │")

        # Print each tile on this side
        for pos in pos_range:
            tile = board.get_tile(pos)
            sid = tile.space_id
            label = _SPACE_LABELS.get(sid, f"? ({sid})")

            if sid == 3:  # DAT — full detail
                golden_tag = "  *** DAT VANG x2 ***" if tile.is_golden else ""
                for line in _land_lines(board, tile):
                    logger.info(f"  │{line}")
                if tile.is_golden:
                    logger.info(f"  │          *** O DAT VANG - phi check in x2 ***")

            elif sid == 6:  # RESORT
                golden_tag = "  *** DAT VANG x2 ***" if tile.is_golden else ""
                if resort_cfg:
                    buy = int(resort_cfg['initCost'] * 1000)
                    toll_base = int(resort_cfg['tollCost'] * 1000)
                    rate = resort_cfg.get('increaseRate', 1)
                    max_lvl = resort_cfg.get('maxUpgrade', 5)
                    logger.info(f"  │    o{pos:>2}  [{label}]  mua=${buy:,}  thue_cap1=${toll_base:,}  rate=x{rate}  max_cap={max_lvl}{golden_tag}")
                else:
                    logger.info(f"  │    o{pos:>2}  [{label}]{golden_tag}")

            elif sid == 1:  # FESTIVAL
                logger.info(f"  │    o{pos:>2}  [{label}]  cap hien tai: {board.festival_level}")

            else:
                logger.info(f"  │    o{pos:>2}  [{label}]")

        logger.info(f"  └" + "─" * 55)

    logger.info("")
    logger.info("=" * 70)


def log_players(players: list[Player]) -> None:
    """Log thong tin khoi tao cua tung nguoi choi."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("NGUOI CHOI")
    logger.info("=" * 60)
    for p in players:
        logger.info(f"  Nguoi choi {p.player_id}:")
        logger.info(f"    Vi tri bat dau : O {p.position} (XUAT PHAT)")
        logger.info(f"    Tien            : ${int(p.cash):,}")
        logger.info(f"    Bat dong san    : Chua co")
    logger.info("=" * 60)


def run_headless(config_loader: ConfigLoader, num_players: int = 4, max_turns: int | None = None):
    """Run game headless with console output.

    Args:
        config_loader: Loaded configuration.
        num_players: Number of players (2-4).
        max_turns: Override for max turns (uses config default if None).
    """
    logger.info("=" * 60)
    logger.info("CTP - Co Ty Phu AI Simulator (Headless)")
    logger.info("=" * 60)

    # Use config max_turns unless overridden
    game_max_turns = max_turns if max_turns is not None else config_loader.max_turns

    logger.info(f"So nguoi choi : {num_players}")
    logger.info(f"So luot toi da: {game_max_turns}")
    logger.info(f"Tien khoi dau : ${int(config_loader.starting_cash):,}")
    logger.info("=" * 60)

    # Create game components
    board = create_board(config_loader)
    players = create_players(config_loader, num_players)
    event_bus = EventBus()

    # Chon ngau nhien 3 o dat vang (CITY hoac RESORT) cho van dau nay
    import random as _random
    _property_tiles = [t for t in board.board if t.space_id in (SpaceId.CITY, SpaceId.RESORT)]
    _golden_tiles = _random.sample(_property_tiles, min(3, len(_property_tiles)))
    for _t in _golden_tiles:
        _t.is_golden = True
    logger.info(f"[Dat vang] 3 o dat vang van nay: {[t.position for t in _golden_tiles]}")

    # Log board map and player info before game starts
    log_board(board)
    log_players(players)

    logger.info("")
    logger.info("=" * 60)
    logger.info("BAT DAU VAN DAU")
    logger.info("=" * 60)

    # Subscribe to all events for logging — pass players for state snapshots
    handler = lambda event: log_event(event, players)
    for event_type in EventType:
        event_bus.subscribe(event_type, handler)

    # Create game controller
    controller = GameController(
        board=board,
        players=players,
        max_turns=game_max_turns,
        event_bus=event_bus,
        starting_cash=config_loader.starting_cash,
    )

    # Publish game start
    event_bus.publish(GameEvent(
        event_type=EventType.GAME_STARTED,
        data={"players": [p.player_id for p in players]}
    ))

    # Run game loop
    turn_count = 0
    while not controller.is_game_over():
        controller.step()
        turn_count += 1
        # Safety limit to prevent infinite loop
        if turn_count > game_max_turns * len(players) * 10:
            logger.warning("Safety limit reached - ending game")
            break

    # Game over - log summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("KET QUA VAN DAU")
    logger.info("=" * 60)
    logger.info(f"Tong so luot: {controller.current_turn}")
    winner = controller._get_winner()
    logger.info(f"NGUOI THANG: {winner}")
    logger.info("")
    logger.info("Xep hang cuoi van:")
    for rank, p in enumerate(sorted(players, key=lambda x: (not x.is_bankrupt, x.cash), reverse=True), 1):
        if p.is_bankrupt:
            logger.info(f"  #{rank} Nguoi choi {p.player_id}: PHA SAN")
        else:
            logger.info(f"  #{rank} Nguoi choi {p.player_id}: ${int(p.cash):,}")
            if p.owned_properties:
                logger.info(f"      Dat dang so huu: {p.owned_properties}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="CTP - Cờ Tỷ Phú AI Simulator")
    parser.add_argument("--headless", action="store_true", help="Run game without visualization")
    parser.add_argument("--players", type=int, default=4, help="Number of players (2-4)")
    parser.add_argument("--turns", type=int, default=None, help="Override max turns")
    args = parser.parse_args()

    if not args.headless:
        print("Visualization not implemented yet. Use --headless flag.")
        return 1

    # Validate player count
    if args.players < 2 or args.players > 4:
        print("Number of players must be between 2 and 4")
        return 1

    # Load config
    try:
        config_loader = ConfigLoader()
        config_loader.load_all()
        run_headless(config_loader, args.players, args.turns)

    except ConfigError as e:
        logger.error(f"Config error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())