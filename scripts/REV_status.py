from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
from utils.profiles import ProfileMatcher
from utils.messaging import is_email_address, is_openreview_id
import csv
import os
import openreview

# Where to write the output.
STATUS_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "Reviewers.csv")

# CSV file to read to parse reviewers to be invited.
REV_LIST_FILE = os.path.join(
    ROOT_DIR, "private", "RSS2025-Reviewers - Reviewer Invitations.csv"
)

# Output file to save new reviewer invitations to be sent via OpenReview recruitment forms.
REV_INVITATION_FILE = os.path.join(ROOT_DIR, "private", "New_Reviewer_Invitations.csv")

"""
Read the initial specific RSS 2027 Reviewers spread sheet, invite new reviewers, check the status of selected reviewers.
"""


def read_rev_list():
    print(f"Reading Reviewers from {REV_LIST_FILE}.")
    with open(REV_LIST_FILE, "r") as f:
        reader = csv.reader(f)
        skip_rows = 4
        reviewers = []
        incomplete_reviewers = []
        declined_reviewers = []
        current_AC = None
        for row in reader:
            # Skip header rows
            if skip_rows > 0:
                skip_rows -= 1
                continue

            # Check AC headers
            if row[0].startswith("Area Chair"):
                current_AC = row[1]
                continue

            # Check if valid format.
            if not row[0].isdigit() or not row[1] or row[1].isspace():
                continue

            reviewer = {
                "name": row[1],
                "email": row[2].lower().strip(),
                "ac": current_AC,
                "ac_num": int(row[0]),
            }

            if not row[1] or not is_email_address(row[2]):
                # Check whether they should be invited.
                if row[4].lower() == "yes" or row[4].lower() == "y":
                    incomplete_reviewers.append(reviewer)
                continue

            reviewer.update(
                {
                    "invited": row[4].lower().startswith("yes"),
                    "agreed": row[5].lower().startswith("yes"),
                    "status": row[7],
                    "id": row[10],
                }
            )
            reviewers.append(reviewer)
    print(
        f"Found {len(reviewers)} reviewers, {len(incomplete_reviewers)} incomplete reviewers, and {len(declined_reviewers)} declined reviewers."
    )
    return reviewers, incomplete_reviewers, declined_reviewers


def print_incomplete_reviewers(incomplete_reviewers):
    print(
        f" ========== Found {len(incomplete_reviewers)} incomplete reviewers: =========="
    )
    acs_with_incomplete_reviewers = set()
    for rev in incomplete_reviewers:
        print(f"- {rev['name']} ({rev['email']}) assigned to {rev['ac']}.")
        acs_with_incomplete_reviewers.add(rev["ac"])
    print(f"ACs with incomplete reviewers: {', '.join(acs_with_incomplete_reviewers)}.")


def add_reviewer_openreview_ids(reviewers_list: list, pm: ProfileMatcher):
    # Add OpenReview IDs to reviewers.
    reviewers = {}
    pm.add_profiles([r["email"] for r in reviewers_list])
    with_profile = 0
    for r in reviewers_list:
        id = pm.get_id(r["email"])
        if is_openreview_id(id):
            with_profile += 1
        r["id"] = id
        if id in reviewers:
            reviewers[id]["acs"].add(r["ac"])
        else:
            reviewers[id] = {"acs": set([r["ac"]])}
    print(
        f"Found {len(reviewers)} unique reviewers from {len(reviewers_list)} listed ({with_profile}/{len(reviewers)} with profile)."
    )
    return reviewers


def get_reviewer_status(reviewers: dict, client, pm: ProfileMatcher):
    # Get reviewers data.
    print("Checking Reviewer Status...")
    status = {}
    groups = ["Reviewers/Invited", "Reviewers", "Reviewers/Declined"]
    group_to_status = {
        "Reviewers": "Accepted",
        "Reviewers/Invited": "Invited",
        "Reviewers/Declined": "Declined",
    }
    for group in groups:
        status_group = set()
        members = client.get_group(f"{VENUE}/{group}").members
        pm.add_profiles(members)
        for key in members:
            status_group.add(pm.get_id(key))
        status[group] = status_group

    # Check status of each reviewer.
    num = {g: 0 for g in groups}
    matched = {g: set() for g in groups}
    num_not_found = 0
    for id, r in reviewers.items():
        found = False
        for g in groups:
            if id in status[g]:
                r["status"] = group_to_status[g]
                num[g] += 1
                matched[g].add(id)
                found = True
        if not found:
            r["status"] = "Not Found"
            num_not_found += 1

    print(
        f"Accepted: {num['Reviewers']}, Declined: {num['Reviewers/Declined']}, Invited: {num['Reviewers/Invited']}, Not Found: {num_not_found}"
    )
    for g in groups:
        unmatched_registrations = status[g] - matched[g]
        if unmatched_registrations:
            print(
                f"Found {len(unmatched_registrations)} unmatched {group_to_status[g]} IDs:"
            )
            for id in unmatched_registrations:
                print(f"- '{id}'")


