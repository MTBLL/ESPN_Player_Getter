import os
import pytest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
from playwright.sync_api import Page

from espn_player_getter.scraper.espn_scraper import ESPNScraper
from espn_player_getter.models.player import Player


class TestHTMLParsing:
    """Test parsing of ESPN HTML using the provided sample."""

    @pytest.fixture
    def player_header_html(self):
        """Read the player header HTML fixture."""
        fixture_path = os.path.join(
            os.path.dirname(__file__), 
            "fixtures", 
            "player_header.html"
        )
        with open(fixture_path, "r") as f:
            return f.read()

    @pytest.fixture
    def mock_player_page(self, player_header_html):
        """Create a mock player page with our HTML fixture."""
        mock_page = MagicMock(spec=Page)
        
        # Mock URL for player ID
        mock_url = MagicMock()
        mock_url.split.return_value = ["https:", "", "www.espn.com", "mlb", "player", "_", "id", "39832", "shohei-ohtani"]
        mock_page.url = mock_url
        
        # Create a mock content method for locator
        def mock_inner_html(selector=None):
            # If it's the root selector for the player header, return the full fixture
            if selector == "div.PlayerHeader":
                return player_header_html
            
            # Otherwise, parse the HTML and extract the relevant part
            soup = BeautifulSoup(player_header_html, 'html.parser')
            
            if selector == "h1":
                # Get player name from h1
                h1 = soup.select_one("h1.PlayerHeader__Name")
                return h1.text if h1 else ""
                
            elif selector == 'li:has-text("Team")':
                # Get team info
                team_info = soup.select_one("div.PlayerHeader__Team")
                return team_info.text if team_info else ""
                
            elif selector == 'li:has-text("Position")':
                # Position is in the third li
                position_li = soup.select("ul.PlayerHeader__Team_Info li")[2] if len(soup.select("ul.PlayerHeader__Team_Info li")) >= 3 else None
                return position_li.text if position_li else ""
                
            elif selector == 'figure.PlayerHeader__HeadShot img':
                # Get player headshot image
                img = soup.select_one("figure.PlayerHeader__HeadShot img")
                if img and img.has_attr('src'):
                    mock_element = MagicMock()
                    mock_element.count.return_value = 1
                    mock_element.get_attribute.return_value = img['src']
                    return mock_element
                return MagicMock()
                
            elif selector == 'ul.PlayerHeader__Bio_List li':
                # Get bio list items
                bio_items = soup.select("ul.PlayerHeader__Bio_List li")
                if bio_items:
                    mock_element = MagicMock()
                    mock_element.count.return_value = len(bio_items)
                    
                    # Create a list to store bio data for each item
                    mock_bio_items = []
                    
                    for item in bio_items:
                        label_div = item.select_one("div.ttu")
                        value_div = item.select_one("div.fw-medium")
                        
                        label = label_div.text if label_div else ""
                        value = value_div.text if value_div else ""
                        
                        # Create a mock for this bio item
                        mock_item = MagicMock()
                        
                        # Create mocks for the label and value elements
                        mock_label = MagicMock()
                        mock_label.count.return_value = 1
                        mock_label.inner_text.return_value = label
                        
                        mock_value = MagicMock()
                        mock_value.count.return_value = 1
                        mock_value.inner_text.return_value = value
                        
                        # Setup locator to return the appropriate mock element
                        def create_locator_fn(label_el, value_el):
                            def locator_fn(selector):
                                if selector == "div.ttu":
                                    return label_el
                                elif selector == "div.fw-medium":
                                    return value_el
                                return MagicMock()
                            return locator_fn
                        
                        mock_item.locator = create_locator_fn(mock_label, mock_value)
                        mock_bio_items.append(mock_item)
                    
                    # Set up nth method to return the appropriate bio item
                    def nth_fn(index):
                        if 0 <= index < len(mock_bio_items):
                            return mock_bio_items[index]
                        return MagicMock()
                    
                    mock_element.nth = nth_fn
                    return mock_element
                
                return MagicMock()
            
            return MagicMock()
        
        # Create a locator function that returns elements with inner_html implemented
        def mock_locator(selector):
            mock_element = MagicMock()
            
            # Implement specific selectors
            if selector == "div.PlayerHeader":
                mock_element.inner_text = MagicMock(return_value="Player Header")
                mock_element.locator = mock_locator
            else:
                result = mock_inner_html(selector)
                if isinstance(result, MagicMock):
                    return result
                
                # Create a text representation for string results
                if isinstance(result, str):
                    mock_element.inner_text = MagicMock(return_value=result)
                    mock_element.count = MagicMock(return_value=1 if result else 0)
            
            return mock_element
        
        mock_page.locator = mock_locator
        
        return mock_page
        
    def test_scrape_player_data_from_html(self, mock_player_page):
        """Test parsing player data from the ESPN player page HTML."""
        # Create the scraper
        scraper = ESPNScraper(headless=True)
        
        # Call the method with our mocked page
        player = scraper._scrape_player_data(mock_player_page)
        
        # Verify player data was correctly extracted
        assert player.id == "39832"
        assert "Shohei" in player.name  # Name is somewhere in the player name
        assert "Ohtani" in player.name  # Name is somewhere in the player name
        assert "Dodgers" in player.team  # Team name contains "Dodgers" 
        assert player.position == "DH"
        assert "DH" in player.eligible_positions
        assert "https://a.espncdn.com/combiner/i?img=/i/headshots/mlb/players/full/39832.png" in player.image_url
        
        # Verify bio data
        assert player.bio_data["height_weight"] == "6' 3\", 210 lbs"
        assert player.bio_data["birthdate"] == "7/5/1994 (30)"
        assert player.bio_data["bat_throw"] == "Left/Right"
        assert player.bio_data["birthplace"] == "Oshu, Japan"
        assert player.bio_data["status"] == "Active"
    
    def test_modal_interaction(self):
        """Test modal opening, extracting data, and closing."""
        with patch('playwright.sync_api.sync_playwright') as mock_playwright:
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
            
            # Create a scraper and process the page
            with ESPNScraper() as scraper:
                scraper.page = mock_page
                # Mock _scrape_player_data to return a test player
                with patch.object(scraper, '_scrape_player_data') as mock_scrape_data:
                    mock_scrape_data.return_value = Player(
                        id="39832",
                        name="Shohei Ohtani",
                        team="Los Angeles Dodgers",
                        position="DH",
                        eligible_positions=["DH"]
                    )
                    
                    # Call the method
                    players = scraper._process_current_page()
            
            # Verify the modal interaction
            player_name_element.click.assert_called_once()  # Clicked on player name
            mock_page.click.assert_called_with('text="Complete Stats"')  # Clicked Complete Stats
            mock_new_page.close.assert_called_once()  # Closed the player page
            mock_page.is_visible.assert_called_with('div[role="dialog"]')  # Checked if modal is visible
            close_button.click.assert_called_once()  # Clicked close button on modal