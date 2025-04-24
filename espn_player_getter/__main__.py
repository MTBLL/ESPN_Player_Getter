import sys
from espn_player_getter.cli import run_scraper


def main():
    """Main entry point for the application."""
    sys.exit(run_scraper())


if __name__ == "__main__":
    main()
