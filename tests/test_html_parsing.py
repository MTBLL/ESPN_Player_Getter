import os
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import Page

from espn_player_getter.scraper.espn_scraper import ESPNScraper


class TestHTMLParsing:
    """Test parsing of ESPN HTML using the provided sample."""

    @pytest.fixture
    def fixture_html_path(self):
        """Get the path to the player header HTML fixture."""
        return os.path.join(os.path.dirname(__file__), "fixtures", "player_header.html")

    def test_scrape_player_data_from_html(self, page, fixture_html_path):
        """Test parsing player data using a real Page object with our fixture HTML."""
        # Load the fixture HTML into the page
        page.goto(f"file://{fixture_html_path}")

        # Create the scraper
        scraper = ESPNScraper(headless=True)

        # Save the original method
        original_method = scraper._scrape_player_data

        # Create a patched version that uses our hardcoded URL
        def patched_scrape_player_data(page: Page):
            # Create a copy of the page with a mocked url
            mock_page = MagicMock(spec=Page)
            mock_page.url = "https://www.espn.com/mlb/player/id/39832/shohei-ohtani"

            # Copy over the locator method to use the real page's locator
            mock_page.locator = page.locator

            # Call the original method with our modified page
            return original_method(mock_page)

        # Apply the patch
        scraper._scrape_player_data = patched_scrape_player_data

        try:
            # Call the method with our page showing the fixture
            player = scraper._scrape_player_data(page)

            # Verify player data was correctly extracted
            assert player.id == "39832"
            assert player.name == "Shohei Ohtani"
            assert "Dodgers" in player.team
            assert player.position == "DH"
            assert "DH" in player.eligible_positions
            assert (
                "https://a.espncdn.com/combiner/i?img=/i/headshots/mlb/players/full/39832.png"
                in player.image_url
            )

            # Verify bio data
            assert player.bio_data["height_weight"] == "6' 3\", 210 lbs"
            assert player.bio_data["birthdate"] == "7/5/1994"
            assert player.bio_data["bat_throw"] == "Left/Right"
            assert player.bio_data["birthplace"] == "Oshu, Japan"
            assert player.bio_data["status"] == "Active"
        finally:
            # Restore original method
            scraper._scrape_player_data = original_method
