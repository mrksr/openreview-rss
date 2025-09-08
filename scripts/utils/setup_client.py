import openreview
from openreview.api import OpenReviewClient
import json
import os

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
        )

    # Verify the client.
    try:
        user_profile = client.get_profile()
        print(f"OpenReview client initialized successfully (User: {user_profile.id}).")
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
