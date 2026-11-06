import openreview
from openreview.api import OpenReviewClient
import json
import os
import subprocess

from utils.paths import VENUE, ROOT_DIR

CREDENTIALS_PATH = os.path.join(ROOT_DIR, "private", "credentials.json")


def read_credentials(file_path):
    if not os.path.exists(file_path):
        print(f"Credentials file '{file_path}' not found.")
        return None
    credentials = json.load(open(file_path))
    if "username" not in credentials or "password" not in credentials:
        print(
            f"Credentials file '{file_path}' does not contain the 'username' and/or 'password' fields."
        )
        return None
    if "username" == "???" or "password" == "???":
        print(f"Please fill in the 'username' and 'password' fields in '{file_path}'.")
        return None
    return credentials


def op_otp_provider(credentials, test_venue):
    """
    Optional: read the TOTP code for MFA from 1Password via the `op` CLI. Enabled by the "op_item" (and for the test venue "op_item_dev") and optional "op_account" keys in the credentials file. No secret is stored in the credentials file.
    """
    item = credentials.get("op_item_dev" if test_venue else "op_item")
    if not item:
        return None
    cmd = ["op", "item", "get", item, "--otp"]
    if credentials.get("op_account"):
        cmd += ["--account", credentials["op_account"]]

    def provider(method):
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()

    return provider


def setup_client(test_venue=False, old_api=False, credentials=CREDENTIALS_PATH):
    """
    Setup an OpenReview client.
    test_venue: If true create a client to the test venue instead.
    old_api: If true use the v1 OpenReview API, otherwise use the v2 API.
    credentials: Path to the credentials JSON file.
    """
    # Get credentials from the user.
    credentials = read_credentials(credentials)
    if not credentials:
        return None

    # Setup the client.
    client = None
    if old_api:
        client = openreview.Client(
            baseurl=f"https://{'dev' if test_venue else ''}api.openreview.net",
            username=credentials["username"],
            password=credentials["password"],
        )
    else:
        client = OpenReviewClient(
            baseurl=f"https://{'dev' if test_venue else ''}api2.openreview.net",
            username=credentials["username"],
            password=credentials["password"],
            mfa_code_provider=op_otp_provider(credentials, test_venue),
        )

    # Verify the client.
    try:
        # Newer openreview-py versions reject get_profile() without an id.
        user = getattr(client, "user", None) or {}
        user_id = user.get("profile", {}).get("id") or user.get("id")
        if not user_id:
            user_id = client.get_profile(credentials["username"]).id
        print(f"OpenReview client initialized successfully (User: {user_id}).")
    except Exception as e:
        print("Error initializing OpenReview client:", e)
        return None
    return client


def get_venue(client):
    try:
        venue = client.get_group(VENUE)
        print("Venue found:", venue.id)
    except Exception as e:
        print("Error finding venue:", e)
        return None
    return venue


def setup_test_client():
    return setup_client(test=True)


def main():
    # Test the setup_client function.
    client = setup_client()
    venue = get_venue(client)
    print(client)
    print(venue)


if __name__ == "__main__":
    main()
