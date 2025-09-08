from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
from utils.profiles import ProfileMatcher
from utils.messaging import is_openreview_id

import csv
import os


# Where to write the output.
STATUS_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "ACs.csv")

# Original Programm Committee Google Sheet (exported as CSV)
AC_LIST_FILE = os.path.join(ROOT_DIR, "private", "ProgramCommittee - ACs.csv")

# Area Chair roles to be read from OpenReview.
AC_ROLES = ["Area_Chairs", "Senior_Area_Chairs"]

"""
Get a CSV of current AC acceptance and registration status.

NOTE(lschmid): Some profiles have several emails, thus matching by email does not work great. Some emails are private, so we can not automatically get them from the OpenReview Profiles (see PRIVATE_EMAILS_FILE). Finally, some ACs have several profiles which seem to mix up the data association. Have not yet found a good way to handle this.
"""


def read_ac_list(file_path=AC_LIST_FILE):
    acs = []
    if not os.path.exists(file_path):
        print(f"AC list file '{file_path}' does not exist.")
        return acs
    with open(file_path, "r") as f:
        reader = csv.reader(f)
        skip_rows = 3
        for row in reader:
            # Skip header rows
            if skip_rows > 0:
                skip_rows -= 1
                continue

            # Valid format requires Name and email.
            if len(row) < 15 or row[0].strip() == "" or row[14].strip() == "":
                continue

            acs.append(
                {
                    "name": row[0],
                    "selected": row[1],
                    "email": row[14],
                    "id": row[5],
                    "accepted": row[6],
                    "role": (
                        "Senior_Area_Chairs" if row[1] == "Senior AC" else "Area_Chairs"
                    ),
                    "emergency": row[1].startswith("EM"),
                }
            )
    return acs


def filter_ac_list(ac_list: list):
    """
    Remove unselected ACs from the list and parse the selection status.
    """
    all_selection_statuses = set([ac["selected"] for ac in ac_list])
    VALID_SELECTIONS = ["1", "EM - invited", "EM - accepted", "Senior AC"]
    KNOWN_INVALID_SELECTIONS = ["EM - declined", "", "0", "decline"]
    len_before = len(ac_list)
    ac_list = [ac for ac in ac_list if ac["selected"] in VALID_SELECTIONS]
    ac_list = [
        ac for ac in ac_list if not (ac["selected"] == "1" and ac["accepted"] != "1")
    ]
    print(f"Filtered ACs from {len_before} to {len(ac_list)} selected.")
    unknown_statuses = (
        all_selection_statuses - set(VALID_SELECTIONS) - set(KNOWN_INVALID_SELECTIONS)
    )
    if unknown_statuses:
        print(f"- Found unknown selection statuses: {', '.join(unknown_statuses)}")
    return ac_list


def add_openreview_ids(ac_list: list, pm: ProfileMatcher):
    # Add OpenReview IDs to reviewers.
    acs = {}
    pm.add_profiles([ac["email"] for ac in ac_list])
    with_profile = 0
    for ac in ac_list:
        id = pm.get_id(ac["email"])
        if is_openreview_id(id):
            with_profile += 1
        acs[id] = ac
        ac["id"] = id
    print(
        f"Found {len(acs)} unique area chairs from {len(ac_list)} listed ({with_profile}/{len(acs)} with profile)."
    )
    return acs


