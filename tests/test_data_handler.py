import json
import os
import tempfile

import pytest

from espn_player_getter.data_handler import save_players, load_players
from espn_player_getter.models.player import Player


@pytest.fixture
def sample_players():
    """Create sample players for testing."""
    return [
        Player(
            id="12345",
            name="Mike Trout",
            team="LAA",
            position="CF",
            eligible_positions=["CF", "OF"]
        ),
        Player(
            id="67890",
            name="Aaron Judge",
            team="NYY",
            position="RF",
            eligible_positions=["RF", "OF"],
            is_starter=True,
            stats={"HR": 52, "AVG": 0.311}
        )
    ]


def test_save_and_load_players(sample_players):
    """Test saving and loading players."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        temp_file = tmp.name
    
    try:
        # Save players to the temporary file
        save_players(sample_players, temp_file)
        
        # Verify file exists and has content
        assert os.path.exists(temp_file)
        with open(temp_file, "r") as f:
            data = json.load(f)
            assert len(data) == 2
        
        # Load players from the temporary file
        loaded_players = load_players(temp_file)
        
        # Verify loaded players match original players
        assert len(loaded_players) == len(sample_players)
        
        # Check first player
        assert loaded_players[0].id == sample_players[0].id
        assert loaded_players[0].name == sample_players[0].name
        assert loaded_players[0].team == sample_players[0].team
        
        # Check second player
        assert loaded_players[1].id == sample_players[1].id
        assert loaded_players[1].name == sample_players[1].name
        assert loaded_players[1].stats == sample_players[1].stats
    finally:
        # Clean up temporary file
        os.unlink(temp_file)
