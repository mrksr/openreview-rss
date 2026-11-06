from utils.setup_client import setup_client
from utils.paths import VENUE, TEST_VENUE, ROOT_DIR
import openreview
import os
import csv

# Use the dev test venue instead of the real one.
USE_TEST_VENUE = False

# Only print what would be posted.
DRY_RUN = True

# CSV with one row per AC. Rows for people who are not (yet) members of the AC or SAC group are ignored.
AC_FILE = os.path.join(ROOT_DIR, "..", "lists", "acs.csv")
# Label of the proposed assignments. Browse and deploy them under this name in OpenReview.
ASSIGNMENT_LABEL = "Manual_SAC_AC"

AC_COLUMN = "Your OpenReview ID"
SAC_COLUMN = "Your SAC's OpenReview ID"


def normalize_id(raw):
    # Fix whitespace and missing '~' from free-text form answers.
    raw = raw.strip()
    if raw and "@" not in raw and not raw.startswith("~"):
        raw = "~" + raw
    return raw


def read_pairs():
    pairs = []  # (ac, sac)
    with open(AC_FILE, "r") as f:
        for row in csv.DictReader(f):
            ac = normalize_id(row[AC_COLUMN])
            sac = normalize_id(row[SAC_COLUMN])
            if ac and sac:
                pairs.append((ac, sac))
    print(f"Read {len(pairs)} AC/SAC pairs from '{AC_FILE}'.")
    return pairs


def get_members(client, group_id):
    # Members are people who accepted. Invited people are in a separate group and are not touched.
    return client.get_group(group_id).members


def get_existing(client, invitation):
    edges = client.get_all_edges(invitation=invitation, label=ASSIGNMENT_LABEL)
    return {(e.head, e.tail) for e in edges}


def post_proposed_edges(client, venue, invitation, pairs, acs, sacs):
    """
    The only function that writes to OpenReview. It posts nothing but Proposed_Assignment edges between existing group members. It never creates or invites users or groups and never deploys.
    """
    expected = f"{venue}/Senior_Area_Chairs/-/Proposed_Assignment"
    if invitation != expected:
        raise ValueError(f"Refusing to write to '{invitation}', expected '{expected}'.")
    # The invitation must already exist. This raises if it does not.
    client.get_invitation(invitation)
    acs = set(acs)
    sacs = set(sacs)
    for ac, sac in pairs:
        if ac not in acs or sac not in sacs:
            raise ValueError(f"Refusing to write edge {ac} -> {sac}: not both group members.")

    edges = [
        openreview.api.Edge(
            invitation=invitation,
            head=ac,
            tail=sac,
            label=ASSIGNMENT_LABEL,
            weight=1,
            signatures=[f"{venue}/Program_Chairs"],
            # Fixed by the invitation: readers are the venue, the tail (SAC), and the head (AC).
            readers=[venue, sac, ac],
            writers=[venue],
        )
        for ac, sac in pairs
    ]
    openreview.tools.post_bulk_edges(client, edges)


def alias_map(client, ids_or_emails):
    """
    Map every given id or email, and every alias of its profile, to the canonical profile id. People with several profile ids or emails then still match. Ids without a profile map to themselves.
    """
    queries = [q.strip().lower() if "@" in q else q.strip() for q in ids_or_emails]
    aliases = {q: q for q in queries}
    for profile in openreview.tools.get_profiles(client, queries):
        names = profile.content.get("names", [])
        for alias in [profile.id] + [n["username"] for n in names if n.get("username")]:
            aliases[alias] = profile.id
        for email in profile.content.get("emails", []):
            aliases[email.lower()] = profile.id
    return aliases


def assign_acs_to_sacs(client, venue):
    invitation = f"{venue}/Senior_Area_Chairs/-/Proposed_Assignment"
    pairs = read_pairs()
    acs = get_members(client, f"{venue}/Area_Chairs")
    sacs = get_members(client, f"{venue}/Senior_Area_Chairs")
    print(f"Found {len(acs)} ACs and {len(sacs)} SACs in OpenReview.")

    # Map everything to one canonical id per person, so that alias profiles and emails still match.
    aliases = alias_map(client, [a for a, _ in pairs] + [s for _, s in pairs] + acs + sacs)
    canon = lambda x: aliases.get(x.lower() if "@" in x else x, x)
    ac_ids = {canon(a): a for a in acs}  # canonical id: group member id
    sac_ids = {canon(s): s for s in sacs}

    edges = []
    ignored_acs = set()
    ignored_sacs = set()
    seen = set()
    for ac, sac in pairs:
        ac_member = ac_ids.get(canon(ac))
        sac_member = sac_ids.get(canon(sac))
        if ac_member is None:
            ignored_acs.add(ac)
        if sac_member is None:
            ignored_sacs.add(sac)
        if ac_member is None or sac_member is None:
            continue
        if (ac_member, sac_member) in seen:
            continue
        seen.add((ac_member, sac_member))
        edges.append((ac_member, sac_member))

    print(f"Ignoring {len(ignored_acs)} rows with ACs that are not in the AC group:")
    for ac in sorted(ignored_acs):
        print(f"- {ac}")
    print(f"Ignoring {len(ignored_sacs)} SACs that are not in the SAC group:")
    for sac in sorted(ignored_sacs):
        print(f"- {sac}")

    # Do not post duplicates.
    existing = get_existing(client, invitation)
    new_edges = [e for e in edges if e not in existing]
    print(f"{len(edges)} valid pairs, {len(edges) - len(new_edges)} already exist.")

    # An AC must only have one SAC.
    by_ac = {}
    for ac, sac in edges:
        by_ac.setdefault(ac, set()).add(sac)
    for ac, s in by_ac.items():
        if len(s) > 1:
            print(f"WARNING: {ac} is listed with several SACs: {sorted(s)}. Skipping this AC.")
    new_edges = [e for e in new_edges if len(by_ac[e[0]]) == 1]
    for ac, sac in existing:
        if ac in by_ac and sac not in by_ac[ac]:
            print(f"WARNING: {ac} already has SAC {sac} with label '{ASSIGNMENT_LABEL}'.")

    if not new_edges:
        print("Nothing to post.")
        return
    for ac, sac in new_edges:
        print(f"{ac} -> {sac}")
    if DRY_RUN:
        print(f"Dry run: would post {len(new_edges)} edges to '{invitation}'.")
        return
    while True:
        answer = input(f"Post {len(new_edges)} edges to '{invitation}'? (y/n): ")
        if answer.lower() == "n":
            print("Aborted.")
            return
        if answer.lower() == "y":
            break

    post_proposed_edges(client, venue, invitation, new_edges, acs, sacs)
    print(f"Posted {len(new_edges)} edges with label '{ASSIGNMENT_LABEL}'.")
    print("Browse and deploy them from the Senior Area Chairs Assignments page.")


def main():
    client = setup_client(test_venue=USE_TEST_VENUE)
    assign_acs_to_sacs(client, TEST_VENUE if USE_TEST_VENUE else VENUE)


if __name__ == "__main__":
    main()
