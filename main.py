#!/usr/bin/env python3
"""CTP - Cờ Tỷ Phú AI Simulator.

Run with: python main.py --headless
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

# Configure logging for headless output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
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

    return Board(
        space_positions=space_positions,
        land_config=land_config,
        resort_config=resort_config,
        festival_config=festival_config
    )


def create_players(config_loader: ConfigLoader, num_players: int = 4) -> list[Player]:
    """Create players with starting cash.

    Args:
        config_loader: Loaded configuration.
        num_players: Number of players to create.

    Returns:
        List of Player instances.
    """
    starting_cash = config_loader.starting_cash
    return [
        Player(player_id=f"Player{i+1}", cash=starting_cash)
        for i in range(num_players)
    ]


def log_event(event: GameEvent):
    """Log game events to console.

    Args:
        event: The game event to log.
    """
    if event.event_type == EventType.DICE_ROLL:
        logger.info(f"  [Dice] Rolled {event.data.get('dice')} (total: {event.data.get('total')})")
    elif event.event_type == EventType.PLAYER_MOVE:
        passed = event.data.get("passed_start", False)
        start_msg = " (passed Start, +15% bonus)" if passed else ""
        logger.info(f"  [Move] Position {event.data.get('old_pos')} -> {event.data.get('new_pos')}{start_msg}")
    elif event.event_type == EventType.TILE_LANDED:
        logger.info(f"  [Tile] Landed on {event.data.get('tile_type')}")
    elif event.event_type == EventType.PROPERTY_PURCHASED:
        logger.info(f"  [Buy] Purchased {event.data.get('property')} for ${event.data.get('price')}")
    elif event.event_type == EventType.RENT_PAID:
        logger.info(f"  [Rent] Paid ${event.data.get('amount')} to {event.data.get('recipient')}")
    elif event.event_type == EventType.TAX_PAID:
        logger.info(f"  [Tax] Paid ${event.data.get('amount')}")
    elif event.event_type == EventType.BONUS_RECEIVED:
        logger.info(f"  [Bonus] Received ${event.data.get('amount')}")
    elif event.event_type == EventType.PRISON_ENTERED:
        logger.info(f"  [Prison] Sent to prison for {event.data.get('turns')} turns")
    elif event.event_type == EventType.PRISON_EXITED:
        logger.info(f"  [Prison] Released from prison")
    elif event.event_type == EventType.FESTIVAL_UPDATED:
        logger.info(f"  [Festival] Level: {event.data.get('level')}, Reward: ${event.data.get('reward')}")
    elif event.event_type == EventType.CARD_DRAWN:
        logger.info(f"  [Card] Drew: {event.data.get('card_id', 'unknown')}")
    elif event.event_type == EventType.PROPERTY_SOLD:
        logger.info(f"  [Sell] Sold property at position {event.data.get('position')} for ${event.data.get('value')}")
    elif event.event_type == EventType.PLAYER_BANKRUPT:
        logger.info(f"  [Bankrupt] {event.player_id} is BANKRUPT!")
    elif event.event_type == EventType.TURN_STARTED:
        reason = event.data.get("reason", "")
        if reason == "in_prison":
            logger.info(f"--- Turn {event.data.get('turn')}: {event.player_id} (in prison) ---")
        else:
            logger.info(f"--- Turn {event.data.get('turn')}: {event.player_id} ---")
    elif event.event_type == EventType.TURN_ENDED:
        player = event.player_id
        # Get player cash from controller context if available
        logger.info(f"  [Turn End] {player} turn complete")
    elif event.event_type == EventType.GAME_STARTED:
        logger.info(f"[Game] Started with {len(event.data.get('players', []))} players")
    elif event.event_type == EventType.GAME_ENDED:
        reason = event.data.get("reason", "unknown")
        logger.info(f"[Game] Ended ({reason})")


def run_headless(config_loader: ConfigLoader, num_players: int = 4, max_turns: int | None = None):
    """Run game headless with console output.

    Args:
        config_loader: Loaded configuration.
        num_players: Number of players (2-4).
        max_turns: Override for max turns (uses config default if None).
    """
    logger.info("=" * 60)
    logger.info("CTP - Cờ Tỷ Phú AI Simulator (Headless)")
    logger.info("=" * 60)

    # Use config max_turns unless overridden
    game_max_turns = max_turns if max_turns is not None else config_loader.max_turns

    logger.info(f"Players: {num_players}")
    logger.info(f"Max turns: {game_max_turns}")
    logger.info(f"Starting cash: ${config_loader.starting_cash}")
    logger.info("=" * 60)

    # Create game components
    board = create_board(config_loader)
    players = create_players(config_loader, num_players)
    event_bus = EventBus()

    # Subscribe to all events for logging
    for event_type in EventType:
        event_bus.subscribe(event_type, log_event)

    # Create game controller
    controller = GameController(
        board=board,
        players=players,
        max_turns=game_max_turns,
        event_bus=event_bus
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
    logger.info("GAME OVER")
    logger.info("=" * 60)
    logger.info(f"Total turns: {controller.current_turn}")
    winner = controller._get_winner()
    logger.info(f"Winner: {winner}")

    logger.info("")
    logger.info("Final standings:")
    for p in sorted(players, key=lambda x: x.cash, reverse=True):
        if p.is_bankrupt:
            status = "BANKRUPT"
        else:
            status = f"${int(p.cash)}"
        logger.info(f"  {p.player_id}: {status}")
        if p.owned_properties:
            logger.info(f"    Properties: {p.owned_properties}")


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