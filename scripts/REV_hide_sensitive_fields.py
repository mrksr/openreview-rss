from utils.setup_client import setup_client
from utils.paths import VENUE
import openreview


"""
Set the readers/nonreaders of sensitive fields in reviews and meta reviews if these are not there yet.
"""
# Who should be able to read the sensitive fields in reviews and meta reviews.
SENSITIVE_FIELDS = [
    "overall_recommendation",
    "confidential_comments",
    "confidence",
    "award_candidate",
    "justification_of_recommendation",
    "suggested_decision",
]

UPDATE_REVIEWS = False
UPDATE_META_REVIEWS = True

def process_reviews(client):
    # Get all reviews.
    venue_group = client.get_group(VENUE)
    submission_name = venue_group.content["submission_name"]["value"]
    review_name = venue_group.content["review_name"]["value"]
    meta_review_name = venue_group.content["meta_review_name"]["value"]

    papers =  client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
    num_updated = 0

    print(f"Updating {len(papers)} papers...")
    for i, paper in enumerate(papers):
        paper_no = paper.number
        rev_invitation = f"{VENUE}/{submission_name}{paper_no}/-/{review_name}"
        meta_review_invitation = f"{VENUE}/{submission_name}{paper_no}/-/{meta_review_name}"
        to_update = []
        if UPDATE_REVIEWS:
            to_update.append(rev_invitation)
        if UPDATE_META_REVIEWS:
            to_update.append(meta_review_invitation)

        paper_updated = False
        for reply in paper.details["replies"]:
            if not any([(inv in reply["invitations"]) for inv in to_update ]):
                continue
            # if reply["id"] != "LcGeprxN4D":
            #     continue
            content_before = reply["content"].copy()
            update_content_readers(reply, paper_no)

            # Check if the content has changed.
            if reply["content"] == content_before:
                continue

            # Post the updated review.
            client.post_note_edit(
                invitation = f'{VENUE}/-/Edit',
                readers = [f'{VENUE}'],
                writers = [f'{VENUE}'],
                signatures = [f'{VENUE}'],
                note = openreview.api.Note(
                    id = reply["id"],
                    content = reply["content"]
                )
            )
            num_updated += 1
            paper_updated = True
        if paper_updated:
            print(f"Updated paper {paper_no} ({i+1}/{len(papers)}).")
    print(f"Updated {num_updated} reviews/meta reviews.")
    


def update_content_readers(reply, paper_no):
    new_readers = [r for r in set([
        f"{VENUE}/Program_Chairs",
        f"{VENUE}/Submission{paper_no}/Senior_Area_Chairs",
        f"{VENUE}/Submission{paper_no}/Area_Chairs",
        reply["signatures"][0]])
    ]
    for k,v in reply["content"].items():
        if k in SENSITIVE_FIELDS:
            v["readers"] = new_readers

def main():
    client = setup_client(test_venue=False)
    process_reviews(client)


if __name__ == "__main__":
    main()
