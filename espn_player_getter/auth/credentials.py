import json
import sys
from pathlib import Path
from typing import Dict, Any

# Constants
AUTH_FILE = Path(".auth/credentials.json")


def load_credentials() -> Dict[str, str]:
    """Load ESPN credentials from auth file.
    
    Returns:
        Dict containing username and password
        
    Raises:
        SystemExit: If auth file doesn't exist or contains invalid JSON
    """
    if not AUTH_FILE.exists():
        print(f"Error: Auth file not found at {AUTH_FILE}")
        print("Please create it with your ESPN credentials.")
        sys.exit(1)
    
    try:
        with open(AUTH_FILE, "r") as f:
            credentials = json.load(f)
            
        # Validate credentials format
        if not isinstance(credentials, dict):
            print(f"Error: Invalid credentials format in {AUTH_FILE}")
            sys.exit(1)
            
        return credentials
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {AUTH_FILE}")
        sys.exit(1)