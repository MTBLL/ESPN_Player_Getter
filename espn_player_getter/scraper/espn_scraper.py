import re
from time import sleep
from typing import Tuple

from playwright.sync_api import Locator, Page, sync_playwright
from typing_extensions import Dict

import espn_player_getter.scraper.elements as E
from espn_player_getter.errors.exceptions import PlayerNotLoadedError
from espn_player_getter.models.player import Player

ESPN_URL = "https://fantasy.espn.com/baseball/players/projections"
ESPN_PLAYER_URL = "https://www.espn.com/mlb/player/stats/_/id/{player_id}/"

DOM_LOADED = "domcontentloaded"

players: Dict[str, Player] = {}


class ESPNScraper:
    """Scraper for ESPN Fantasy Baseball player data."""

    def __init__(self, headless: bool = True, base_url: str = ESPN_URL):
        """Initialize the scraper.

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.base_url = base_url
        self.expected_player_row = 1

    def __enter__(self):
        """Start Playwright session when entering context."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close browser and stop Playwright when exiting context."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def scrape_players(self, player_limit: int = 500) -> Dict[str, Player]:
        """Scrape player data from ESPN Fantasy Baseball.

        Args:
            player_limit: Maximum number of players to scrape per category (batters/pitchers)

        Returns:
            Dictionary of Player objects with player ID as key
        """
        print("Navigating to ESPN Fantasy Baseball players page...")
        assert self.page, "Page object is not initialized"
        self.page.goto(self.base_url)
        self.page.wait_for_load_state()
        self._player_table_did_load()

        print("Scraping player data...")

        # First scrape batters (default tab)
        print("Scraping BATTERS...")
        batters = self._scrape_player_tables(player_limit)
        print(f"Scraped {len(batters)} batters")

        # Add batters to all players
        players.update(batters)

        # Switch to pitchers tab
        print("Switching to PITCHERS tab...")

        # Click the Pitchers tab
        self.page.click('label:has-text("Pitchers")')
        self.expected_player_row = 1

        # Wait for initial page load
        self.page.wait_for_load_state()

        # Reset our expected row counter since we're starting a new category
        sleep(1)

        # Wait for the player table to refresh with rank starting at 1
        # This is the key indicator that the tab switch has completed
        print("Waiting for player table to reset with rank 1...")

        max_attempts = 10

        for attempt in range(max_attempts):
            if self._player_table_did_load():
                break

            # Sleep before next attempt
            sleep(0.1)

            # If we've tried several times, try clicking the tab again
            if attempt == 5:
                print("Retrying tab click...")
                self.page.click('label:has-text("Pitchers")')
                self.page.wait_for_load_state()

        # Then scrape pitchers
        print("Scraping PITCHERS...")
        pitchers = self._scrape_player_tables(player_limit)
        print(f"Scraped {len(pitchers)} pitchers")

        # Add pitchers to all players
        players.update(pitchers)

        # Now complete player details by visiting individual player pages
        print("Completing player details...")
        completed_players = self._complete_player_details(players)

        print(f"Total players scraped: {len(completed_players)}")
        return completed_players

    def _scrape_player_tables(self, player_limit: int) -> Dict[str, Player]:
        """Scrape players from the current category tab (batters or pitchers).

        Args:
            player_limit: Maximum number of players to scrape

        Returns:
            Dictionary of Player objects with player ID as key
        """
        positions_players = {}
        page_num = 1
        has_next_page = True
        self.expected_player_row = 1

        while has_next_page and len(positions_players) < player_limit:
            print(f"Processing page {page_num}...")
            # Process current page players
            current_page_players, last_player_row = self._process_current_page()
            positions_players.update(current_page_players)
            self.expected_player_row = last_player_row

            # Check if we've reached the player limit
            if len(positions_players) >= player_limit:
                print(f"Reached player limit ({player_limit}). Stopping.")
                # Trim to exact limit if we have more than the limit
                if len(positions_players) > player_limit:
                    # Keep only the first player_limit items
                    extra_count = len(positions_players) - player_limit
                    # Convert to list of tuples, slice, and convert back to dict
                    positions_players = dict(
                        list(positions_players.items())[:player_limit]
                    )
                    print(f"Trimmed {extra_count} players to meet limit.")
                break

            # Check if there's a next page and navigate to it
            assert self.page, "Page object is None"
            next_button = self.page.locator(E.BTN_NEXT)
            if next_button.count() > 0 and next_button.is_enabled():
                # Get the current first player name for comparison
                current_first_player_name = ""
                try:
                    first_player_element = self.page.locator(E.LINK_PLAYER_NAME).first
                    if first_player_element.is_visible():
                        current_first_player_name = (
                            first_player_element.inner_text().strip()
                        )
                except Exception:
                    pass

                print(
                    f"Clicking next page button, expecting first row rank {self.expected_player_row}..."
                )
                next_button.click()

                # Wait for basic page load
                self.page.wait_for_load_state()

                # Use our helper method to verify the next page has loaded
                new_page_loaded = self._player_table_did_load(
                    expected_row=self.expected_player_row,
                    timeout_seconds=8,
                )

                # If verification failed, try one more time
                if not new_page_loaded:
                    print("Retrying next page click...")
                    try:
                        if next_button.is_visible() and next_button.is_enabled():
                            next_button.click()
                            self.page.wait_for_load_state()

                            # Try waiting again
                            new_page_loaded = self._player_table_did_load(
                                expected_row=self.expected_player_row, timeout_seconds=5
                            )
                    except Exception:
                        pass

                if new_page_loaded:
                    print(f"Successfully moved to page {page_num + 1}")
                    page_num += 1
                else:
                    print("Failed to verify next page loaded, stopping pagination.")
                    has_next_page = False
            else:
                has_next_page = False
                print("No more pages to process (no next button available)")

        return positions_players

    def _player_table_did_load(
        self, expected_row: int = None, timeout_seconds: int = 6
    ) -> bool:
        """Wait for the player table to load with the expected first row.

        Args:
            expected_row: The expected rank value for the first row (after header)
            timeout_seconds: Maximum time to wait in seconds

        Returns:
            True if the table loaded correctly, False otherwise
        """
        assert self.page, "Page object is None"
        expected_row = (
            expected_row if expected_row is not None else self.expected_player_row
        )
        max_attempts = int(timeout_seconds * 10)  # 10 attempts per second

        for attempt in range(max_attempts):
            try:
                players_table = self.page.locator(E.PLAYERS_TABLE)

                # Verify table is visible
                if not players_table.is_visible():
                    sleep(0.1)
                    continue

                # Check for rank elements
                rank_elements = players_table.locator('div[title="Rank"]')
                if rank_elements.count() < 2:  # Need at least header + first row
                    sleep(0.1)
                    continue

                # Check first row rank value
                rank_element = rank_elements.nth(1)  # first row after header
                if not rank_element.is_visible():
                    sleep(0.1)
                    continue

                player_row_text = rank_element.inner_text().strip()
                if not player_row_text or not player_row_text.isdigit():
                    sleep(0.1)
                    continue

                player_row_int = int(player_row_text)
                if player_row_int != expected_row:
                    if attempt % 5 == 0:  # Only log every few attempts to reduce noise
                        print(
                            f"Waiting for row {expected_row}, currently seeing row {player_row_int}"
                        )
                    sleep(0.1)
                    continue

                # ensure the first player row id is not currently in the dictionary
                player_row = players_table.locator(E.PLAYER_ROW).first
                player_name = self._get_player_name_from_row(player_row)
                # Special considerations for Shohei Ohtani since he's two-way player; may need to create a list of those players one day
                if player_name == "Shohei Ohtani":
                    player_row = players_table.locator(E.PLAYER_ROW).nth(1)

                player_id, _ = self._get_player_id_and_img_url_from_row(player_row)
                if player_id in players.keys():
                    print(f"Player ID {player_id} already exists in the dictionary")
                    sleep(0.1)
                    continue

                # All checks passed
                return True

            except Exception:
                sleep(0.1)

        print(
            f"WARNING: Player table did not load with row {expected_row} after {timeout_seconds} seconds"
        )
        return False

    def _process_current_page(self) -> Tuple[Dict[str, Player], int]:
        """Process the current page of players, extracting basic data from rows.

        Returns:
            Dictionary of Player objects with player ID as key
        """
        current_page_players = {}

        players_table = self.page.locator(E.PLAYERS_TABLE)

        # Get all player rows
        assert players_table, "Players table is None"
        player_rows = players_table.locator(E.PLAYER_ROW)
        player_count = player_rows.count()

        print(f"Found {player_count} players on current page")
        unloaded_player_indicies = [x for x in range(player_count)]
        while len(unloaded_player_indicies) > 0:
            for i in unloaded_player_indicies:
                try:
                    # Get the row element
                    player_row = player_rows.nth(i)
                    # Get player name
                    player_name_element = player_row.locator(E.LINK_PLAYER_NAME)
                    player_name = player_name_element.inner_text()
                    player_id = ""
                    image_url = ""

                    player_id, image_url = self._get_player_id_and_img_url_from_row(
                        player_row
                    )
                    if player_id:
                        unloaded_player_indicies.remove(i)

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

                    current_page_players[player_id] = player
                    print(f"Added player from row: {player_name} (ID: {player_id})")

                except PlayerNotLoadedError as e:
                    print(f"Player not loaded: {e}")
                    continue
                except Exception as e:
                    print(f"Error processing player row: {e}")
                    continue

        return current_page_players, self.expected_player_row + player_count

    def _complete_player_details(self, players: Dict[str, Player]) -> Dict[str, Player]:
        """Complete player details by visiting individual player pages.

        Args:
            players: Dictionary of Player objects with player ID as key

        Returns:
            Dictionary of Player objects with complete data
        """
        completed_players = {}

        for player_id, player in players.items():
            if not player.id:
                print(f"Skipping player without ID: {player.name}")
                continue

            try:
                print(f"Completing details for player: {player.name} (ID: {player.id})")

                # Create player page URL
                player_url = ESPN_PLAYER_URL.format(player_id=player.id)

                # Open player page in a new page
                assert self.browser, "Browser is not set"
                player_page = self.browser.new_page()
                player_page.goto(player_url)
                player_page.wait_for_load_state(DOM_LOADED)

                # Get bio data for the player
                player.bio_data = self._scrape_player_bio(player_page)

                # Close the player page
                player_page.close()

                completed_players.update({player_id: player})
                print(f"Completed details for player: {player.name}")

            except Exception as e:
                print(f"Error completing details for player {player.name}: {e}")
                # Add the player with incomplete data anyway
                completed_players.update({player_id: player})
                continue

        return completed_players

    def _scrape_player_bio(self, page: Page) -> Dict:
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

    def _get_player_id_and_img_url_from_row(self, row: Locator) -> Tuple[str, str]:
        player_id = ""
        image_url = ""
        headshot_img = row.locator(E.PLAYER_HEADSHOT)
        if headshot_img.count() > 0:
            src = headshot_img.get_attribute("src") or ""
            # Extract player ID from image URL (e.g., "/i/headshots/mlb/players/full/39832.png")
            if src:
                image_url = src
                match = re.search(r"/full/(\d+)\.png", src)
                if match:
                    player_id = match.group(1)
                else:
                    raise PlayerNotLoadedError(
                        f"Player ID not found in image URL: {src} - {player_id}"
                    )

        return player_id, image_url

    def _get_player_name_from_row(self, row: Locator) -> str:
        return row.locator(E.LINK_PLAYER_NAME).inner_text().strip()
