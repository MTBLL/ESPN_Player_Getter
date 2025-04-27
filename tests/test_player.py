from espn_player_getter.models.player import Player


def test_player_to_dict():
    """Test converting Player to dictionary."""
    player = Player(
        id="12345",
        name="Mike Trout",
        team="LAA",
        position="CF",
        eligible_positions=["CF", "OF"],
        stats={"HR": 40, "AVG": 0.300},
        image_url="https://example.com/image.png",
        bio_data={
            "height_weight": "6' 2\", 235 lbs",
            "birthdate": "8/7/1991 (32)",
            "bat_throw": "Right/Right",
            "birthplace": "Vineland, NJ",
            "status": "Active",
        },
    )

    player_dict = player.to_dict()

    assert player_dict["id"] == "12345"
    assert player_dict["name"] == "Mike Trout"
    assert player_dict["team"] == "LAA"
    assert player_dict["position"] == "CF"
    assert player_dict["eligible_positions"] == ["CF", "OF"]
    assert player_dict["stats"] == {"HR": 40, "AVG": 0.300}
    assert player_dict["image_url"] == "https://example.com/image.png"
    assert player_dict["bio_data"]["height_weight"] == "6' 2\", 235 lbs"
    assert player_dict["bio_data"]["birthdate"] == "8/7/1991 (32)"
    assert player_dict["bio_data"]["bat_throw"] == "Right/Right"
    assert player_dict["bio_data"]["birthplace"] == "Vineland, NJ"
    assert player_dict["bio_data"]["status"] == "Active"


def test_player_from_dict():
    """Test creating Player from dictionary."""
    player_dict = {
        "id": "12345",
        "name": "Mike Trout",
        "team": "LAA",
        "position": "CF",
        "eligible_positions": ["CF", "OF"],
        "stats": {"HR": 40, "AVG": 0.300},
        "image_url": "https://example.com/image.png",
        "bio_data": {
            "height_weight": "6' 2\", 235 lbs",
            "birthdate": "8/7/1991 (32)",
            "bat_throw": "Right/Right",
            "birthplace": "Vineland, NJ",
            "status": "Active",
        },
    }

    player = Player.from_dict(player_dict)

    assert player.id == "12345"
    assert player.name == "Mike Trout"
    assert player.team == "LAA"
    assert player.position == "CF"
    assert player.eligible_positions == ["CF", "OF"]
    assert player.stats == {"HR": 40, "AVG": 0.300}
    assert player.image_url == "https://example.com/image.png"
    assert player.bio_data["height_weight"] == "6' 2\", 235 lbs"
    assert player.bio_data["birthdate"] == "8/7/1991 (32)"
    assert player.bio_data["bat_throw"] == "Right/Right"
    assert player.bio_data["birthplace"] == "Vineland, NJ"
    assert player.bio_data["status"] == "Active"


def test_player_from_dict_minimal():
    """Test creating Player from dictionary with minimal fields."""
    player_dict = {
        "id": "67890",
        "name": "Aaron Judge",
        "team": "NYY",
        "position": "RF",
        "eligible_positions": ["RF", "OF"],
    }

    player = Player.from_dict(player_dict)

    assert player.id == "67890"
    assert player.name == "Aaron Judge"
    assert player.team == "NYY"
    assert player.position == "RF"
    assert player.eligible_positions == ["RF", "OF"]
    assert player.stats is None
    assert player.image_url == ""
    assert player.bio_data == {}
