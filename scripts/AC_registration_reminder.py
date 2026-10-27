from utils.setup_client import setup_client
from utils.paths import ROOT_DIR
from utils.messaging import Emails, deadline_reminder, signature
from scripts.AC_status import read_ac_status
from datetime import datetime

import os

# Where to write the output.
AC_STATUS_FILE = os.path.join(ROOT_DIR, "private", "ACs.csv")

"""
Read a list of ACs and their status from a CSV file and send expertise selection reminders.
"""


def send_registration_invitation(acs, client):
    mail = Emails()
    mail.subject = "[RSS27] Senior Area Chair Registration Available"
    mail.message = (
        "Dear {{fullname}},\n\nThe Senior Area Chair Registration Task (https://openreview.net/group?id=roboticsfoundation.org/RSS/2027/Conference/Senior_Area_Chairs#senior-area-chair-tasks) is now available and due by January 10. To complete it, please\n\n1) Update your OpenReview profile. This information will be used to avoid conflicts of interests (CoI). You can find your OpenReview profile here: https://openreview.net/profile.\n\n2) Complete your Expertise Selection by importing your relevant papers to OpenReview. This information will be used to compute affinity scores and match papers to ACs and reviewers. You can find your expertise selection here: https://openreview.net/invitation?id=roboticsfoundation.org/RSS/2027/Conference/Senior_Area_Chairs/-/Expertise_Selection.\n\n3) Please select at least 3 RSS Keywords that describe your expertise in decreasing order of priority. These will be used to match papers to ACs and reviewers.\n\nThank you for serving as a Senior Area Chair for RSS 2027, we're excited to have you on board! "
        + signature()
    )
    mail.recipients = [ac["email"] for ac in acs if ac["role"] == "Senior_Area_Chairs"]
    mail.send(client)


def send_registration_reminder(acs, client):
    # TODO(lschmid): Needs updates for SACs.
    only_kw_missing = []
    registration_missing = []
    sac_registration_missing = []
    num_completed = 0
    for ac in acs:
        if ac["decision"] != "Accepted":
            continue
        if ac["role"] == "Senior_Area_Chairs":
            if not ac["registration_completed"]:
                sac_registration_missing.append(ac["email"])
            continue
        if ac["registration_completed"]:
            if ac["num_keywords"] >= 3:
                num_completed += 1
            else:
                only_kw_missing.append(ac["email"])
        else:
            registration_missing.append(ac["email"])

    print(f"============ Area Chair registration status ============")
    print(f"Completed: {num_completed}.")
    print(f"Only keywords missing: {len(only_kw_missing)}.")
    print(f"Registration missing: {len(registration_missing)}.")
    print(f"SAC registration missing: {len(sac_registration_missing)}.")
    deadline = datetime(2025, 1, 10)
    print(deadline_reminder(deadline))

    # Send reminders.
    if only_kw_missing:
        mail = Emails()
        mail.subject = "[RSS27] Please Select Area Chair Keywords"
        mail.message = (
            "Dear {{fullname}},\n\nOur records indicate that you have already registered but not yet selected 3 Keywords. To add them, you can go to 'Area Chair Console -> Area Chairs Registration -> Edit (Registration) -> Keyword Selection' (https://openreview.net/group?id=roboticsfoundation.org/RSS/2027/Conference/Area_Chairs#area-chair-tasks).\n\n"
            + deadline_reminder(deadline)
            + "\n\n"
            + signature()
        )
        mail.recipients = only_kw_missing
        mail.send(client)

    if registration_missing:
        mail = Emails()
        mail.subject = "[RSS27] Please Complete the Area Chair Registration"
        mail.message = (
            "Dear {{fullname}},\n\nOur records indicate that you have not yet completed your registration. To do so, please go to 'Area Chair Console -> Tasks -> Area Chairs Registration' (https://openreview.net/group?id=roboticsfoundation.org/RSS/2027/Conference/Area_Chairs#area-chair-tasks).\n\n"
            + deadline_reminder(deadline)
            + "\n\n"
            + signature()
        )
        mail.recipients = registration_missing
        mail.send(client)

    if sac_registration_missing:
        mail = Emails()
        mail.subject = "[RSS27] Please Complete the Senior Area Chair Registration"
        mail.message = (
            "Dear {{fullname}},\n\nOur records indicate that you have not yet completed your registration. To do so, please go to 'Senior Area Chair Console -> Tasks -> Senior Area Chairs Registration' (https://openreview.net/group?id=roboticsfoundation.org/RSS/2027/Conference/Senior_Area_Chairs#senior-area-chair-tasks).\n\n"
            + deadline_reminder(deadline)
            + "\n\n"
            + signature()
        )
        mail.recipients = sac_registration_missing
        mail.send(client)

    print(f"============ Area Chair registration reminder completed ============")


def main():
    client = setup_client()
    acs = read_ac_status(AC_STATUS_FILE)
    send_registration_reminder(acs, client)
    # send_registration_invitation(acs, client)


if __name__ == "__main__":
    main()
