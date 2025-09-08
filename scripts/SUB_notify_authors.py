from utils.setup_client import setup_client
from utils.paths import VENUE
from utils.messaging import Emails

"""
Send first-round decision notifications to authors. This will notify all authors without further confirmation.
"""

NOTIFIY_PAPER_NOS = [] # If not empty, only notify these paper numbers. Otherwise notify all papers.
ONLY_WITH_META_REVIEW = False    # If true, skip papers that did not (yet) receive a meta review


def notify_review_release(client):
    papers =  client.get_all_notes(content={"venueid": f"{VENUE}/Submission"},  details="replies")
    venue_group = client.get_group(VENUE)
    submission_name = venue_group.content["submission_name"]["value"]
    meta_review_name = venue_group.content["meta_review_name"]["value"]
    without_meta_review = set()
    print(f"Found {len(papers)} papers.")
    num_notified = 0
    for note in papers:
        nr = note.number
        if NOTIFIY_PAPER_NOS and nr not in NOTIFIY_PAPER_NOS:
            continue
        if ONLY_WITH_META_REVIEW:
            has_meta_review = False
            meta_review_invitation = f"{VENUE}/{submission_name}{nr}/-/{meta_review_name}"
            for reply in note.details["replies"]:
                if meta_review_invitation in reply["invitations"]:
                    has_meta_review = True
                    break
            if not has_meta_review:
                without_meta_review.add(nr)
                continue

        id = note.id
        title = note.content["title"]["value"]
        authors = note.content["authorids"]["value"]
        
        mail = Emails()
        mail.subject = f"[RSS 2025] Reviews Released for Paper {nr}"
        mail.message = (
            "Dear {{fullname}},"
            + f"\n\nThanks to the efforts of our Reviewers, Emergency Reviewers, Area Chairs, and Senior Area Chairs, reviews and the first round of decisions for all active RSS 2025 submissions are now available. Please read the rest of this email carefully for instructions.\n\n**Reviews**\n\nYou can access the reviews and decision for your submission number {nr} titled \"{title}\" on OpenReview: https://openreview.net/forum?id={id}\n\nA small group of papers ended up with more than three reviews due to the Area Chair's extraordinary efforts in recruiting additional reviewers. If your paper is one of these, please note that it does not reflect any special status. \n\n**Rejected papers**\n\nPapers that did not receive at least one recommendation of Weak Accept or higher from either the reviewers or the AC are marked for rejection, as described in the overview of the RSS review process here: https://roboticsconference.org/reviewps/. While we understand this is an undesirable outcome, we hope the authors received constructive feedback from the first round of reviews and will find other ways to engage with RSS.\n\n**Rebuttal**\n\nPapers that received at least one recommendation of Weak Accept or higher from either the reviewers or the AC will be given the opportunity to submit a one-page rebuttal. The deadline to submit your rebuttal is March 24, 23:59 AoE. \n\nYou will be able to prepare a one-page PDF document using the template that can be found on the RSS website (https://roboticsconference.org/information/authorinfo/). The entire rebuttal must fit on one page, including any references. To upload your rebuttal, click the “Rebuttal” button on the OpenReview page of your paper, upload the PDF, and submit the form.\n\nRebuttals longer than one page will lead to a desk rejection decision for the corresponding paper. The same applies to rebuttals where the margins and formatting are deemed to have been altered from the template. The rebuttal must maintain anonymity. The rebuttal cannot include external links to videos, code repositories, etc.\n\nThe primary purpose of the rebuttal is to correct any factual inaccuracies in the reviews and provide further details or clarifications requested by the reviewers. You may include small additional experiments or analyzes, as well as any figures, graphs, or proofs needed to clarify your arguments. Please note that rebuttals will be evaluated primarily by the Area Chairs and, in most cases, will not be shared again with the reviewers. Additionally, please note that you will not have the opportunity to submit a revised version of your paper during the rebuttal period. However, if your paper is accepted, you will be able to incorporate the reviewers’ and Area Chair’s comments into the camera-ready version.\n\nBest regards,\n\nRSS 2025 Program Committee"
        )

        mail.recipients = authors
        mail.send(client, skip_verify=True)
        num_notified += 1
        print(f"{nr}")
    print(f"Sent notifications to {num_notified} papers.")
    if without_meta_review:
        print(f"Found {len(without_meta_review)} papers without a meta review:")
        print(f"- { ', '.join([str(x) for x in without_meta_review])}")


def main():
    client = setup_client()
    notify_review_release(client)


if __name__ == "__main__":
    main()
