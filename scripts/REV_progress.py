from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
from utils.messaging import Emails, deadline_reminder
from datetime import datetime
import os
import csv

ASSIGNMENT_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "review_progress.csv")


def get_assignments(client):
    # Get all live papers.
    papers = {
        p.id: p.number
        for p in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    }
    print(f"Read {len(papers)} papers.")

    # SAC Data
    sac = {}  # paper_id: sac_id
    edges = client.get_grouped_edges(
        f"{VENUE}/Senior_Area_Chairs/-/Assignment", groupby="head"
    )
    for edge in edges:
        val = edge["values"][0]
        paper_id = val["head"]
        if paper_id not in papers:
            continue
        sac_id = val["tail"]
        sac[paper_id] = sac_id
    print(f"Read {len(sac)} SAC assignments.")

    # AC Data
    ac = {}  # paper_id: ac_id
    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Assignment", groupby="head"
    )
    for edge in edges:
        val = edge["values"][0]
        paper_id = val["head"]
        if paper_id not in papers:
            continue
        ac_id = val["tail"]
        ac[paper_id] = ac_id
    print(f"Read {len(ac)} AC assignments.")

    # Reviewer Data
    rev = {}  # paper_id: reviewer_ids
    edges = client.get_grouped_edges(f"{VENUE}/Reviewers/-/Assignment", groupby="head")
    num_edges = 0
    for edge in edges:
        for val in edge["values"]:
            paper_id = val["head"]
            if paper_id not in papers:
                continue
            rev_id = val["tail"]
            if paper_id not in rev:
                rev[paper_id] = []
            rev[paper_id].append(rev_id)
            num_edges += 1
    print(f"Read {num_edges} reviewer assignments.")
    return sac, ac, rev, papers


def get_completed_reviews(client):
    venue_group = client.get_group(VENUE)
    submission_name = venue_group.content["submission_name"]["value"]
    review_name = venue_group.content["review_name"]["value"]

    submissions = client.get_all_notes(
        invitation=f"{VENUE}/-/{submission_name}", details="replies"
    )
    reviews = {s.id: set() for s in submissions}  # paper_id: submitted_reviewer_ids
    print("Reading completed reviews...")
    for s in submissions:
        rev_invitation = f"{VENUE}/{submission_name}{s.number}/-/{review_name}"
        for reply in s.details["replies"]:
            if rev_invitation not in reply["invitations"]:
                continue
            reviewer_signature = reply["signatures"][0]
            reviewer_id = client.get_group(reviewer_signature).members[0]
            reviews[s.id].add(reviewer_id)

    return reviews


def print_stats(sacs, acs, rev, papers):
    # All papers with less than 3 reviewers.
    num_missing = 0
    acs_missing = {}
    sacs_missing = {}
    for id, no in papers.items():
        num_rev = len(rev.get(id, []))
        if num_rev < 3:
            ac = acs.get(id, "None")
            sac = sacs.get(id, "None")
            num_missing += 1
            if ac not in acs_missing:
                acs_missing[ac] = set()
            acs_missing[ac].add(no)
    print(f"Papers with less than 3 assigned reviewers: {num_missing}")
    if acs_missing:
        print("Num papers missing by AC:")
        for ac, papers in sorted(
            acs_missing.items(), key=lambda x: len(x[1]), reverse=True
        ):
            print(
                f"  - {ac} misses {len(papers)} papers ({', '.join([str(p) for p in papers])})"
            )


def save_assignments(sac, ac, rev, papers, reviews):
    # Sort by AC and paper No.
    data = {}  # {ac: {no: num_rev}} # assigned reviewers
    completed_data = {}  # {ac: {no: num_rev}} # completed reviews
    for id, no in papers.items():
        num_rev = len(rev.get(id, []))
        ac_id = ac.get(id, "None")
        if ac_id not in data:
            data[ac_id] = {no: num_rev}
        else:
            data[ac_id][no] = num_rev

        # Completed reviews.
        num_completed = len(reviews.get(id, []))
        if ac_id not in completed_data:
            completed_data[ac_id] = {no: num_completed}
        else:
            completed_data[ac_id][no] = num_completed

    # Save to csv.
    with open(ASSIGNMENT_OUTPUT_FILE, "w") as f:
        writer = csv.writer(f)
        header = ["AC"] + ["Paper No", "Num Rev"] * 12
        writer.writerow(header)
        for ac_id, papers in sorted(data.items()):
            row = [ac_id]
            for no, num_rev in sorted(papers.items()):
                row.extend([no, num_rev])
            writer.writerow(row)
        writer.writerow(header)
        for ac_id, papers in sorted(completed_data.items()):
            row = [ac_id]
            for no, num_rev in sorted(papers.items()):
                row.extend([no, num_rev])
            writer.writerow(row)
    print(f"Saved data to '{ASSIGNMENT_OUTPUT_FILE}'.")


