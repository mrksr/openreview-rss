from utils.messaging import is_email_address, is_openreview_id
from utils.paths import ROOT_DIR
import os
import json
import openreview

"""
Tools to get a unique OpenReview profile for potentially several email addresses and hopefully solve multiple profiles as well.
"""


class ProfileMatcher:
    def __init__(self, client, ids_or_emails = [], associated_profiles=None):
        self.client = client  # OpenReview Client to get info.
        self._ids = set()  # unique_ids (OpenReview ID if it exists, otherwise email)
        self._id_map = {}  # openreview id to unique_id
        self._emails = {}  # email to unique_id
        self._email_map = {}  # all emails for an uid.
        self._names = {}  # full name for an uid.

        # Optional: Initialization
        # Read associated profiles if possible.
        default_file = os.path.join(ROOT_DIR, "private", "associated_profiles.json")
        if associated_profiles is None and os.path.exists(default_file):
            associated_profiles = json.load(open(default_file))

        if associated_profiles:
            profiles_to_get = associated_profiles.keys() | associated_profiles.values()
            profiles = openreview.tools.get_profiles(self.client, profiles_to_get)

            # Add all associated profiles.
            for id_from, id_to in associated_profiles.items():
                if is_openreview_id(id_from):
                    self._id_map[id_from] = id_to
                elif is_email_address(id_from):
                    self._emails[id_from] = id_to
                    if id_to not in self._email_map:
                        self._email_map[id_to] = set()
                    self._email_map[id_to].add(id_from)
                self._ids.add(id_to)

            for p in profiles:
                target_id = self.get_id(p.id)
                if target_id in associated_profiles:
                    target_id = associated_profiles[target_id]
                for email in p.content["emails"]:
                    self._emails[email] = target_id
                    if target_id not in self._email_map:
                        self._email_map[target_id] = set()
                    self._email_map[target_id].add(email)
                if "names" in p.content and p.content["names"]:
                    self._names[target_id] = p.content["names"][0]["fullname"]

        if ids_or_emails:
            self.add_profiles(ids_or_emails)

    def add_profiles(self, ids_or_emails):
        """
        Add a list of profiles, as email addresses or openreview ids or a mix thereof, to the profile matcher. If there are existing profiles, the new ones will be linked to the existing ones to keep previous keys intact.
        """
        # Get all profile information.
        queries = [
            (m.lower() if is_email_address(m) else m).strip() for m in ids_or_emails
        ]
        # NOTE(lschmid): This will only get existing profiles.
        profiles = openreview.tools.get_profiles(self.client, queries)

        # Add all existing profiles.
        for profile in profiles:
            self._add_profile(profile)

        # Check all input IDs and emails that were not associated.
        for query in queries:
            if is_openreview_id(query) and query not in self._ids:
                try:
                    profile = openreview.tools.get_profile(self.client, query)
                    if profile is not None:
                        self._add_profile(profile, query)
                except openreview.openreview.OpenReviewException:
                    continue
            if is_email_address(query) and query not in self._emails:
                # If no profile exists use the email as key.
                self._emails[query] = query
                self._email_map[query] = [query]
                self._ids.add(query)

    def _add_profile(self, profile, query=None):
        """
        Add a profile to the matcher. Optionally also provide the query to add.
        """
        target_id = profile.id

        # Check if the profile was already added.
        if target_id in self._ids:
            if query is not None:
                if is_openreview_id(query):
                    self._id_map[query] = target_id
                if is_email_address(query):
                    self._emails[query] = target_id
                    self._email_map[target_id].add(query)
            return

        # Check linked IDs.
        if target_id in self._id_map:
            target_id = self._id_map[target_id]
        else:
            # Check links via duplicate emails.
            for email in profile.content["emails"]:
                if email in self._emails:
                    target_id = self._emails[email]
                    self._id_map[profile.id] = target_id
                    break
            if target_id == profile.id:
                # This is a new profile.
                self._ids.add(target_id)

        # Add email links.
        for email in profile.content["emails"]:
            self._emails[email] = target_id
            if target_id not in self._email_map:
                self._email_map[target_id] = set()
            self._email_map[target_id].add(email)

        # Add name.
        if "names" in profile.content and profile.content["names"]:
            self._names[target_id] = profile.content["names"][0]["fullname"]

    def get_id(self, id_or_email):
        """
        Get the unique profile id for a given email address or openreview_id.
        """
        if is_openreview_id(id_or_email):
            if id_or_email in self._id_map:
                return self._id_map[id_or_email]
            return id_or_email
        if is_email_address(id_or_email):
            email = id_or_email.lower().strip()
            if email in self._emails:
                return self._emails[email]
            return email
        print(f"Invalid email address or openreview_id: {id_or_email}")
        return None
    
    def get_name(self, id_or_email):
        """
        Get the full name for a given email address or openreview_id.
        """
        id = self.get_id(id_or_email)
        return self._names.get(id, id_or_email)

    def update_ids(self, list_or_dict):
        if list_or_dict is list:
            list_or_dict = [self.get_id(id) for id in list_or_dict]
        elif list_or_dict is dict:
            list_or_dict = {self.get_id(k): v for k, v in list_or_dict.items()}

    def num_profiles(self):
        return len(self._ids)

    def num_emails(self):
        return len(self._emails)

    def num_duplicate_profiles(self):
        return len(self._id_map)

    def all_ids(self):
        return self._ids

    def get_emails(self, id):
        return self._email_map.get(id, [])

    def print(self):
        """
        Print all known profiles and their associated emails and IDs.
        """
        print("Known Profiles:")
        for id in self._ids:
            print(f"{id}:")
            for id_from, id_to in self._id_map.items():
                if id_to == id:
                    print(f"  '{id_from}'")
            for email in self.get_emails(id):
                print(f"  '{email}'")
