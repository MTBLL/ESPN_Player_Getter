import re
from time import sleep
from typing import List

from playwright.sync_api import Page, sync_playwright

import espn_player_getter.scraper.elements as E
from espn_player_getter.models.player import Player

ESPN_URL = "https://fantasy.espn.com/baseball/players/projections"
ESPN_PLAYER_URL = "https://www.espn.com/mlb/player/stats/_/id/{player_id}/"

DOM_LOADED = "domcontentloaded"


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
        self.__enter__()
        assert self.page, "Page object is not initialized"
        breakpoint()
        self.page.goto(ESPN_URL)
        self.page.wait_for_load_state(DOM_LOADED)

        print("Scraping player data...")
        all_players = []

        # First scrape batters (default tab)
        print("Scraping BATTERS...")
        batters = self._scrape_player_tables(player_limit)
        print(f"Scraped {len(batters)} batters")

        # Add batters to all players
        all_players.extend(batters)

        # Switch to pitchers tab
        print("Switching to PITCHERS tab...")
        self.page.click('label:has-text("Pitchers")')
        self.page.wait_for_load_state(DOM_LOADED)

        # Then scrape pitchers
        print("Scraping PITCHERS...")
        pitchers = self._scrape_player_tables(player_limit)
        print(f"Scraped {len(pitchers)} pitchers")

        # Add pitchers to all players
        all_players.extend(pitchers)

        # Now complete player details by visiting individual player pages
        print("Completing player details...")
        completed_players = self._complete_player_details(all_players)

        print(f"Total players scraped: {len(completed_players)}")
        return completed_players

    def _scrape_player_tables(self, player_limit: int = 500) -> List[Player]:
        """Scrape players from the current category tab (batters or pitchers).

        Args:
            player_limit: Maximum number of players to scrape

        Returns:
            List of Player objects with basic data
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
            next_button = self.page.locator(E.BTN_NEXT)
            if next_button.count() > 0 and next_button.is_enabled():
                next_button.click()
                self.page.wait_for_load_state(DOM_LOADED)
                page_num += 1
            else:
                has_next_page = False
                print("No more pages to process")

        return players

    def _process_current_page(self) -> List[Player]:
        """Process the current page of players, extracting basic data from rows.

        Returns:
            List of Player objects with basic data
        """
        current_page_players = []
        player_table_loaded = False
        players_table = None

        # Get the player table
        assert self.page, "Page object is None"
        while not player_table_loaded:
            players_table = self.page.locator(E.PLAYERS_TABLE)
            player_table_loaded = players_table.is_visible()
            sleep(0.1)

        # Get all player rows
        assert players_table, "Players table is None"
        player_rows = players_table.locator(E.PLAYER_ROW)
        player_count = player_rows.count()

        print(f"Found {player_count} players on current page")

        for i in range(player_count):
            try:
                # Get the row element
                player_row = player_rows.nth(i)
                player_row.scroll_into_view_if_needed()

                # Get player name
                player_name_element = player_row.locator(E.LINK_PLAYER_NAME)
                player_name = player_name_element.inner_text()

                # Get player ID and image URL from headshot
                player_id = ""
                image_url = ""
                headshot_img = player_row.locator(E.PLAYER_HEADSHOT)
                if headshot_img.count() > 0:
                    src = headshot_img.get_attribute("src") or ""
                    # Extract player ID from image URL (e.g., "/i/headshots/mlb/players/full/39832.png")
                    if src:
                        image_url = src
                        match = re.search(r"/full/(\d+)\.png", src)
                        if match:
                            player_id = match.group(1)

                # Get team name
                team = ""
                team_logo = player_row.locator(E.PLAYER_TEAM_LOGO)
                if team_logo.count() > 0:
                    team = team_logo.get_attribute("alt") or ""

                # Get player positions
                positions = []
                positions_element = player_row.locator(E.PLAYER_POSITIONS)
                if positions_element.count() > 0:
                    positions_text = positions_element.inner_text()
                    positions = [pos.strip() for pos in positions_text.split(",")]

                # Create player object with data from row
                player = Player(
                    id=player_id,
                    name=player_name,
                    team=team,
                    position=positions[0] if positions else "",
                    eligible_positions=positions,
                    image_url=image_url,
                    bio_data={},
                )

                current_page_players.append(player)
                print(f"Added player from row: {player_name} (ID: {player_id})")

            except Exception as e:
                print(f"Error processing player row: {e}")
                continue

        return current_page_players

    def _complete_player_details(self, players: List[Player]) -> List[Player]:
        """Complete player details by visiting individual player pages.

        Args:
            players: List of Player objects with basic data

        Returns:
            List of Player objects with complete data
        """
        completed_players = []

        for player in players:
            if not player.id:
                print(f"Skipping player without ID: {player.name}")
                continue

            try:
                print(f"Completing details for player: {player.name} (ID: {player.id})")

                # Create player page URL
                player_url = ESPN_PLAYER_URL.format(player_id=player.id)

                # Open player page in a new page
                player_page = self.browser.new_page()
                player_page.goto(player_url)
                player_page.wait_for_load_state(DOM_LOADED)

                # Get bio data for the player
                bio_data = self._scrape_player_bio(player_page)
                player.bio_data = bio_data

                # Close the player page
                player_page.close()

                completed_players.append(player)
                print(f"Completed details for player: {player.name}")

            except Exception as e:
                print(f"Error completing details for player {player.name}: {e}")
                # Add the player with incomplete data anyway
                completed_players.append(player)
                continue

        return completed_players

    def _scrape_player_bio(self, page: Page) -> dict:
        """Scrape player bio data from the player page.

        Args:
            page: The Playwright page object for the player page

        Returns:
            Dictionary with player bio data
        """
        # Get player header div
        player_header = page.locator(E.PLAYER_HEADER)

        # Extract bio data from the PlayerHeader__Bio section
        bio_data_raw = {}
        bio_list = player_header.locator(E.PLAYER_BIO_LIST)

        for i in range(bio_list.count()):
            li_item = bio_list.nth(i)

            # Get the two divs - first is label, second is value
            divs = li_item.locator("div")

            # Make sure we have both divs
            if divs.count() >= 2:
                label = (
                    divs.nth(0).inner_text().strip().upper()
                )  # First div - the label (uppercase for consistency)
                value = divs.nth(1).inner_text().strip()  # Second div - the value

                # Add to dictionary with the raw label as key
                bio_data_raw[label] = value

        bio_data = {}
        field_mapping = {
            "HT/WT": "height_weight",
            "BIRTHDATE": "birthdate",
            "BAT/THR": "bat_throw",
            "BIRTHPLACE": "birthplace",
            "STATUS": "status",
        }
        for raw_key, value in bio_data_raw.items():
            if raw_key == "BIRTHDATE":
                value = value.split(" ")[0].strip()
            if raw_key in field_mapping:
                bio_data[field_mapping[raw_key]] = value
            else:
                # For any fields not in our mapping, use lowercase version of original key
                bio_data[raw_key.lower()] = value

        return bio_data