def notify_review_assignments(reviewers, client):
    recipients = set()
    for rev_ids in reviewers.values():
        recipients.update(rev_ids)
    print(f"Found total reviewers: {len(recipients)}")
    mail = Emails()
    mail.subject = "[RSS27] Reviewer Assignment"
    mail.message = "Dear {{fullname}},\n\nThank you for agreeing to serve as a Reviewer for RSS 2027! We are pleased to inform you that you have been assigned to review papers for the conference. Please go to the OpenReview Reviewer Console (https://openreview.net/group?id=roboticsfoundation.org/RSS/2025/Conference/Reviewers) to view your assigned papers and submit your reviews.\n\nThe (hard) deadline to submit your reviews is March 10, 2025. This is 27 days from now.\n\nThe quality and rigor of the review process are key ingredients in making RSS a unique, prestigious, and engaging conference. Therefore, we encourage you to write deep, constructive, and empathetic reviews, and to help us identify excellent papers as part of the RSS 2027 program.\n\nImportant Information: The authors will only have one week to prepare a one page rebuttal after receiving the reviews. The rebuttal will be assessed by the Area Chairs, and will not go back to the reviewers. Therefore, when preparing your review, please include a clear list of strengths and weaknesses, as well as clear recommendations about improvements you expect the authors to implement for the paper to be acceptable. Moreover, please keep in mind that the authors will have limited time to implement these recommendations before the camera ready paper is due. For instance, adding multiple baselines or multiple experiments might be incompatible with the available time. You can find more information about the RSS review process here: https://roboticsconference.org/reviewps/\n\nIf you have any questions, please contact rss2027pc@gmail.com.\n\nThank you for your support!\n\nBest regards,\nThe RSS 2027 Program Chair"

    print(mail.message)
    mail.recipients = list(recipients)
    mail.send(client)


def review_reminders(reviewers, reviews, client, check_for_authors=False):
    assigned_reviews = {}  # rev_id: paper_ids
    for paper_id, rev_ids in reviewers.items():
        for rev_id in rev_ids:
            if rev_id not in assigned_reviews:
                assigned_reviews[rev_id] = set()
            assigned_reviews[rev_id].add(paper_id)

    completed_reviews = {}  # rev_id: paper_ids
    for paper_id, rev_ids in reviews.items():
        for rev_id in rev_ids:
            if rev_id not in completed_reviews:
                completed_reviews[rev_id] = set()
            completed_reviews[rev_id].add(paper_id)

    reviewers_done = [
        rev
        for rev in assigned_reviews
        if len(assigned_reviews[rev]) == len(completed_reviews.get(rev, []))
    ]
    reviews_not_done = {
        rev: assigned_reviews[rev] - completed_reviews.get(rev, set())
        for rev in assigned_reviews
    }

    reviewers_not_done = [
        rev for rev, reviews in reviews_not_done.items() if len(reviews) > 0
    ]

    reviewers_started = [
        rev
        for rev, reviews in reviews_not_done.items()
        if len(reviews) < len(assigned_reviews.get(rev, [])) and len(reviews) > 0
    ]
    reviewers_not_started = {
        rev: reviews
        for rev, reviews in reviews_not_done.items()
        if len(reviews) == len(assigned_reviews.get(rev, []))
    }

    print(f"Reviewers done: {len(reviewers_done)}")
    print(f"Reviewers not done: {len(reviewers_not_done)}")
    print(f"- Reviewers started: {len(reviewers_started)}")
    print(f"- Reviewers not started: {len(reviewers_not_started)}")
    for i in range(1, 5):
        print(
            f"  - {i} papers: {len([rev for rev, reviews in reviewers_not_started.items() if len(reviews) == i])}"
        )

    # Optional: Check how many reviewers are also authors.
    if check_for_authors:
        authors = get_authors(client)
        reviewer_authors = set(reviewers_not_started) & authors
        if reviewer_authors:
            print(
                f"Found {len(reviewer_authors)} not started reviewers that are also authors."
            )

    # Send reminders to reviewers.
    mail = Emails()
    mail.subject = "[RSS27] Review Reminder: Hard Deadline Today"
    deadline = datetime(2025, 3, 10)
    mail.message = (
        "Dear {{fullname}},\n\nThank you for agreeing to serve as a Reviewer for RSS 2027! Our records indicate that you have not yet completed all reviews. Please go to the OpenReview Reviewer Console (https://openreview.net/group?id=roboticsfoundation.org/RSS/2025/Conference/Reviewers) to view your assigned papers and submit your reviews.\n\n"
        + deadline_reminder(deadline)
        + "\n\nThe quality and rigor of the review process are key ingredients in making RSS a unique, prestigious, and engaging conference. Therefore, we encourage you to write deep, constructive, and empathetic reviews, and to help us identify excellent papers as part of the RSS 2027 program.\n\nImportant Information: The authors will only have one week to prepare a one page rebuttal after receiving the reviews. The rebuttal will be assessed by the Area Chairs, and will not go back to the reviewers. Therefore, when preparing your review, please include a clear list of strengths and weaknesses, as well as clear recommendations about improvements you expect the authors to implement for the paper to be acceptable. Moreover, please keep in mind that the authors will have limited time to implement these recommendations before the camera ready paper is due. For instance, adding multiple baselines or multiple experiments might be incompatible with the available time. You can find more information about the RSS review process here: https://roboticsconference.org/reviewps/\n\nIf you have any questions, please contact rss2027pc@gmail.com.\n\nThank you for your support!\n\nBest regards,\nThe RSS 2027 Program Chair"
    )
    mail.recipients = reviewers_not_done
    mail.send(client)


def get_authors(client):
    authors = set()
    print("Loading authors...")
    for author_group in client.get_group(f"{VENUE}/Authors").members:
        authors.update(client.get_group(author_group).members)
    print(f"Found {len(authors)} authors.")
    return authors


def main():
    client = setup_client()
    sac, ac, rev, papers = get_assignments(client)
    print_stats(sac, ac, rev, papers)
    # reviews = get_completed_reviews(client)
    # save_assignments(sac, ac, rev, papers, reviews)

    # notify_review_assignments(rev, client)

    # review_reminders(rev, reviews, client,  check_for_authors=True)


if __name__ == "__main__":
    main()