def check_ac_status(acs, client, pm):
    # Get all ACs who have accepted.
    accepted = set()
    declined = set()
    invited = set()
    for role in AC_ROLES:
        accepted.update(
            [pm.get_id(p) for p in client.get_group(f"{VENUE}/{role}").members]
        )
        declined.update(
            [pm.get_id(p) for p in client.get_group(f"{VENUE}/{role}/Declined").members]
        )
        invited.update(
            [pm.get_id(p) for p in client.get_group(f"{VENUE}/{role}/Invited").members]
        )
    for id, data in acs.items():
        if id in accepted:
            data["decision"] = "Accepted"
        elif id in declined:
            data["decision"] = "Declined"
        elif id in invited:
            data["decision"] = "Invited"
        else:
            data["decision"] = ""

    # Get all ACs who have completed registration.
    registration_notes = []
    for role in AC_ROLES:
        registration_notes.extend(
            client.get_all_notes(invitation=f"{VENUE}/{role}/-/Registration")
        )

    registrations = set()
    unmatched_registrations = set()
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

        if id in acs:
            acs[id].update(data)
        else:
            unmatched_registrations.add(id)

    # Fill in missing registration data.
    for id, data in acs.items():
        if "registration_completed" not in data:
            data["registration_completed"] = False
            data["keywords"] = []
            data["num_keywords"] = 0

    if unmatched_registrations:
        print(
            f"Found {len(unmatched_registrations)} unmatched registration signatures: {unmatched_registrations}"
        )


def write_ac_status(acs, output_file):
    with open(output_file, "w") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "email",
                "id",
                "decision",
                "registration_completed",
                "keywords",
                "num_keywords",
                "role",
                "emergency",
            ],
        )
        writer.writeheader()
        for ac in acs.values():
            to_write = ac.copy()
            to_write.pop("selected")
            to_write.pop("accepted")
            to_write["keywords"] = ";".join(to_write["keywords"])
            writer.writerow(to_write)
    print(f"Wrote Area Chairs status to {output_file}.")


def read_ac_status(file_path=STATUS_OUTPUT_FILE):
    acs = []
    if not os.path.exists(file_path):
        print(f"Status file '{file_path}' does not exist.")
        return acs
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert strings to correct types.
            row["num_keywords"] = int(row["num_keywords"])
            row["registration_completed"] = row["registration_completed"] == "True"
            row["emergency"] = row["emergency"] == "True"
            row["keywords"] = row["keywords"].split(";") if row["keywords"] else []
            acs.append(row)
    print(f"Read {len(acs)} ACs from '{file_path}'.")
    return acs


def print_ac_status(acs, compact=False):
    done = []
    accepted = []
    declined = []
    pending = []
    for id, ac in acs.items():
        if ac["registration_completed"] and ac["num_keywords"] > 0:
            done.append(id)
        elif ac["decision"] == "Accepted":
            accepted.append(id)
        elif ac["decision"] == "Declined":
            declined.append(id)
        elif ac["decision"] == "Invited":
            pending.append(id)

    if compact:
        print(
            f"AC Status Overview:\n- Completed: {len(done)}\n- Accepted:  {len(accepted)}\n- Invited:   {len(pending)}\n- Declined:  {len(declined)}\n- Total:     {len(done)+len(accepted)+len(pending)}"
        )
    else:
        print(
            f" ==================== Registration completed: {len(done)} ===================="
        )
        for ac in done:
            print(ac)
        print(f" ==================== Accepted: {len(accepted)} ====================")
        for ac in accepted:
            print(ac)
        print(f" ==================== Pending: {len(pending)} ====================")
        for ac in pending:
            print(ac)
        print(f" ==================== Declined: {len(declined)} ====================")
        for ac in declined:
            print(ac)
        print(f" ==================== Total: {len(acs)} ====================")


def print_emergency_acs_to_invite(acs):
    emergency_acs = [
        ac
        for ac in acs.values()
        if ac["selected"] == "EM - accepted" and ac["decision"] == ""
    ]
    print(f"Found {len(emergency_acs)} new emergency ACs to invite:")
    for ac in emergency_acs:
        print(f"{ac['email']},{ac['name']}")


def main():
    # Read the program committee sheet.
    ac_list = read_ac_list()
    # ac_list = filter_ac_list(ac_list)
    client = setup_client()
    pm = ProfileMatcher(client)
    acs = add_openreview_ids(ac_list, pm)

    # Update the AC status from openreview.
    check_ac_status(acs, client, pm)
    print_ac_status(acs, compact=False)
    write_ac_status(acs, STATUS_OUTPUT_FILE)

    # Optional: Print new emergency ACs to invite.
    print_emergency_acs_to_invite(acs)


if __name__ == "__main__":
    main()
