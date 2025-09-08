from utils.setup_client import setup_client
from utils.paths import VENUE
from utils.messaging import Emails, deadline_reminder, signature

from datetime import datetime

from REV_progress import get_assignments


"""
Send emails to reviewers on OpenReview for the initial announcement and reminders periodically afterwards.
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


def notify_review_assignments(reviewers, client):
    mail = Emails()
    mail.subject = "[RSS25] Reviewer Assignment"
    mail.message = (
        "Dear {{fullname}},\n\nThank you for agreeing to serve as a Reviewer for RSS 2025! We are pleased to inform you that you have been assigned to review papers for the conference. Please go to 'Reviewer Console -> Tasks -> Reviewer Registration' (https://openreview.net/group?id=roboticsfoundation.org/RSS/2025/Conference/Reviewers#reviewer-tasks) to view your assigned papers and submit your reviews.\n\n"
        + signature()
    )
    mail.recipients = ["~Reviewer"]
    mail.send(client)


def main():
    client = setup_client()
    sac, ac, rev, papers = get_assignments(client)
    notify_review_assignments(rev, client)


if __name__ == "__main__":
    main()
