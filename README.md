# ESPN Player Getter

[![codecov](https://codecov.io/gh/MTBLL/ESPN_Player_Getter/graph/badge.svg?token=G7PISZO0A4)](https://codecov.io/gh/MTBLL/ESPN_Player_Getter)

A command-line tool to scrape ESPN Fantasy Baseball Player information using Playwright. This tool serves as the foundation for the MTBL Player Database.

## Installation

This project uses Poetry for dependency management. To install:

```bash
# Install Poetry if you don't have it already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install Playwright browsers
poetry run playwright install
```

## Usage

```bash
# Run using the convenience script
poetry run python run.py

# Or run as a module
poetry run python -m espn_player_getter

# Specify output file
poetry run python run.py -o path/to/output.json

# Run in visible browser mode (not headless)
poetry run python run.py --no-headless

# Set player limit per category (batters and pitchers)
poetry run python run.py --limit 100
```

## Project Structure

```
espn_player_getter/
   models/            # Data models
   scraper/           # Web scraping logic
   __init__.py        # Package initialization
   __main__.py        # Module entry point
   cli.py             # Command-line interface
   data_handler.py    # Data saving/loading utilities

tests/                # Test suite
   ...

run.py                # Convenience runner script
```

## Development

```bash
# Run tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=espn_player_getter
```

## Integration with other tools

This script is designed to be executable from the command line and can be invoked from a coordinating file. For example:

```python
# In your coordinating file
import subprocess

def update_player_database():
    # Run the ESPN Player Getter
    result = subprocess.run(
        ["python", "/path/to/ESPN_Player_Getter/run.py", "-o", "players.json"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
        
    print(f"Success: {result.stdout}")
    return True
```

## Notes

- The scraper navigates to ESPN's fantasy baseball projections page and scrapes both batters and pitchers.
- By default, it captures up to 500 players in each category (batters and pitchers).
- The scraper handles pagination automatically.
- Player data includes name, team, position, and eligible positions.
- Make sure to regularly update the scraping logic as ESPN may change their website structure over time.
- You may need to handle rate limiting, captchas, or other anti-scraping measures.
