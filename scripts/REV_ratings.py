from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
import os
import csv
import numpy as np

RATINGS_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "review_ratings.csv")
DECISIONS_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "review_decisions.csv")
SAVE_RATINGS_AS_INT = False # Ture: Save as int, False: Save as string

RATINGS = {
  1 : "Strong Reject",
    2 : "Reject",
    3 : "Weak Reject",
    4 : "Weak Accept",
    5 : "Accept",
    6 : "Strong Accept",
}
rating_to_int = {v: k for k, v in RATINGS.items()}

def get_ratings(client):
    data = {} # {paper_no : {forum, reviews, meta_review}

    # Get reviews and meta reviews.
    print("Reading reviews and meta reviews...")
    venue_group = client.get_group(VENUE)
    submission_name = venue_group.content["submission_name"]["value"]
    review_name = venue_group.content["review_name"]["value"]
    meta_review_name = venue_group.content["meta_review_name"]["value"]

    papers =  client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
    for paper in papers:
        paper_id = paper.forum
        paper_no = paper.number
        rev_invitation = f"{VENUE}/{submission_name}{paper_no}/-/{review_name}"
        meta_review_invitation = f"{VENUE}/{submission_name}{paper_no}/-/{meta_review_name}"
        paper_data = {
            "forum": paper_id,
            "reviews": [],
            "meta_review": {},
            "category": paper.content['category']['value'] 
            }
        for reply in paper.details["replies"]:
            if rev_invitation in reply["invitations"]:
                # Review
                paper_data["reviews"].append(reply["content"])
            elif meta_review_invitation in reply["invitations"]:
                # Meta review. Subsequent notes should merge/overwrite the previous ones. OpenReview MRs should be ordered by date.
                paper_data["meta_review"].update(reply["content"])
        data[paper_no] = paper_data
    print(f"Found {len(data)} papers.")
    return data
    

def save_ratings(ratings, output_file=RATINGS_OUTPUT_FILE):
    # Save to csv.
    with open(output_file, "w") as f:
        writer = csv.writer(f)
        header = ["Paper No", "Forum", "Review 1", "Review 2", "Review 3", "Review 4", "Review 5", "Meta Review", "AC Decision",  "AC Meeting Recommendation", "First Round Decision"] 
        writer.writerow(header)
        for no, data in sorted(ratings.items()):
            row = [no, data["forum"]]
            for i in range(5):
                if i < len(data["reviews"]):
                    rating = data["reviews"][i]["overall_recommendation"]["value"]
                    if SAVE_RATINGS_AS_INT:
                        row.append(rating if rating in RATINGS else rating_to_int[rating])
                    else:
                        row.append(RATINGS[rating] if rating in RATINGS else rating)
                else:
                    row.append("")
            if data["meta_review"]:
                # Save meta review rating.
                meta_review = data["meta_review"]
                rating = meta_review["overall_recommendation"]["value"]
                if SAVE_RATINGS_AS_INT:
                    row.append(rating if rating in RATINGS else rating_to_int[rating])
                else:
                    row.append(RATINGS[rating] if rating in RATINGS else rating)

                # Save second meta review decision.
                decision = meta_review.get("suggested_decision", {}).get("value")
                row.append(decision if decision else "")
                ac_meeting_decision = meta_review.get("overall_recommendation_after_area_chair_meeting", {}).get("value")
                row.append(ac_meeting_decision if ac_meeting_decision else "")
            else:
                row.append("", "", "")
            row.append(get_decision(data)[0])
            writer.writerow(row)
    print(f"Saved ratings to '{output_file}'.")

def save_first_decisions(ratings):
    # Save decisions to csv, such that it can be read by openreview.
    decisions ={}
    with open(DECISIONS_OUTPUT_FILE, "w") as f:
        writer = csv.writer(f)
        # Format: paper_no, decision, comment.
        for no, data in sorted(ratings.items()):
            decision, comment = get_decision(data)
            writer.writerow([no, decision, comment])
            if decision in decisions:
                decisions[decision] += 1
            else:
                decisions[decision] = 1
    print("Decisions:")
    for decision, count in decisions.items():
        print(f"- '{decision}': {count}")
    print(f"Saved first decisions to '{DECISIONS_OUTPUT_FILE}'.")


def get_decision(rating):
    # Get the final decision.
    max_rating = 0
    for review in rating["reviews"] + [rating["meta_review"]]:
        rating = review["overall_recommendation"]["value"]
        if rating in RATINGS:
            max_rating = max(max_rating, rating)
        else:
            max_rating = max(max_rating, rating_to_int[rating])
    if max_rating >= 4:
        return "Invited for Rebuttal", "Papers that received at least one recommendation of Weak Accept or higher from either the reviewers or the AC will be given the opportunity to submit a one-page rebuttal. The rebuttal will be considered in the final decision."
    return "Rejected", "Papers that did not receive at least one recommendation of Weak Accept or higher from either the reviewers or the AC are marked for rejection, as described in the overview of the RSS review process here: https://roboticsconference.org/reviewps/. While we understand this is an undesirable outcome, we hope the authors received constructive feedback from the first round of reviews and will find other ways to engage with RSS."

def main():
    client = setup_client()
    ratings = get_ratings(client)
    save_ratings(ratings)
    # save_first_decisions(ratings)

if __name__ == "__main__":
    main()
