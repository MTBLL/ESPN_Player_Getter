import os
from unittest.mock import MagicMock, patch

import pytest

from espn_player_getter.models.player import Player
from espn_player_getter.scraper.espn_scraper import ESPNScraper


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


@patch("espn_player_getter.scraper.espn_scraper.sync_playwright")
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


@pytest.fixture
def fixture_player_table_path():
    """Get the path to the player table HTML fixture."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "player_table.html")


@pytest.fixture
def fixture_player_header_path():
    """Get the path to the player header HTML fixture."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "player_header.html")


def test_process_current_page(page, fixture_player_table_path):
    """Test processing the current page of players using a real HTML fixture."""
    # Load the fixture HTML into the page
    page.goto(f"file://{fixture_player_table_path}")

    # Create the scraper without starting a new Playwright instance
    scraper = ESPNScraper(headless=True)

    # Set the page directly
    scraper.page = page
    # Call the method
    players = scraper._process_current_page()
    # Verify results
    assert len(players) == 50  # We should get players from the fixture
    assert all(isinstance(player, Player) for player in players)

    # Verify first player details (adjust these assertions based on your fixture content)
    # These assertions are examples and should be replaced with real expected values
    first_player = players[0]
    assert first_player.name == "Shohei Ohtani"
    assert first_player.team == "Los Angeles Dodgers"
    assert first_player.eligible_positions == ["DH", "SP"]


def test_scrape_player_bio(page, fixture_player_header_path):
    """Test scraping player bio data from a player page."""
    # Load the fixture HTML into the page
    page.goto(f"file://{fixture_player_header_path}")

    # Create the scraper without starting a new Playwright instance
    scraper = ESPNScraper(headless=True)

    # Set the page directly
    scraper.page = page

    # Call the method with the mock page
    bio_data = scraper._scrape_player_bio(page)

    # Verify bio data was correctly extracted
    assert bio_data["height_weight"] == "6' 3\", 210 lbs"
    assert bio_data["birthdate"] == "7/5/1994"  # Note: date is parsed to remove the age
    assert bio_data["bat_throw"] == "Left/Right"
    assert bio_data["birthplace"] == "Oshu, Japan"
    assert bio_data["status"] == "Active"


@patch("espn_player_getter.scraper.espn_scraper.sync_playwright")
@patch("espn_player_getter.scraper.espn_scraper.ESPN_URL")
def test_scrape_players(
    mock_espn_url,
    mock_sync_playwright,
    page,
    fixture_player_table_path,
    fixture_player_header_path,
):
    """Test scraping players from both batters and pitchers categories."""
    # Load the fixture HTML into the page
    mock_espn_url.__str__.return_value = f"file://{fixture_player_table_path}"
    # Load the fixture HTML into the page
    # page.goto(f"file://{fixture_player_table_path}")

    # Create the scraper without starting a new Playwright instance
    scraper = ESPNScraper(headless=True)

    # Set the page directly
    # scraper.page = page

    # Call the method
    players = scraper.scrape_players(player_limit=10)

    # Verify results
    assert len(players) == 4  # 2 batters + 2 pitchers


@patch("espn_player_getter.scraper.espn_scraper.sync_playwright")
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
    with patch.object(ESPNScraper, "_process_current_page") as mock_process_page:
        # Return 3 players for first page, 2 for second page
        page1_players = [
            Player(
                id="1",
                name="Player1",
                team="Team1",
                position="1B",
                eligible_positions=["1B"],
                image_url="https://example.com/player1.png",
                bio_data={"status": "Active"},
            ),
            Player(
                id="2",
                name="Player2",
                team="Team2",
                position="2B",
                eligible_positions=["2B"],
                image_url="https://example.com/player2.png",
                bio_data={"status": "Active"},
            ),
            Player(
                id="3",
                name="Player3",
                team="Team3",
                position="3B",
                eligible_positions=["3B"],
                image_url="https://example.com/player3.png",
                bio_data={"status": "Active"},
            ),
        ]
        page2_players = [
            Player(
                id="4",
                name="Player4",
                team="Team4",
                position="SS",
                eligible_positions=["SS"],
                image_url="https://example.com/player4.png",
                bio_data={"status": "Active"},
            ),
            Player(
                id="5",
                name="Player5",
                team="Team5",
                position="OF",
                eligible_positions=["OF"],
                image_url="https://example.com/player5.png",
                bio_data={"status": "Active"},
            ),
        ]
        mock_process_page.side_effect = [page1_players, page2_players]

        with ESPNScraper(headless=True) as scraper:
            # Set up the mock for the next button
            scraper.page = mock_page
            scraper.page.locator.return_value = next_button_mock

            # Call the method with a limit that ensures we should get all players
            players = scraper._scrape_player_tables(player_limit=10)

            # Verify the method was called twice (once for each page)
            assert mock_process_page.call_count == 2

            # Verify results - we should get all 5 players
            assert len(players) == 5
