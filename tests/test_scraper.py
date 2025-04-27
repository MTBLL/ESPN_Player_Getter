import os

import pytest

from espn_player_getter.models.player import Player
from espn_player_getter.scraper.espn_scraper import ESPNScraper


@pytest.fixture
def fixture_batters_table_path():
    """Get the path to the player table HTML fixture."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "batters_table.html")


@pytest.fixture
def fixture_pitchers_table_path():
    """Get the path to the player table HTML fixture."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "pitchers_table.html")


@pytest.fixture
def fixture_player_header_path():
    """Get the path to the player header HTML fixture."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "player_header.html")


class TestScraper:
    def test_process_current_page(self, page, fixture_batters_table_path):
        """Test processing the current page of players using a real HTML fixture."""
        # Load the fixture HTML into the page
        page.goto(f"file://{fixture_batters_table_path}")

        scraper = ESPNScraper(
            headless=True, base_url=f"file://{fixture_batters_table_path}"
        )

        # Set the page directly
        scraper.page = page
        # Call the method
        players = scraper._process_current_page()
        # Verify results
        assert len(players) == 50  # We should get players from the fixture
        assert all(isinstance(player, Player) for player in players)

        # Verify first player details (adjust these assertions based on your fixture content)
        first_player = players[0]
        assert first_player.name == "Shohei Ohtani"
        assert first_player.team == "Los Angeles Dodgers"
        assert first_player.eligible_positions == ["DH", "SP"]

    def test_scrape_player_bio(self, page, fixture_player_header_path):
        """Test scraping player bio data from a player page."""
        # Load the fixture HTML into the page
        page.goto(f"file://{fixture_player_header_path}")

        scraper = ESPNScraper(
            headless=True, base_url=f"file://{fixture_player_header_path}"
        )

        # Set the page directly
        scraper.page = page

        # Call the method with the mock page
        bio_data = scraper._scrape_player_bio(scraper.page)

        # Verify bio data was correctly extracted
        assert bio_data["height_weight"] == "6' 3\", 210 lbs"
        assert (
            bio_data["birthdate"] == "7/5/1994"
        )  # Note: date is parsed to remove the age
        assert bio_data["bat_throw"] == "Left/Right"
        assert bio_data["birthplace"] == "Oshu, Japan"
        assert bio_data["status"] == "Active"

    def test_scrape_players(
        self,
        page,
        fixture_batters_table_path,
        fixture_pitchers_table_path,
        fixture_player_header_path,
    ):
        """Test scraping players from both batters and pitchers categories."""
        # Create the scraper without starting a new Playwright instance
        scraper = ESPNScraper(
            headless=True, base_url=f"file://{fixture_batters_table_path}"
        )

        # Save the original click method to restore it later
        original_click = page.click

        def mock_click_handler(selector, **kwargs):
            if 'label:has-text("Pitchers")' in selector:
                # Instead of clicking, load the pitcher fixture
                page.goto(
                    f"file://{fixture_pitchers_table_path}"
                )  # Use the same or a different fixture
            else:
                # For any other click, use the original behavior
                original_click(selector, **kwargs)

        # Replace the click method with our mock
        page.click = mock_click_handler

        try:
            # Set the page directly
            scraper.page = page

            # Call the method
            players = scraper.scrape_players(player_limit=10)

            # Verify results
            assert len(players) == 20  # 10 batters, 10 pitchers
        finally:
            page.click = original_click

    def test_complete_player_details(
        self, page, browser, context, fixture_player_header_path
    ):
        """Test scraping players from a category (batters or pitchers)."""
        page.goto(f"file://{fixture_player_header_path}")

        players = [
            Player(
                id="39832",
                name="Shohei Ohtani",
                team="Los Angeles Dodgers",
                position="DH",
                eligible_positions=["DH", "SP"],
                image_url="https://example.com/player1.png",
                bio_data={},
            )
        ]

        scraper = ESPNScraper(
            headless=True, base_url=f"file://{fixture_batters_table_path}"
        )

        context = browser.new_context()

        with open(fixture_player_header_path, "r") as f:
            player_header_content = f.read()

        # Set up route handler for player detail pages
        # This will intercept any URL that matches the pattern of your player detail pages
        def route_handler(route):
            # Fulfill with our fixture content instead of making the real request
            route.fulfill(
                status=200, body=player_header_content, content_type="text/html"
            )

        # Route pattern should match your ESPN_PLAYER_URL pattern
        # For example if ESPN_PLAYER_URL is "https://www.espn.com/mlb/player/_/id/{player_id}/..."
        context.route("**/mlb/player/**", route_handler)
        scraper.browser = browser
        scraper.context = context
        scraper.page = page

        # Run the test
        players = scraper._complete_player_details(players)
        assert len(players) == 1
        assert players[0].bio_data != {}
        bio_data = players[0].bio_data
        assert bio_data["height_weight"] == "6' 3\", 210 lbs"
        assert bio_data["birthdate"] == "7/5/1994"
        assert bio_data["bat_throw"] == "Left/Right"
        assert bio_data["status"] == "Active"

        scraper.context.unroute("**/mlb/player/**")
