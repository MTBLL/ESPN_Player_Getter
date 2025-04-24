from typing import List

from playwright.sync_api import sync_playwright, Page

from espn_player_getter.models.player import Player

ESPN_URL = "https://fantasy.espn.com/baseball/players/projections"

class ESPNScraper:
    """Scraper for ESPN Fantasy Baseball player data."""

    def __init__(self, headless: bool = True):
        """Initialize the scraper.

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    def __enter__(self):
        """Start Playwright session when entering context."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close browser and stop Playwright when exiting context."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def scrape_players(self, player_limit: int = 500) -> List[Player]:
        """Scrape player data from ESPN Fantasy Baseball.

        Args:
            player_limit: Maximum number of players to scrape per category (batters/pitchers)
            
        Returns:
            List of Player objects
        """
        print("Navigating to ESPN Fantasy Baseball players page...")
        self.page.goto(ESPN_URL)
        self.page.wait_for_load_state("networkidle")

        print("Scraping player data...")
        all_players = []
        
        # First scrape batters (default tab)
        print("Scraping BATTERS...")
        batters = self._scrape_player_category(player_limit)
        print(f"Scraped {len(batters)} batters")
        
        # Add player_type field to batters
        for player in batters:
            player.player_type = "batter"
        all_players.extend(batters)
        
        # Switch to pitchers tab
        print("Switching to PITCHERS tab...")
        self.page.click('label:has-text("Pitchers")')
        self.page.wait_for_load_state("networkidle")
        
        # Then scrape pitchers
        print("Scraping PITCHERS...")
        pitchers = self._scrape_player_category(player_limit)
        print(f"Scraped {len(pitchers)} pitchers")
        
        # Add player_type field to pitchers
        for player in pitchers:
            player.player_type = "pitcher"
        all_players.extend(pitchers)

        print(f"Total players scraped: {len(all_players)}")
        return all_players
        
    def _scrape_player_category(self, player_limit: int = 500) -> List[Player]:
        """Scrape players from the current category tab (batters or pitchers).
        
        Args:
            player_limit: Maximum number of players to scrape
            
        Returns:
            List of Player objects
        """
        players = []
        page_num = 1
        has_next_page = True

        while has_next_page and len(players) < player_limit:
            print(f"Processing page {page_num}...")
            # Process current page players
            current_page_players = self._process_current_page()
            players.extend(current_page_players)
            
            # Check if we've reached the player limit
            if len(players) >= player_limit:
                print(f"Reached player limit ({player_limit}). Stopping.")
                # Trim to exact limit
                if len(players) > player_limit:
                    players = players[:player_limit]
                break
            
            # Check if there's a next page and navigate to it
            next_button = self.page.locator('button[class*="next"]')
            if next_button.count() > 0 and next_button.is_enabled():
                next_button.click()
                self.page.wait_for_load_state("networkidle")
                page_num += 1
            else:
                has_next_page = False
                print("No more pages to process")
                
        return players
    
    def _process_current_page(self) -> List[Player]:
        """Process the current page of players.
        
        Returns:
            List of Player objects from the current page
        """
        current_page_players = []
        
        # Get the player table
        players_table = self.page.locator('div[class*="players-table"]')
        
        # Get all player rows
        player_rows = players_table.locator('div[class*="player-info-section"]')
        player_count = player_rows.count()
        
        print(f"Found {player_count} players on current page")
        
        for i in range(player_count):
            try:
                # Get the row element
                player_row = player_rows.nth(i)
                
                # Find and click the player name element to open the player card
                player_name_element = player_row.locator('div[class*="player-name"] a')
                player_name = player_name_element.inner_text()
                
                # Click to open the player modal
                player_name_element.click()
                self.page.wait_for_selector('text="Complete Stats"')
                
                # Open Complete Stats in a new page
                with self.page.context.expect_page() as new_page_info:
                    self.page.click('text="Complete Stats"')
                player_page = new_page_info.value
                player_page.wait_for_load_state("networkidle")
                
                # Scrape player info from the player page
                player_data = self._scrape_player_data(player_page)
                current_page_players.append(player_data)
                
                # Close the player page
                player_page.close()
                
                # Close the player modal if it's still open
                if self.page.is_visible('div[role="dialog"]'):
                    self.page.press('Escape')
                
                print(f"Scraped player: {player_name}")
                
            except Exception as e:
                print(f"Error scraping player: {e}")
                continue

        return current_page_players
    
    def _scrape_player_data(self, page: Page) -> Player:
        """Scrape player data from the player page.
        
        Args:
            page: The Playwright page object for the player page
            
        Returns:
            Player object with scraped data
        """
        # Get player header div
        player_header = page.locator('div.PlayerHeader')
        
        # Get player ID from URL
        url = page.url
        player_id = url.split('/')[-1]
        
        # Get player name
        name = player_header.locator('h1').inner_text()
        
        # Get team name
        team_element = player_header.locator('li:has-text("Team")')
        team = team_element.inner_text().replace('Team', '').strip() if team_element.count() > 0 else ""
        
        # Get player position
        position_element = player_header.locator('li:has-text("Position")')
        position = position_element.inner_text().replace('Position', '').strip() if position_element.count() > 0 else ""
        
        # Parse eligible positions from the position string
        eligible_positions = [pos.strip() for pos in position.split(',')]
        primary_position = eligible_positions[0] if eligible_positions else ""
        
        return Player(
            id=player_id,
            name=name,
            team=team,
            position=primary_position,
            eligible_positions=eligible_positions
        )