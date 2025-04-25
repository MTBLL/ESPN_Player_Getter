import os
from unittest.mock import MagicMock, patch

import pytest
from playwright.sync_api import Page

from espn_player_getter.models.player import Player
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

    @pytest.mark.skip(reason="Not implemented")
    def test_modal_interaction(self):
        """Test modal opening, extracting data, and closing."""
        with patch("playwright.sync_api.sync_playwright") as mock_playwright:
            # Mock browser, context, and page
            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_new_page = MagicMock()
            mock_context = MagicMock()

            # Setup mock returns
            mock_playwright.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_page.return_value = mock_page
            mock_page.context = mock_context

            # Mock page expectations for modal
            player_name_element = MagicMock()
            player_name_element.inner_text.return_value = "Shohei Ohtani"
            player_row = MagicMock()
            player_row.locator.return_value = player_name_element

            players_rows = MagicMock()
            players_rows.count.return_value = 1
            players_rows.nth.return_value = player_row

            players_table = MagicMock()
            players_table.locator.return_value = players_rows

            # Configure page.locator to return table initially
            mock_page.locator.return_value = players_table

            # Setup expectations for new page
            context_expectation = MagicMock()
            context_expectation.__enter__ = MagicMock(return_value=context_expectation)
            context_expectation.__exit__ = MagicMock(return_value=None)
            context_expectation.value = mock_new_page
            mock_context.expect_page.return_value = context_expectation

            # Set up modal visibility and closing
            mock_page.is_visible.return_value = True  # Modal is visible
            close_button = MagicMock()
            close_button.count.return_value = 1  # Button found

            # Update locator to return close button when looking for it
            def mock_locator(selector):
                if selector == 'div[class*="players-table"]':
                    return players_table
                elif selector == 'button[class*="closebtn"]':
                    return close_button
                else:
                    return MagicMock()

            mock_page.locator = mock_locator
            mock_page.wait_for_selector = MagicMock()

            # Create a scraper and process the page
            with ESPNScraper() as scraper:
                scraper.page = mock_page
                # Mock _scrape_player_data to return a test player
                with patch.object(scraper, "_scrape_player_data") as mock_scrape_data:
                    mock_scrape_data.return_value = Player(
                        id="39832",
                        name="Shohei Ohtani",
                        team="Los Angeles Dodgers",
                        position="DH",
                        eligible_positions=["DH"],
                    )

                    # Call the method
                    players = scraper._process_current_page()

            # Verify the modal interaction
            player_name_element.click.assert_called_once()  # Clicked on player name
            mock_page.click.assert_called_with(
                'text="Complete Stats"'
            )  # Clicked Complete Stats
            mock_new_page.close.assert_called_once()  # Closed the player page
            mock_page.is_visible.assert_called_with(
                'div[role="dialog"]'
            )  # Checked if modal is visible
            close_button.click.assert_called_once()  # Clicked close button on modal
