import csv
from utils.setup_client import setup_client
from utils.paths import ROOT_DIR, VENUE
from SUB_inspection import get_domain_from_profile
from utils.messaging import is_email_address
from utils.parse_notes import is_accepted, get_reviews, get_meta_reviews
import openreview
import os
import numpy as np

OUT_FILE = os.path.join(ROOT_DIR, "private", "special_issue_candidates.csv")


def read_papers(client):
    # ID, authors, affiliation, titles.
    submissions = client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    )
    data = []  # List of dicts: {paper_no, authors, title, reviews[rating, name, email]}

    print("Reading submission data...")
    for sub in submissions:
        # Only accepted papers.
        if not is_accepted(sub):
            continue

        # Paper author data.
        print(f"Parsing paper: {sub.number}")
        d = {}
        d["paper_no"] = sub.number
        d["title"] = sub.content["title"]["value"]
        d["authors"] = sub.content["authors"]["value"]

        # Review data.
        review_num = 1
        for review in get_reviews(sub):
            reviewer_signature = review["signatures"][0]
            reviewer_id = client.get_group(reviewer_signature).members[0]
            p = openreview.tools.get_profile(client, reviewer_id)
            name = p.get_preferred_name()
            email = p.get_preferred_email()
            rating = review["content"]["overall_recommendation"]["value"]
            d[f"review_{review_num}"] = {
                "rating": rating,
                "name": name,
                "email": email,
            }
            review_num += 1

        # Meta-review data.
        for meta_review in get_meta_reviews(sub):
            reviewer_signature = meta_review["signatures"][0]
            reviewer_id = client.get_group(reviewer_signature).members[0]
            p = openreview.tools.get_profile(client, reviewer_id)
            name = p.get_preferred_name()
            email = p.get_preferred_email()
            rating = meta_review.get(
                "overall_recommendation_after_area_chair_meeting", {}
            ).get("value")
            if rating is None:
                rating = meta_review["content"]["overall_recommendation"]["value"]
            d["meta_review"] = {
                "rating": rating,
                "name": name,
                "email": email,
            }
            break

        data.append(d)

    print(f"Found {len(data)} accepted papers.")
    return data


def save_papers(papers, out_file=OUT_FILE):
    with open(out_file, "w") as f:
        writer = csv.writer(f)
        header = ["Paper No", "Title", "Authors"]
        for i in range(1, 6):
            header.append(f"Review {i} Rating")
            header.append(f"Review {i} Name")
            header.append(f"Review {i} Email")
        header.extend(["Meta-Review Rating", "Meta-Review Name", "Meta-Review Email"])
        writer.writerow(header)
        for p in papers:
            row = [p["paper_no"], p["title"], ", ".join(p["authors"])]
            for i in range(1, 6):
                review = p.get(f"review_{i}")
                if review:
                    row.append(review["rating"])
                    row.append(review["name"])
                    row.append(review["email"])
                else:
                    row.extend(["", "", ""])
            meta_review = p.get("meta_review")
            if meta_review:
                row.append(meta_review["rating"])
                row.append(meta_review["name"])
                row.append(meta_review["email"])
            else:
                row.extend(["", "", ""])
            writer.writerow(row)
    print(f"Saved accepted papers to '{out_file}'")


def main():
    client = setup_client()
    papers = read_papers(client)
    save_papers(papers)


if __name__ == "__main__":
    main()
