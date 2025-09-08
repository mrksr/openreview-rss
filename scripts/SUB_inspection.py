from utils.setup_client import setup_client
from utils.messaging import is_email_address
from utils.paths import VENUE, ROOT_DIR
from SUB_verify_initial_papers import REQUIREMENTS, CONFIRMATION_FIELDS
import openreview
import pickle
import os
import csv

"""
Tools to get stats and lists of papers for specific categories of submissions.
"""

SUBMISSION_DATA_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "submission_data.csv")


def get_domain_from_profile(profile):
    if not "history" in profile.content:
        return None
    history = profile.content["history"]
    if not "institution" in history[0]:
        return None
    return history[0]["institution"].get("domain", None)


def get_submission_affiliations(client):
    # Only 'active' submissions
    submissions = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    data = {}  # affiliation: papers

    print("Reading affiliation data...")
    for sub in submissions:
        paper_nr = sub.number
        authors = sub.content["authorids"]["value"]
        profiles = openreview.tools.get_profiles(client, authors)
        for p in profiles:
            affiliation = get_domain_from_profile(p)
            if not affiliation:
                continue
            if not affiliation in data:
                data[affiliation] = set()
            data[affiliation].add(paper_nr)
        for a in authors:
            if is_email_address(a):
                affiliation = a.split("@")[-1]
                if not affiliation in data:
                    data[affiliation] = set()
                data[affiliation].add(paper_nr)
    print(f"Found {len(data)} affiliations in {len(submissions)} papers.")
    return data


def lazy_submissions(client, force_recompute=False):
    cache_file = os.path.join(ROOT_DIR, "private", "cache", "affiliations.p")
    if os.path.exists(cache_file) and not force_recompute:
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    affiliations = get_submission_affiliations(client)
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(affiliations, f)
    return affiliations


def analyze_affiliations(affiliations):
    SEARCH_KEYS = [f"{x}." for x in ["affiliation1", "affiliation2"]]
    affected_papers = set()
    for a in affiliations:
        if any([k in a.lower() for k in SEARCH_KEYS]):
            print(f"Found {a} with {len(affiliations[a])} papers.")
            affected_papers.update(affiliations[a])
    print(f"Found {len(affected_papers)} affected papers:")
    for p in sorted(affected_papers):
        print(f"- {p}")
    return affected_papers


def get_sac_authored_papers(client):
    sacs = client.get_group(f"{VENUE}/Senior_Area_Chairs").members
    papers = {}  # paper_nr: sac
    # Only 'active' submissions
    for sub in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}):
        paper_nr = sub.number
        for sac in sacs:
            if sac in sub.content["authorids"]["value"]:
                papers[paper_nr] = sac
                break
    print(f"Found {len(papers)} papers with SAC authorship:")
    for nr, sac in papers.items():
        print(f"- {nr} ({sac})")
    return papers


def get_submission_overview_sheet(client, affected_papers, sac_authored_papers):
    # Get submissions.
    submissions = client.get_all_notes(invitation=f"{VENUE}/-/Submission")
    # paper number, title, link, category, authors, HasPDF, ChecklistComplete, from LA, SAC authored
    with open(SUBMISSION_DATA_OUTPUT_FILE, "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "Paper Number",
                "Title",
                "Link",
                "Category",
                "Authors",
                "HasPDF",
                "ChecklistComplete",
                "From LA",
                "SAC Authored",
            ]
        )
        for sub in submissions:
            data = [
                sub.number,
                sub.content["title"]["value"],
                f"https://openreview.net/forum?id={sub.id}",
                sub.content["category"]["value"],
                ", ".join(sub.content["authors"]["value"]),
            ]

            # PDF
            data.append(sub.content.get("pdf", {}).get("value") is not None)

            # Checklist
            confirmations = set()
            for field in CONFIRMATION_FIELDS:
                confirmations.update(sub.content.get(field, {"value": []})["value"])
            missing_confirmations = [
                c for c in REQUIREMENTS[data[3]] if c not in confirmations
            ]
            data.append(len(missing_confirmations) == 0)

            # From LA
            data.append(sub.number in affected_papers)
            # SAC authored
            data.append(sub.number in sac_authored_papers)
            writer.writerow(data)
    print(f"Wrote submission overview sheet to '{SUBMISSION_DATA_OUTPUT_FILE}'")


def main():
    client = setup_client()
    # Get affiliation data.
    affiliations = lazy_submissions(client, force_recompute=False)
    affected_papers = analyze_affiliations(affiliations)

    # Check SAC authored papers.
    sac_authored_papers = get_sac_authored_papers(client)

    # Write submission overview sheet.
    get_submission_overview_sheet(client, affected_papers, sac_authored_papers)


if __name__ == "__main__":
    main()
