import pytest
from unittest.mock import MagicMock, patch

from espn_player_getter.scraper.espn_scraper import ESPNScraper
from espn_player_getter.models.player import Player


@pytest.fixture
def mock_page():
    """Create a mock page object for testing."""
    mock_page = MagicMock()
    
    # Setup typical page structure
    mock_page.goto = MagicMock()
    mock_page.wait_for_load_state = MagicMock()
    mock_page.locator = MagicMock(return_value=mock_page)
    mock_page.click = MagicMock()
    
    # Make count return something reasonable for player rows
    mock_page.count = MagicMock(return_value=5)
    
    # Setup for player row processing
    mock_page.nth = MagicMock(return_value=mock_page)
    mock_page.inner_text = MagicMock(return_value="Player Name")
    
    # Setup for browser/playwright context
    mock_context = MagicMock()
    mock_context.expect_page = MagicMock()
    mock_page.context = mock_context
    
    # Set up wait_for_selector to not actually wait
    mock_page.wait_for_selector = MagicMock()
    
    # Set up is_visible for modal detection
    mock_page.is_visible = MagicMock(return_value=True)
    
    # Setup mock URL that will be parsed for player ID
    mock_page.url = "https://www.espn.com/mlb/player/_/id/12345"
    
    # Setup for player page
    mock_player_page = MagicMock()
    mock_player_page.url = "https://www.espn.com/mlb/player/_/id/12345"
    mock_player_page.locator = MagicMock(return_value=mock_player_page)
    mock_player_page.inner_text = MagicMock(return_value="Player Name")
    mock_player_page.wait_for_load_state = MagicMock()
    mock_player_page.count = MagicMock(return_value=1)
    mock_player_page.close = MagicMock()
    
    # Make expect_page return mock_player_page
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__ = MagicMock(return_value=mock_context_manager)
    mock_context_manager.__exit__ = MagicMock(return_value=None)
    mock_context_manager.value = mock_player_page
    mock_context.expect_page.return_value = mock_context_manager
    
    return mock_page


@pytest.fixture
def mock_playwright():
    """Create a mock playwright object for testing."""
    mock_playwright = MagicMock()
    
    # Set up the browser
    mock_browser = MagicMock()
    mock_browser.new_page = MagicMock()
    mock_playwright.chromium.launch = MagicMock(return_value=mock_browser)
    
    return mock_playwright


@patch('espn_player_getter.scraper.espn_scraper.sync_playwright')
def test_scraper_initialization(mock_sync_playwright, mock_playwright):
    """Test scraper initialization."""
    mock_sync_playwright.return_value.start.return_value = mock_playwright
    
    with ESPNScraper(headless=True) as scraper:
        assert scraper.headless is True
        assert scraper.playwright is not None
        assert scraper.browser is not None
        assert scraper.page is not None
    
    # Verify resources are cleaned up
    mock_playwright.stop.assert_called_once()


@patch('espn_player_getter.scraper.espn_scraper.sync_playwright')
def test_process_current_page(mock_sync_playwright, mock_page, mock_playwright):
    """Test processing the current page of players."""
    # Setup mocks
    mock_sync_playwright.return_value.start.return_value = mock_playwright
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_page.return_value = mock_page
    
    with ESPNScraper(headless=True) as scraper:
        # Override the page with our mock
        scraper.page = mock_page
        
        # Call the method
        players = scraper._process_current_page()
        
        # Verify results
        assert len(players) == 5  # We set count to return 5
        assert all(isinstance(player, Player) for player in players)


