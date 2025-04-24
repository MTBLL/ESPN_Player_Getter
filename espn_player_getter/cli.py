import argparse
import sys
from typing import List

from espn_player_getter.data_handler import save_players
from espn_player_getter.scraper.espn_scraper import ESPNScraper


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Scrape ESPN Fantasy Baseball Player data")
    parser.add_argument(
        "-o", "--output", 
        default="data/espn_players.json",
        help="Output file path for the scraped data (default: data/espn_players.json)"
    )
    parser.add_argument(
        "--no-headless", 
        action="store_true", 
        help="Run browser in visible mode"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Limit the number of players to scrape per category (default: 500)"
    )
    return parser.parse_args()


def run_scraper():
    """Main function to run the scraper.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Scrape player data
        with ESPNScraper(headless=not args.no_headless) as scraper:
            # Scrape players with specified limit
            players = scraper.scrape_players(player_limit=args.limit)
            
            # Save players to file
            save_players(players, args.output)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
