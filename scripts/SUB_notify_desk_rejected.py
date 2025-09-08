from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
import pickle
import os
from utils.messaging import Emails
from utils.desk_reject import DeskReject
import csv


"""
Send a nicer email to all authors of desk rejected papers.
"""

SAVE_DR_PAPERS_PATH = os.path.join(ROOT_DIR, "private", "desk_rejected_papers.p")

PAPERS_TO_DR_SHEET = os.path.join(
    ROOT_DIR,
    "private",
    "2025-01-24-initialPaperAssessmentAndDeskRejections-PRonly - desk rejections.csv",
)


def send_dr_notification(client):
    notes = client.get_all_notes(
        invitation=f"{VENUE}/-/Desk_Rejected_Submission", details="directReplies"
    )
    print(f"Found {len(notes)} desk rejected papers.")
    notified_papers = set()
    if os.path.exists(SAVE_DR_PAPERS_PATH):
        notified_papers = pickle.load(open(SAVE_DR_PAPERS_PATH, "rb"))
        print(f"Loaded {len(notified_papers)} notified papers.")
    num_notified = 0
    for note in notes:
        nr = note.number
        if nr in notified_papers:
            continue
        authors = note.content["authorids"]["value"]
        title = note.content["title"]["value"]
        reason = None
        for details in note.details["directReplies"]:
            if "desk_reject_comments" in details["content"]:
                reason = details["content"]["desk_reject_comments"]["value"]
                break

        notified_papers.add(nr)
        mail = Emails()
        mail.subject = f"[RSS 2025] Submission {nr} Decision"
        mail.message = (
            "Dear {{fullname}},"
            + f'\n\nWe regret to inform you that your submission {nr} "{title}" has been desk rejected, and will not be considered for review at RSS 2025.\n\nReason: {reason}\n\nThe desk rejection decision follows the RSS guidelines, reported on the RSS website: https://roboticsconference.org/reviewps/\n\nWhile we understand this is disappointing news, we hope this will not discourage you from pursuing your research and hope you will still consider submitting to RSS and participating in RSS 2025.\n\nSincerely,\nRSS 2025 Program Chair'
        )

        mail.recipients = authors
        mail.send(client, skip_verify=False)
        num_notified += 1
    print(f"Sent notifications to {num_notified} desk rejected papers.")
    pickle.dump(notified_papers, open(SAVE_DR_PAPERS_PATH, "wb"))
    print(f"Saved notified paper nrs to '{SAVE_DR_PAPERS_PATH}'.")


def read_dr_list(file):
    # Read the desk rejection list.
    papers = {}  # {nr: title, reason}
    skip_rows = 1
    with open(PAPERS_TO_DR_SHEET, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if skip_rows > 0:
                skip_rows -= 1
                continue
            if len(row[0]) == 0:
                break
            nr, title = row[0].split(" - ")
            papers[int(nr)] = {"title": title, "reason": row[1].strip()}
    return papers


def desk_reject_by_list(client):
    papers = read_dr_list(PAPERS_TO_DR_SHEET)
    print(f"Desk rejecting {len(papers)} papers.")
    dr = DeskReject(client)
    for nr, info in papers.items():
        # print(f"Desk rejecting {nr}: {info['title']}")
        dr.reject_papers(nr, info["reason"])
    print("Done.")


def main():
    client = setup_client()
    send_dr_notification(client)


if __name__ == "__main__":
    main()
