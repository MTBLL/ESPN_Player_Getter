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
            eligible_positions=["CF", "OF"],
            image_url="https://example.com/trout.png",
            bio_data={
                "height_weight": "6' 2\", 235 lbs",
                "birthdate": "8/7/1991 (32)",
                "bat_throw": "Right/Right",
                "birthplace": "Vineland, NJ",
                "status": "Active"
            }
        ),
        Player(
            id="67890",
            name="Aaron Judge",
            team="NYY",
            position="RF",
            eligible_positions=["RF", "OF"],
            stats={"HR": 52, "AVG": 0.311},
            image_url="https://example.com/judge.png",
            bio_data={
                "height_weight": "6' 7\", 282 lbs",
                "birthdate": "4/26/1992 (31)",
                "bat_throw": "Right/Right",
                "birthplace": "Sacramento, CA",
                "status": "Active"
            }
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
        assert loaded_players[0].image_url == sample_players[0].image_url
        assert loaded_players[0].bio_data == sample_players[0].bio_data
        
        # Check second player
        assert loaded_players[1].id == sample_players[1].id
        assert loaded_players[1].name == sample_players[1].name
        assert loaded_players[1].stats == sample_players[1].stats
        assert loaded_players[1].image_url == sample_players[1].image_url
        assert loaded_players[1].bio_data == sample_players[1].bio_data
    finally:
        # Clean up temporary file
        os.unlink(temp_file)
