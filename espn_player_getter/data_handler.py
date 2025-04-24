import json
import os
from pathlib import Path
from typing import List

from espn_player_getter.models.player import Player


def save_players(players: List[Player], output_file: str) -> None:
    """Save player data to a JSON file.
    
    Args:
        players: List of Player objects to save
        output_file: Path to the output file
    """
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Convert players to dictionaries
    players_data = [player.to_dict() for player in players]
    
    # Write to file
    with open(output_file, "w") as f:
        json.dump(players_data, f, indent=2)
    
    print(f"Saved {len(players)} players to {output_file}")


def load_players(input_file: str) -> List[Player]:
    """Load player data from a JSON file.
    
    Args:
        input_file: Path to the input file
        
    Returns:
        List of Player objects
        
    Raises:
        FileNotFoundError: If the input file doesn't exist
        json.JSONDecodeError: If the input file contains invalid JSON
    """
    with open(input_file, "r") as f:
        players_data = json.load(f)
    
    # Convert dictionaries to Player objects
    players = [Player.from_dict(player_data) for player_data in players_data]
    
    print(f"Loaded {len(players)} players from {input_file}")
    return players