@patch('espn_player_getter.scraper.espn_scraper.sync_playwright')
def test_scrape_player_data(mock_sync_playwright, mock_page, mock_playwright):
    """Test scraping player data from a player page."""
    # Setup mocks
    mock_sync_playwright.return_value.start.return_value = mock_playwright
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_page.return_value = mock_page
    
    # Mock the split method
    mock_page.url = MagicMock()
    mock_split_result = mock_page.url.split.return_value
    mock_split_result.__getitem__.return_value = "12345"
    
    with ESPNScraper(headless=True) as scraper:
        # Call the method with the mock player page
        player = scraper._scrape_player_data(mock_page)
        
        # Verify results
        assert isinstance(player, Player)
        assert player.id == "12345"  # From the mock URL
        assert player.name == "Player Name"


@patch('espn_player_getter.scraper.espn_scraper.sync_playwright')
def test_scrape_players(mock_sync_playwright, mock_page, mock_playwright):
    """Test scraping players from both batters and pitchers categories."""
    # Setup mocks
    mock_sync_playwright.return_value.start.return_value = mock_playwright
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_page.return_value = mock_page
    
    # Setup mock for _scrape_player_category method
    with patch.object(ESPNScraper, '_scrape_player_category') as mock_scrape_category:
        # Create mock batters and pitchers
        mock_batters = [
            Player(id="1", name="Batter1", team="Team1", position="1B", eligible_positions=["1B"]),
            Player(id="2", name="Batter2", team="Team2", position="OF", eligible_positions=["OF"])
        ]
        mock_pitchers = [
            Player(id="3", name="Pitcher1", team="Team3", position="SP", eligible_positions=["SP"]),
            Player(id="4", name="Pitcher2", team="Team4", position="RP", eligible_positions=["RP"])
        ]
        
        # Configure mock to return different values on subsequent calls
        mock_scrape_category.side_effect = [mock_batters, mock_pitchers]
        
        with ESPNScraper(headless=True) as scraper:
            # Call the method
            players = scraper.scrape_players(player_limit=10)
            
            # Verify the method was called twice (once for batters, once for pitchers)
            assert mock_scrape_category.call_count == 2
            
            # Verify results
            assert len(players) == 4  # 2 batters + 2 pitchers
            
            # Check that player_type was set correctly
            batters = [p for p in players if p.player_type == "batter"]
            pitchers = [p for p in players if p.player_type == "pitcher"]
            assert len(batters) == 2
            assert len(pitchers) == 2


@patch('espn_player_getter.scraper.espn_scraper.sync_playwright')
def test_scrape_player_category(mock_sync_playwright, mock_page, mock_playwright):
    """Test scraping players from a category (batters or pitchers)."""
    # Setup mocks
    mock_sync_playwright.return_value.start.return_value = mock_playwright
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_page.return_value = mock_page
    
    # Mock the next button behavior - first enabled, then disabled
    next_button_mock = MagicMock()
    next_button_mock.is_enabled.side_effect = [True, False]
    next_button_mock.count.return_value = 1
    
    # Setup processing for two pages
    with patch.object(ESPNScraper, '_process_current_page') as mock_process_page:
        # Return 3 players for first page, 2 for second page
        page1_players = [
            Player(id="1", name="Player1", team="Team1", position="1B", eligible_positions=["1B"]),
            Player(id="2", name="Player2", team="Team2", position="2B", eligible_positions=["2B"]),
            Player(id="3", name="Player3", team="Team3", position="3B", eligible_positions=["3B"])
        ]
        page2_players = [
            Player(id="4", name="Player4", team="Team4", position="SS", eligible_positions=["SS"]),
            Player(id="5", name="Player5", team="Team5", position="OF", eligible_positions=["OF"])
        ]
        mock_process_page.side_effect = [page1_players, page2_players]
        
        with ESPNScraper(headless=True) as scraper:
            # Set up the mock for the next button
            scraper.page = mock_page
            scraper.page.locator.return_value = next_button_mock
            
            # Call the method with a limit that ensures we should get all players
            players = scraper._scrape_player_category(player_limit=10)
            
            # Verify the method was called twice (once for each page)
            assert mock_process_page.call_count == 2
            
            # Verify results - we should get all 5 players
            assert len(players) == 5