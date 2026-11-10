from utils.setup_client import setup_client
from utils.paths import VENUE, TEST_VENUE, ROOT_DIR
from SAC_assign_acs import normalize_id, get_members
import openreview
import os
import csv

# Use the dev test venue instead of the real one.
USE_TEST_VENUE = False

# CSV with one row per Shepherd (RSS 2027 name for Reviewers), from the Shepherd sign-up form.
SHEPHERD_FILE = os.path.join(ROOT_DIR, "..", "lists", "reviewers.csv")
# Validated AC -> Shepherd pools. Input for the pool-restricted affinity and conflict edges once papers exist.
POOL_FILE = os.path.join(ROOT_DIR, "private", "shepherd_pools.csv")

SHEPHERD_COLUMN = "Your OpenReview ID"
AC_COLUMN = "Your AC's OpenReview ID"
NAME_COLUMN = "Name (First, Last)"
WORKLOAD_COLUMN = "Maximum desired workload"


def read_rows():
    rows = []
    with open(SHEPHERD_FILE, "r") as f:
        for row in csv.DictReader(f):
            shepherd = normalize_id(row[SHEPHERD_COLUMN])
            ac = normalize_id(row[AC_COLUMN])
            if shepherd and ac:
                rows.append((shepherd, ac, row))
    print(f"Read {len(rows)} Shepherd/AC pairs from '{SHEPHERD_FILE}'.")
    return rows


def alias_map(client, ids_or_emails):
    """
    Like SAC_assign_acs.alias_map, but resolves ids and emails separately. The combined
    openreview.tools.get_profiles call fails on this list ("The field ids cannot be empty").
    """
    queries = {q.strip().lower() if "@" in q else q.strip() for q in ids_or_emails}
    queries.discard("")
    aliases = {q: q for q in queries}
    ids = sorted(q for q in queries if q.startswith("~"))
    emails = sorted(q for q in queries if "@" in q)
    profiles = list(openreview.tools.get_profiles(client, ids)) if ids else []
    # Email lookups are refused for this account, so emails only match group members listed by the same email.
    for email in emails:
        print(f"Cannot resolve '{email}' to a profile. Fix the CSV row by hand if this person has an id.")
    for profile in profiles:
        names = profile.content.get("names", [])
        for alias in [profile.id] + [n["username"] for n in names if n.get("username")]:
            aliases[alias] = profile.id
        for email in profile.content.get("emails", []):
            aliases[email.lower()] = profile.id
    return aliases


def workload(row):
    digits = "".join(c for c in row.get(WORKLOAD_COLUMN, "") if c.isdigit())
    return int(digits) if digits else 0


def build_pools(client, venue):
    rows = read_rows()
    shepherds = get_members(client, f"{venue}/Shepherds")
    acs = get_members(client, f"{venue}/Area_Chairs")
    print(f"Found {len(shepherds)} Shepherds and {len(acs)} ACs in OpenReview.")

    aliases = alias_map(client, [s for s, _, _ in rows] + [a for _, a, _ in rows] + shepherds + acs)
    canon = lambda x: aliases.get(x.lower() if "@" in x else x, x)
    shepherd_ids = {canon(s): s for s in shepherds}  # canonical id: group member id
    ac_ids = {canon(a): a for a in acs}

    pairs = {}  # shepherd member id: {ac member id: row}
    ignored_shepherds = set()
    ignored_acs = {}  # listed AC that is not in the AC group: shepherds naming them
    for shepherd, ac, row in rows:
        shepherd_member = shepherd_ids.get(canon(shepherd))
        ac_member = ac_ids.get(canon(ac))
        if shepherd_member is None:
            ignored_shepherds.add(shepherd)
            continue
        if ac_member is None:
            ignored_acs.setdefault(ac, set()).add(shepherd_member)
            continue
        pairs.setdefault(shepherd_member, {})[ac_member] = row

    print(f"Ignoring {len(ignored_shepherds)} rows with Shepherds that are not in the Shepherds group (pending, declined, or not invited):")
    for s in sorted(ignored_shepherds):
        print(f"- {s}")
    print(f"WARNING: {sum(len(v) for v in ignored_acs.values())} accepted Shepherds name an AC that is not in the AC group:")
    for ac, s in sorted(ignored_acs.items()):
        print(f"- {ac}: {', '.join(sorted(s))}")

    # A Shepherd must only have one AC.
    multi = {s: a for s, a in pairs.items() if len(a) > 1}
    for s, a in sorted(multi.items()):
        print(f"WARNING: {s} is listed with several ACs: {sorted(a)}. Skipping this Shepherd.")

    # Shepherds who accepted but have no usable row.
    listed = set(pairs) | {s for v in ignored_acs.values() for s in v}
    unlisted = sorted(set(shepherds) - listed)
    print(f"WARNING: {len(unlisted)} accepted Shepherds have no row in the sign-up CSV:")
    for s in unlisted:
        print(f"- {s}")

    pools = {}  # ac: [(shepherd, row)]
    for s, a in pairs.items():
        if s in multi:
            continue
        (ac, row), = a.items()
        pools.setdefault(ac, []).append((s, row))

    empty = sorted(set(acs) - set(pools))
    print(f"WARNING: {len(empty)} ACs have no accepted Shepherds:")
    for ac in empty:
        print(f"- {ac}")

    print(f"\n{sum(len(v) for v in pools.values())} Shepherds in {len(pools)} AC pools (Shepherds / summed max papers):")
    for ac, members in sorted(pools.items(), key=lambda x: len(x[1])):
        print(f"{ac}: {len(members)} / {sum(workload(r) for _, r in members)}")
    return pools


def write_pools(pools):
    with open(POOL_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ac", "shepherd", "name", "max_papers"])
        for ac, members in sorted(pools.items()):
            for s, row in sorted(members):
                w.writerow([ac, s, row[NAME_COLUMN], workload(row)])
    print(f"Wrote pools to '{POOL_FILE}'.")


def main():
    client = setup_client(test_venue=USE_TEST_VENUE)
    pools = build_pools(client, TEST_VENUE if USE_TEST_VENUE else VENUE)
    write_pools(pools)


if __name__ == "__main__":
    main()
