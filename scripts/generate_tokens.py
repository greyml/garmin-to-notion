"""Generate Garmin OAuth tokens locally and output as JSON string for GitHub secret.

Usage:
    python scripts/generate_tokens.py

Reads GARMIN_EMAIL and GARMIN_PASSWORD from environment variables.
Outputs a JSON token string to stdout for setting as the GARMIN_AUTH_TOKEN GitHub secret.
"""

import json
import os
import sys
import pathlib

from garminconnect import Garmin, GarminConnectAuthenticationError

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

if not email or not password:
    print("Error: Set GARMIN_EMAIL and GARMIN_PASSWORD environment variables", file=sys.stderr)
    sys.exit(1)

try:
    print(f"Logging in as {email}...", file=sys.stderr)
    garmin = Garmin(email, password)
    garmin.login("~/.garminconnect")
    print("Login successful!", file=sys.stderr)

    # Get the token as JSON string
    token_str = pathlib.Path.home().joinpath(".garminconnect", "garmin_tokens.json").read_text()
    
    # Verify it's valid JSON
    try:
        json.loads(token_str)
    except json.JSONDecodeError:
        print("Error: Token is not valid JSON", file=sys.stderr)
        sys.exit(1)
    
    # Output token to stdout (will be captured by GitHub Actions)
    print(token_str)
    print(f"Token length: {len(token_str)} chars", file=sys.stderr)

except GarminConnectAuthenticationError as e:
    print(f"Authentication failed: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
