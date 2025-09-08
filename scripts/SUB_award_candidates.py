from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
import os
import csv

"""
List of award candidates.
"""

OUTPUT_DIR = os.path.join(ROOT_DIR, "private", "submission_pdfs", "AwardCandidates")
REVIEW_FIELDS = ["summary_of_contribution","summary_of_strengths","summary_of_limitations", "feedback_for_improvement_and_clarification_requests", "nature_of_contribution", "overall_recommendation", "confidential_comments", "confidence"]
META_REVIEW_FIELDS = ["paper_summary", "paper_strengths", "major_weaknesses", "overall_recommendation", "requested_changes_and_specific_questions_for_authors", "nature_of_contribution", "award_candidate", "confidence", "confidential_comments", "overall_recommendation_after_area_chair_meeting", "justification_of_recommendation", "justification_of_final_recommendation" ]
MAX_REVIEWERS = 4

def format_field(s):
    return ' '.join(word.capitalize() for word in s.split('_'))
    

def get_award_candidates(client):
    # Get reviews and meta reviews.
    print("Reading reviews and meta reviews...")
    venue_group = client.get_group(VENUE)
    submission_name = venue_group.content["submission_name"]["value"]
    meta_review_name = venue_group.content["meta_review_name"]["value"]
    candidates = {} # {paper_no : award_recommendation}
    decisions = {} # {paper_no : decision}

    papers = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
    for paper in papers:
        paper_no = paper.number
        meta_review_invitation = f"{VENUE}/{submission_name}{paper_no}/-/{meta_review_name}"
        decision_invitation = f"{VENUE}/{submission_name}{paper_no}/-/Decision"
        for reply in paper.details["replies"]:
            if meta_review_invitation in reply["invitations"]:
                # Meta review
                candidates[paper_no] = reply["content"]["award_candidate"]["value"]
            if decision_invitation in reply["invitations"]:
                # Decision
                decisions[paper_no] = reply["content"]["decision"]["value"]
    print(f"Found {len(candidates)} papers.")
    return candidates, decisions

def download_award_reviews(client, award_candidates, decisions):
    # Get reviews and meta reviews.
    print("Reading reviews and meta reviews...")
    with open(os.path.join(OUTPUT_DIR, "reviews.csv"), "w",) as csvfile:
        writer = csv.writer(csvfile, delimiter='\\')
        header = ["Paper No"] + [format_field(x) for x in REVIEW_FIELDS] * MAX_REVIEWERS +[format_field(x) for x in META_REVIEW_FIELDS] 
        writer.writerow(header)

        papers = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
        num_saved = 0
        for paper in papers:
            paper_no = paper.number
            if award_candidates[paper_no] == "No" or decisions[paper_no] != 'Accepted':
                continue
            meta_review_invitation = f"{VENUE}/Submission{paper_no}/-/Meta_Review"
            review_invitation = f"{VENUE}/Submission{paper_no}/-/Official_Review"
            result = ""
            num_reviews = 0
            row = [paper_no]
            for reply in paper.details["replies"]:
                if review_invitation in reply["invitations"]:
                    result += f"# Review by {format_field(reply['signatures'][0].split('/')[-1])}:\n"
                    for field in REVIEW_FIELDS:
                        if field in reply["content"] and "value" in reply["content"][field]:
                            result += f"**{format_field(field)}:**\n"
                            result += f"{reply['content'][field]['value']}\n\n"
                        row.append(reply["content"].get(field, {}).get("value", ""))
                    num_reviews += 1
            while num_reviews < MAX_REVIEWERS:
                row.extend([""] * len(REVIEW_FIELDS))
                num_reviews += 1
            for reply in paper.details["replies"]:
                if meta_review_invitation in reply["invitations"]:
                    result += f"# Meta review by {format_field(reply['signatures'][0].split('/')[-1])}:\n"
                    for field in META_REVIEW_FIELDS:
                        if field in reply["content"] and "value" in reply["content"][field]:
                            result += f"**{format_field(field)}:**\n"
                            result += f"{reply['content'][field]['value']}\n\n"
                        row.append(reply["content"].get(field, {}).get("value", ""))

            with open(os.path.join(OUTPUT_DIR, f"{paper_no:03d}_reviews.md"), "w") as f:
                f.write(result)
            writer.writerow([str(x).replace('\n','') for x in row])
            num_saved += 1
    print(f"Saved {num_saved} reviews to '{OUTPUT_DIR}'.")

def print_award_candidates(candidates):
    yes = [p for p, v in candidates.items() if v == "Yes"]
    no = [p for p, v in candidates.items() if v == "No"]
    maybe = [p for p, v in candidates.items() if v == "Maybe"]
    print("Award candidates:")
    print(f"Yes: {len(yes)}")
    print(f"- {', '.join([str(p) for p in yes])}")
    print(f"Maybe: {len(maybe)}")
    print(f"- {', '.join([str(p) for p in maybe])}")
    print(f"No: {len(no)}")
    print(f"Total: {len(yes) + len(maybe) + len(no)}")


def main():
    client = setup_client()
    award_candidates, decisions = get_award_candidates(client)
    print_award_candidates(award_candidates)
    download_award_reviews(client, award_candidates, decisions)


if __name__ == "__main__":
    main()
