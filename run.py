#!/usr/bin/env python3

"""Convenience script to run the ESPN Player Getter."""

import sys
from espn_player_getter.cli import run_scraper

if __name__ == "__main__":
    sys.exit(run_scraper())
