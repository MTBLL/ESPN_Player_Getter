from typing import Dict
from playwright.sync_api import Page

# Constants
ESPN_URL = "https://www.espn.com/fantasy/baseball/"

def login_to_espn(page: Page, credentials: Dict[str, str]) -> None:
    """Log in to ESPN Fantasy Baseball.

    Args:
        page: Playwright page object
        credentials: Dictionary containing username and password
    """
    username = credentials.get("username")
    password = credentials.get("password")

    if not username or not password:
        print("Warning: Empty credentials provided, continuing without login")
        return

    print("Logging in to ESPN Fantasy Baseball...")
    
    # Navigate to ESPN Fantasy Baseball
    page.goto(ESPN_URL)
    page.wait_for_load_state("networkidle")
    
    # Click on the login button
    page.click("button:has-text('Log In')")
    
    # Fill in the credentials
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    
    # Submit the login form
    page.click('button:has-text("Log In")')
    
    # Wait for navigation to complete
    page.wait_for_load_state("networkidle")
    
    print("Login successful!")