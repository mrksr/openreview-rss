import csv
from utils.setup_client import setup_client
from utils.paths import ROOT_DIR, VENUE
from SUB_inspection import get_domain_from_profile
from utils.messaging import is_email_address
from utils.parse_notes import is_accepted
import openreview
import os

OUT_FILE = os.path.join(ROOT_DIR, "private", "accepted_papers_3.csv")


def read_accepted(client, include_affiliations=False):
    # ID, authors, affiliation, titles.
    submissions = client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    )
    data = {}  # paper_no: {authors, title, affiliations}

    print(
        "Reading submission"
        + (" and affiliation" if include_affiliations else "")
        + " data..."
    )
    for sub in submissions:
        # Only accepted papers.
        paper_nr = sub.number

        if not is_accepted(sub):
            continue

        title = sub.content["title"]["value"]
        abstract = sub.content["abstract"]["value"]
        category = sub.content["category"]["value"]
        abstract_confirmed = "confirmation_that_abstract_is_correct" in sub.content
        if not include_affiliations:
            data[paper_nr] = {
                "title": title,
                "abstract": abstract,
                "category": category,
                "abstract_confirmed": abstract_confirmed,
            }
            continue

        authors = sub.content["authors"]["value"]
        author_ids = sub.content["authorids"]["value"]
        keywords = sub.content["keywords"]["value"]
        profiles = openreview.tools.get_profiles(client, author_ids)
        affiliations = set()
        for p in profiles:
            affiliation = get_domain_from_profile(p)
            if affiliation:
                affiliations.add(affiliation)
        for a in author_ids:
            if is_email_address(a):
                affiliation = a.split("@")[-1]
                affiliations.add(affiliation)
        data[paper_nr] = {
            "authors": authors,
            "title": title,
            "abstract": abstract,
            "category": category,
            "affiliations": list(affiliations),
            "keywords": keywords,
        }
    print(f"Found {len(data)} accepted papers.")
    return data


def save_accepted_papers(papers, out_file=OUT_FILE):
    with open(out_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Paper No", "Title", "Authors", "Affiliations", "Keywords"])
        for no, data in papers.items():
            writer.writerow([no, data["title"], ";".join(data["authors"]), ";".join(data["affiliations"]), ";".join(data["keywords"])])
    print(f"Saved accepted papers to '{out_file}'")


def main():
    client = setup_client()
    papers = read_accepted(client)
    save_accepted_papers(papers)


if __name__ == "__main__":
    main()
