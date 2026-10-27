import openreview
from datetime import datetime
from utils.paths import VENUE

"""
Tools to send emails via OpenReview-API.
"""


def is_email_address(mail):
    """
    Check whether a string is an email address.
    """
    return "@" in mail


def is_openreview_id(id):
    """
    Check whether a string is an OpenReview ID.
    Input: id (str)
    """
    return id.startswith("~") and "@" not in id


def deadline_reminder(deadline):
    """
    Create a string reminding of a deadline.
    Input: deadline (datetime)
    """
    now = datetime.now()
    days = (deadline.date() - now.date()).days
    if days < 0:
        return f"The deadline was {deadline.strftime('%b %d %Y')}. Please complete the task as soon as possible."
    days_msg = (
        f"{days} days from now" if days > 1 else ("tomorrow" if days == 1 else "today")
    )
    return f"The deadline is {deadline.strftime('%b %d %Y')}. This is {days_msg}."


def signature():
    """
    Create a signature for emails.
    """
    return "If you have any questions, please contact rss2027pc@gmail.com.\n\nThank you for your support!\n\nBest regards,\nRSS27 Program Chairs"


class Emails:
    def __init__(
        self,
        client,
        subject: str = None,
        message: str = None,
        recipients: list = None,
    ):
        self.client = client
        self.subject = subject
        self.message = message
        self.recipients = recipients
        # This is the meta invitation that allows sending emails. Signature needs to be of a program chair.
        self.invitation = f"{VENUE}/-/Edit"
        self.signature = f"{VENUE}/Program_Chairs"

    def send(self, skip_verify=False):
        # Verify setup correct.
        if not self.subject:
            print("No subject specified. Aborted.")
            return
        if not self.message:
            print("No message specified. Aborted.")
            return
        if not self.recipients:
            print("No recipients specified. Aborted.")
            return

        # Get user confirmation vefore sending.
        while not skip_verify:
            answer = input(
                f"Send email to {len(self.recipients)} recipients? (y/n) (l: list recipients, p: print message): "
            )
            if answer.lower() in ["l", "list"]:
                for recipient in self.recipients:
                    print(recipient)
                continue

            if answer.lower() in ["p", "print"]:
                print(
                    f"Subject: {self.subject[0] if isinstance(self.subject, list) else self.subject}"
                )
                print(
                    self.message[0] if isinstance(self.message, list) else self.message
                )
                continue

            if answer.lower() not in ["y", "yes"]:
                print("Sending mail aborted.")
                return
            else:
                break

        print("Sending...")
        self.client.post_message(
            subject=self.subject,
            recipients=self.recipients,
            message=self.message,
            invitation=self.invitation,
            signature=self.signature,
        )

        print(f"Emails sent to {len(self.recipients)} recipients.", end="\r")

    def resolve_recipients(self):
        resolved = set()
        for recipient in self.recipients:
            if is_email_address(recipient) or is_openreview_id(recipient):
                resolved.add(recipient)
            else:
                # Resolve group.
                try:
                    group = self.client.get_group(recipient)
                    resolved.update(group.members)
                except openreview.OpenReviewException as e:
                    print(f"Error resolving group '{recipient}': {e}")
        return list(resolved)


def test_deadline_reminder():
    deadline = datetime(2025, 1, 10)
    print(deadline_reminder(deadline))


if __name__ == "__main__":
    test_deadline_reminder()
