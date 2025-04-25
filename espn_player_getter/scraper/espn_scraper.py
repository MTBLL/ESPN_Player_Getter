from typing import List

from playwright.sync_api import Page, sync_playwright

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
        assert self.page, "Page object is not initialized"
        self.page.goto(ESPN_URL)
        self.page.wait_for_load_state("networkidle")

        print("Scraping player data...")
        all_players = []

        # First scrape batters (default tab)
        print("Scraping BATTERS...")
        batters = self._scrape_player_category(player_limit)
        print(f"Scraped {len(batters)} batters")

        # Add batters to all players
        all_players.extend(batters)

        # Switch to pitchers tab
        print("Switching to PITCHERS tab...")
        self.page.click('label:has-text("Pitchers")')
        self.page.wait_for_load_state("networkidle")

        # Then scrape pitchers
        print("Scraping PITCHERS...")
        pitchers = self._scrape_player_category(player_limit)
        print(f"Scraped {len(pitchers)} pitchers")

        # Add pitchers to all players
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
            assert self.page, "Page object is None"
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
        assert self.page, "Page object is None"
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
                    # Try clicking the close button first
                    close_button = self.page.locator('button[class*="closebtn"]')
                    if close_button.count() > 0:
                        close_button.click()
                    else:
                        # Fallback to pressing Escape key
                        self.page.keyboard.press("Escape")

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
        player_header = page.locator("div.PlayerHeader")

        # Get player ID from URL
        url = page.url
        
        # Extract ID from URL - format is typically /id/12345/player-name
        url_parts = url.split("/")
        player_id = None
        
        # Find "id" in URL parts and get the next element
        for i, part in enumerate(url_parts):
            if part == "id" and i < len(url_parts) - 1:
                player_id = url_parts[i + 1]
                break
                
        # Fallback to last part if not found
        if not player_id:
            player_id = url_parts[-1]

        # Get player name
        name = player_header.locator("h1").inner_text()

        # Get team name
        team_element = player_header.locator('li:has-text("Team")')
        team = (
            team_element.inner_text().replace("Team", "").strip()
            if team_element.count() > 0
            else ""
        )

        # Get player position
        position_element = player_header.locator('li:has-text("Position")')
        position = (
            position_element.inner_text().replace("Position", "").strip()
            if position_element.count() > 0
            else ""
        )

        # Parse eligible positions from the position string
        eligible_positions = [pos.strip() for pos in position.split(",")]
        primary_position = eligible_positions[0] if eligible_positions else ""

        # Get player image URL
        image_url = ""
        headshot_img = player_header.locator('figure.PlayerHeader__HeadShot img')
        if headshot_img.count() > 0:
            image_url = headshot_img.get_attribute("src") or ""
        
        # Extract bio data from the PlayerHeader__Bio section
        bio_data = {}
        bio_list = player_header.locator('ul.PlayerHeader__Bio_List li')
        
        for i in range(bio_list.count()):
            bio_item = bio_list.nth(i)
            label_element = bio_item.locator('div.ttu')
            value_element = bio_item.locator('div.fw-medium')
            
            if label_element.count() > 0 and value_element.count() > 0:
                label = label_element.inner_text().strip()
                value = value_element.inner_text().strip()
                
                # Normalize the keys to be consistent
                if label.upper() == "HT/WT":
                    bio_data["height_weight"] = value
                elif label.upper() == "BIRTHDATE":
                    bio_data["birthdate"] = value
                elif label.upper() == "BAT/THR":
                    bio_data["bat_throw"] = value
                elif label.upper() == "BIRTHPLACE":
                    bio_data["birthplace"] = value
                elif label.upper() == "STATUS":
                    bio_data["status"] = value
                else:
                    # For any other fields that might be added in the future
                    bio_data[label.lower()] = value

        return Player(
            id=player_id,
            name=name,
            team=team,
            position=primary_position,
            eligible_positions=eligible_positions,
            image_url=image_url,
            bio_data=bio_data,
        )