def get_reviewer_registration(reviewers: dict, client, pm: ProfileMatcher):
    registration_notes = client.get_all_notes(
        invitation=f"{VENUE}/Reviewers/-/Registration"
    )
    registrations = set()
    unmatched_registrations = set()
    pm.add_profiles([note.signatures[0] for note in registration_notes])
    for note in registration_notes:
        id = pm.get_id(note.signatures[0])
        registrations.add(id)
        data = {}

        data["registration_completed"] = (
            note.content["profile_confirmed"]["value"] == "Yes"
            and note.content["expertise_confirmed"]["value"] == "Yes"
        )
        data["keywords"] = note.content["keyword_selection"]["value"]
        data["num_keywords"] = len(data["keywords"])

        if id in reviewers:
            reviewers[id].update(data)
        else:
            unmatched_registrations.add(id)

    # Fill in missing registration data.
    for id, data in reviewers.items():
        if "registration_completed" not in data:
            data["registration_completed"] = False
            data["keywords"] = []
            data["num_keywords"] = 0

    if unmatched_registrations:
        print(
            f"Found {len(unmatched_registrations)} unmatched registration signatures:"
        )
        for id in unmatched_registrations:
            print(f"- '{id}'")


def merge_reviewer_list(reviewer_list, reviewers):
    # Merge reviewer list with reviewer data.
    for r in reviewer_list:
        if r["id"] in reviewers:
            r.update(reviewers[r["id"]])
        else:
            r["status"] = "Not Found"
            r["registration_completed"] = False
            r["keywords"] = []
            r["num_keywords"] = 0
            r["acs"] = set()


def write_reviewer_status(reviewer_list, output_file):
    reviewers_to_save = reviewer_list.copy()
    with open(output_file, "w") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "email",
                "id",
                "status",
                "registration_completed",
                "keywords",
                "num_keywords",
                "ac",
                "ac_num",
                "invited",
                "agreed",
                "acs",
            ],
        )
        writer.writeheader()
        for row in reviewers_to_save:
            row["keywords"] = ";".join(row["keywords"])
            row["acs"] = ", ".join(row["acs"]) if len(row["acs"]) > 1 else ""
            row["registration_completed"] = (
                "Completed" if row["registration_completed"] else "Missing"
            )
            if row["status"] == "Not Found" and (
                not row["agreed"] or not row["invited"]
            ):
                row["status"] = ""
            writer.writerow(row)
    print(f"Wrote Reviewer status to {output_file}.")


def read_reviewer_status(file_path):
    reviewers = []
    if not os.path.exists(file_path):
        print(f"Status file '{file_path}' does not exist.")
        return reviewers
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert strings to correct types.
            row["num_keywords"] = int(row["num_keywords"])
            row["keywords"] = row["keywords"].split(";") if row["keywords"] else []
            row["acs"] = set(row["acs"].split(", ")) if row["acs"] else set()
            reviewers.append(row)
    print(f"Read {len(reviewers)} Reviewers from '{file_path}'.")
    return reviewers


def write_new_reviewer_invitations(reviewer_list, output_file):
    num_new_reviewers = 0
    with open(output_file, "w") as f:
        for reviewer in reviewer_list:
            if not reviewer["invited"]:
                continue
            if reviewer["status"] in ["Accepted", "Declined", "Invited"]:
                continue
            # Write the invitation.
            f.write(f"{reviewer['email']}, {reviewer['name']}\n")
            num_new_reviewers += 1

    print(f"Wrote {num_new_reviewers} new reviewer invitations to {output_file}.")


def verify_reviewer_invitations(reviewer_list, reviewers):
    # Run this after the most recent sheet has been downloaded.
    print("Running reviewer list verification. This is only relevant if the sheet has been updated and re-downloaded.")
    status_priority = {"Accepted": 3, "Invited": 2, "Declined": 1}
    sheet_highest_status = {} # id: status
    for r in reviewer_list:
        current_status = sheet_highest_status.get(r["id"], "")
        if status_priority.get(r["status"], 0) > status_priority.get(current_status, 0):
            sheet_highest_status[r["id"]] = r["status"]

    invited_not_in_list = {}  # id: (sheet, or)
    accepted_not_in_list = {}  # id: (sheet, or)
    for id, sheet_status in sheet_highest_status.items():
        if id not in reviewers:
            continue
        or_status = reviewers[id]["status"]
        if or_status == "Invited" and sheet_status != "Invited":
            invited_not_in_list[id] = (sheet_status, or_status)
        if or_status == "Accepted" and sheet_status != "Accepted":
            accepted_not_in_list[id] = (sheet_status, or_status)

    if invited_not_in_list:
        print(f"Found {len(invited_not_in_list)} invited reviewers not in the list:")
        for id, status in invited_not_in_list.items():
            print(f"- {id}: Sheet: {status[0]}, OR: {status[1]}")
    if accepted_not_in_list:
        print(f"Found {len(accepted_not_in_list)} accepted reviewers not in the list:")
        for id, status in accepted_not_in_list.items():
            print(f"- {id}: Sheet: {status[0]}, OR: {status[1]}")
    print("Reviewer list verification completed.")


def main():
    # Read reviewers to invite from the spreadsheet.
    reviewer_list, incomplete_reviewers, declined_reviewers = read_rev_list()
    # print_incomplete_reviewers(incomplete_reviewers)
    client = setup_client()
    pm = ProfileMatcher(client)
    reviewers = add_reviewer_openreview_ids(reviewer_list, pm)

    # Update the status of all reviewers.
    get_reviewer_status(reviewers, client, pm)
    get_reviewer_registration(reviewers, client, pm)

    # Optionally verify reviewer invitations.
    verify_reviewer_invitations(reviewer_list, reviewers)

    # Merge and write the final list.
    merge_reviewer_list(reviewer_list, reviewers)
    write_reviewer_status(reviewer_list, STATUS_OUTPUT_FILE)

    # Create invitations for new reviewers.
    write_new_reviewer_invitations(reviewer_list, REV_INVITATION_FILE)


if __name__ == "__main__":
    main()
