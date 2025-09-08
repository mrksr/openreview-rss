from utils.setup_client import setup_client
from utils.paths import ROOT_DIR
from utils.messaging import Emails, deadline_reminder, signature
from REV_status import read_reviewer_status
from datetime import datetime

import os

# Where to read the reviewer data.
REV_STATUS_FILE = os.path.join(ROOT_DIR, "private", "Reviewers.csv")

"""
Read a list of reviewers and their status from a CSV file and send acceptance and registration reminders. 
IMPORTANT: Run this script after running "REV_status.py" to update the file.
"""


def send_registraton_reminders(reviewers, client):
    to_remind = [
        r["id"]
        for r in reviewers
        if r["status"] == "Accepted" and r["registration_completed"] == "Missing"
    ]
    deadline = datetime(2025, 2, 1)

    # Send reminders.
    if to_remind:
        mail = Emails()
        mail.subject = "[RSS25] Reminder: Reviewer Registration"
        mail.message = (
            "Dear {{fullname}},\n\nThank you for agreeing to serve as a Reviewer for RSS 2025! Our records indicate that you have not yet completed the reviewer registration. To do so, please go to 'Reviewer Console -> Tasks -> Reviewer Registration' (https://openreview.net/group?id=roboticsfoundation.org/RSS/2025/Conference/Reviewers#reviewer-tasks). \n\nNote that without a complete OpenReview account, we will not be able to assign you any papers.\n\n"
            + deadline_reminder(deadline)
            + "\n\n"
            + signature()
        )
        mail.recipients = to_remind
        mail.send(client)


def main():
    client = setup_client()
    reviewers = read_reviewer_status(REV_STATUS_FILE)
    send_registraton_reminders(reviewers, client)


if __name__ == "__main__":
    main()
