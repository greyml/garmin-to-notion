import json
import os
import subprocess
from dataclasses import dataclass

from dotenv import load_dotenv
from garminconnect import Garmin


@dataclass(frozen=True)
class GarminConfiguration:
    activity_fetch_limit: int


def get_garmin_client() -> tuple[Garmin, GarminConfiguration]:
    load_dotenv()

    print("Initializing Garmin client...")

    garmin_client = _get_garmin_client()
    garmin_configuration = _get_garmin_configuration()

    print("Garmin client authenticated successfully.")

    # Try to persist the refreshed token (for future-proofing)
    _persist_token_if_needed(garmin_client)

    return garmin_client, garmin_configuration


def _get_garmin_client() -> Garmin:
    garmin_auth_token = os.getenv("GARMIN_AUTH_TOKEN")

    if not garmin_auth_token:
        raise ValueError(
            "GARMIN_AUTH_TOKEN is required. "
            "See README_AUTH_SETUP.md for instructions on generating a token."
        )

    # GARMIN_AUTH_TOKEN is passed as an inline JSON string (>512 chars), so the
    # library treats it as token data rather than a file path. This means the
    # access token is refreshed in memory on each run via diauth.garmin.com
    # (standard OAuth2 refresh — separate from the SSO endpoints that are
    # rate-limited), but the refreshed token is never written back anywhere.
    #
    # This is safe as long as Garmin issues non-rotating refresh tokens, which
    # is currently the case. If that ever changes and runs start failing with
    # 401s, we persist the updated token back to the GitHub secret.
    garmin_client = Garmin()
    garmin_client.login(tokenstore=garmin_auth_token)

    return garmin_client


def _persist_token_if_needed(garmin_client: Garmin) -> None:
    """
    Persist the refreshed Garmin token back to GitHub secrets.
    
    This handles the case where Garmin switches to rotating refresh tokens.
    If the token has changed since we loaded it, we update the GitHub secret.
    """
    try:
        # Get the current token from the client
        current_token = garmin_client.oauth2_token
        
        if not current_token:
            print("No OAuth2 token available to persist")
            return
        
        # Get the original token from environment
        original_token_str = os.getenv("GARMIN_AUTH_TOKEN")
        
        if not original_token_str:
            return
        
        try:
            original_token = json.loads(original_token_str)
        except json.JSONDecodeError:
            print("Could not parse original token")
            return
        
        # Compare refresh tokens (the part that might rotate)
        original_refresh_token = original_token.get("refresh_token")
        current_refresh_token = current_token.get("refresh_token")
        
        # Only update if the refresh token has changed
        if original_refresh_token != current_refresh_token:
            print("Refresh token has changed, updating GitHub secret...")
            _update_github_secret(current_token)
        else:
            print("Token is current, no update needed")
    
    except Exception as e:
        print(f"Warning: Could not persist token: {e}")
        print("This is not critical - the token will be refreshed on next run")


def _update_github_secret(token: dict) -> None:
    """
    Update the GARMIN_AUTH_TOKEN GitHub secret with the new token.
    
    Requires:
    - GITHUB_TOKEN environment variable (GitHub Actions provides this automatically)
    - Repository in format: owner/repo
    """
    github_token = os.getenv("GITHUB_TOKEN")
    github_repository = os.getenv("GITHUB_REPOSITORY")
    
    if not github_token or not github_repository:
        print("GITHUB_TOKEN or GITHUB_REPOSITORY not set, skipping token update")
        return
    
    try:
        # Serialize the token back to JSON
        token_json = json.dumps(token)
        
        # Use gh CLI to update the secret (this is the most reliable method)
        # gh CLI is pre-installed in GitHub Actions runners
        result = subprocess.run(
            ["gh", "secret", "set", "GARMIN_AUTH_TOKEN", "--body", token_json],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            env={**os.environ, "GH_TOKEN": github_token},
            timeout=30
        )
        
        if result.returncode == 0:
            print("Successfully updated GARMIN_AUTH_TOKEN secret")
        else:
            print(f"Failed to update secret: {result.stderr}")
    
    except Exception as e:
        print(f"Error updating GitHub secret: {e}")
        print("Token refresh will still work in memory for this run")


def _get_garmin_configuration():
    return GarminConfiguration(
        activity_fetch_limit=int(os.getenv("GARMIN_ACTIVITIES_FETCH_LIMIT", "10")),
    )
