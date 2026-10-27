from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
from utils.messaging import Emails
from utils.parse_notes import is_accepted
import os
import csv

"""
Send first-round decision notifications to authors. This will notify all authors without further confirmation.
"""

NOTIFIY_PAPER_NOS = (
    []
)  # If not empty, only notify these paper numbers. Otherwise notify all papers.
FINAL_DECISION_CSV = os.path.join(
    ROOT_DIR, "private", "RSS2025-Paper Ratings - ratings.csv"
)  # CSV file with final decisions.
DECISIONS_OUTPUT_PATH = os.path.join(
    ROOT_DIR, "private", "final_decisions.csv"
)  # Path to the folder with the decisions.
DECISION_MAPPING = {
    "Accept": "Accepted",
    "Reject": "Rejected",
    "Conditional Accept": "Conditionally Accepted",
}
CONDITIONAL_ACCEPT_PAPERS = []
REGISTRATIONS_CSV = os.path.join(
    ROOT_DIR, "private", "RSS2025 - Accepted Papers - papers.csv"
)


def read_decisions_from_csv():
    # Read decisions from CSV file.
    with open(FINAL_DECISION_CSV, "r") as f:
        reader = csv.DictReader(f)
        decisions = {
            int(row["Paper No"]): {
                "first_round": row["First Round Decision"],
                "final_decision": row["Final Decision after ACM"],
            }
            for row in reader
        }
    for d in decisions.values():
        d["final_decision"] = DECISION_MAPPING.get(
            d["final_decision"], d["final_decision"]
        )
    print(f"Found {len(decisions)} ratings.")
    return decisions


def save_decisions_to_csv(decisions):
    # Save decisions to CSV file.
    with open(DECISIONS_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        for paper_no, data in decisions.items():
            writer.writerow([paper_no, data["final_decision"]])
    print(f"Saved {len(decisions)} ratings to '{DECISIONS_OUTPUT_PATH}'.")


def analyze_decisions(decisions):
    dec = {}
    for data in decisions.values():
        if data["final_decision"] not in dec:
            dec[data["final_decision"]] = 0
        dec[data["final_decision"]] += 1
    print(f"Found {len(decisions)} ratings:")
    for k, v in dec.items():
        print(f"- {k}: {v}")


def notify_final_decision(client, decisions):
    # Read decisions from CSV file.
    mail = Emails(client)
    notes = {
        n.number: n
        for n in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    }
    for no, decision in decisions.items():
        if NOTIFIY_PAPER_NOS and no not in NOTIFIY_PAPER_NOS:
            continue
        if no not in notes:
            print(f"Paper {no} not found.")
            print(" ")
            continue
        if decision["first_round"] == "Rejected":
            # Rejected first round, already notified.
            continue
        note = notes[no]
        title = note.content["title"]["value"]
        authors = note.content["authorids"]["value"]
        url = f"https://openreview.net/forum?id={note.forum}"
        mail.subject = f"[RSS 2027] Decision for Paper {no}"

        if decision["final_decision"] == "Accepted":
            mail.message = (
                "Dear {{fullname}},\n\n"
                + f"""Thank you for submitting your paper titled “{title}” ({no}) to RSS 2027. We are delighted to inform you that your submission has been accepted. Congratulations! 

You can find the final reviews and meta review for your paper on the submission page in OpenReview at: {url}  

Your final camera-ready paper must be submitted via OpenReview by April 25, 2025 (23:59 AoE).  For the camera-ready version, please de-anonymise the paper, and you are welcome (and encouraged) to include external links to project websites and/or code repositories.

Note that for the paper to be included in the RSS 2027 proceedings, we require at least one author of an accepted paper to be registered for the full conference at the in-person rate before the camera-ready deadline of April 25, 2025.

CONFERENCE DECISION PROCESS:
We received 594 complete paper submissions, and from the very large number of high-quality papers we selected 163 papers for presentation, which represents an acceptance rate of roughly 27%. Each contributed RSS paper was reviewed by reviewers and an Area Chair. In some cases a secondary Area Chair also reviewed the paper. Final decisions about inclusion in the RSS 2027 program were made by the Program Committee during the in-person RSS Area Chair meeting on April 4-5, 2025. All decisions are final.

We look forward to seeing you in Los Angeles, California, USA at RSS 2027, for an exciting technical program and conference. Congratulations!

Best regards,

Luca Carlone
RSS 2027 Program Chair"""
            )
        elif decision["final_decision"] == "Rejected":
            mail.message = (
                "Dear {{fullname}},\n\n"
                + f"""Thank you for submitting your paper titled “{title}” ({no}) to RSS 2027. We regret to inform you that your submission was not accepted. You can find the final reviews and meta review for your paper on the submission page in OpenReview at: {url}

CONFERENCE DECISION PROCESS
We received 594 complete paper submissions, and from the very large number of high-quality papers we selected 163 papers for presentation, which represents an acceptance rate of roughly 27%. Each contributed RSS paper was reviewed by reviewers and an Area Chair. In some cases a secondary Area Chair also reviewed the paper. Final decisions about inclusion in the RSS 2027 program were made by the Program Committee on April 4-5, 2025. All decisions are final.

We understand this is disappointing, and we realize that it is an undesirable outcome after you put so much time and effort in a paper. I hope you will remain excited about your current work, and you will consider submitting to RSS in the future and participating in RSS 2027. 

Best regards,

Luca Carlone
RSS 2027 Program Chair"""
            )
        elif decision["final_decision"] == "Conditionally Accepted":
            mail.message = (
                "Dear {{fullname}},\n\n"
                + f"""Thank you for submitting your paper titled “{title}” ({no}) to RSS 2027. Your paper has been CONDITIONALLY accepted. You can find the final reviews and meta review for your paper on the submission page in OpenReview at: {url}  

Please carefully read the meta-review comments to address the remaining issues identified by the reviewer team. You must email your revision to rss2027pc@gmail.com by April 18, 2025 (23:59 AoE). Please email a pdf (and if requested video material) with your changes highlighted. Your paper will be reviewed by the PC to ensure the conditions for acceptance have been met.

Best regards,

Luca Carlone
RSS 2027 Program Chair"""
            )
        else:
            print(f"Paper {no} has unknown decision '{decision['final_decision']}'.")
            print(" ")
            continue

        mail.recipients = authors
        mail.send(skip_verify=False)
        print(f"Sent notification to paper {no} ({decision['final_decision']}).")


def notify_conditional_accept(client):
    # Special notification that
    mail = Emails(client)
    notes = {
        n.number: n
        for n in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    }
    for no in CONDITIONAL_ACCEPT_PAPERS:
        if no not in notes:
            print(f"Paper {no} not found.")
            print(" ")
            continue
        note = notes[no]
        title = note.content["title"]["value"]
        authors = note.content["authorids"]["value"]
        url = f"https://openreview.net/forum?id={note.forum}"
        mail.subject = f"[RSS 2027] Decision for Paper {no}"
        mail.message = (
            "Dear {{fullname}},\n\n"
            + f"""Thank you for submitting your paper titled “{title}” ({no}) to RSS 2027. We are delighted to inform you that your submission has been accepted. Congratulations! 

You can find the final reviews and meta review for your paper on the submission page in OpenReview at: {url}  

Your final camera-ready paper must be submitted via OpenReview by April 25, 2025 (23:59 AoE).  For the camera-ready version, please de-anonymise the paper, and you are welcome (and encouraged) to include external links to project websites and/or code repositories. If you need more time to prepare the camera-ready version, please email us at rss2027pc@gmail.com.

Note that for the paper to be included in the RSS 2027 proceedings, we require at least one author of an accepted paper to be registered for the full conference at the in-person rate before the camera-ready deadline of April 25, 2025.

CONFERENCE DECISION PROCESS:
We received 594 complete paper submissions, and from the very large number of high-quality papers we selected 163 papers for presentation, which represents an acceptance rate of roughly 27%. Each contributed RSS paper was reviewed by reviewers and an Area Chair. In some cases a secondary Area Chair also reviewed the paper. Final decisions about inclusion in the RSS 2027 program were made by the Program Committee during the in-person RSS Area Chair meeting on April 4-5, 2025. All decisions are final.

We look forward to seeing you in Los Angeles, California, USA at RSS 2027, for an exciting technical program and conference. Congratulations!

Best regards,

Luca Carlone
RSS 2027 Program Chair"""
        )
        mail.recipients = authors
        mail.send(skip_verify=False)
        print(f"Sent notification to paper {no}.")


def remind_registration(client):
    # Read missing registration from CSV file.
    missing_registrations = []
    with open(REGISTRATIONS_CSV, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row[0] != "Yes" and row[2] != "":
                missing_registrations.append(int(row[1]))
    print(f"Found {len(missing_registrations)} missing registrations.")

    mail = Emails(client)
    notes = {
        n.number: n
        for n in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    }
    for no in missing_registrations:
        if no not in notes:
            print(f"Paper {no} not found.")
            print(" ")
            continue
        note = notes[no]
        title = note.content["title"]["value"]
        authors = note.content["authorids"]["value"]
        mail.subject = f"[RSS 2027] No Authors Registered for Paper {no}"
        mail.message = (
            "Dear {{fullname}},\n\n"
            + f"Our records indicate that, currently, no authors of your paper {no} titled “{title}” are registered for RSS 2027. Note that for the paper to be included in the RSS 2027 proceedings, we require at least one author of an accepted paper to be registered for the full conference at the in-person rate. The deadline for registration was April 25, 2025 (23:59 AoE). Please register an author to present your paper AS SOON AS POSSIBLE, or we might be unable to include the paper in the conference proceedings.\n\nRegistration can be found at https://roboticsconference.org/attending/registration\n\nBest regards,\n\nLuca Carlone\nRSS 2027 Program Chair"
        )
        mail.recipients = authors
        mail.send(skip_verify=True)
    print(f"Sent registration reminder to {len(missing_registrations)} papers.")


def email_accepted_papers(client, message, subject):
    mail = Emails(client)
    mail.message = message
    num_emails = 0
    for note in client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    ):
        no = note.number
        if not is_accepted(note):
            continue

        num_emails += 1
        mail.subject = subject + f" for Paper {no}"
        mail.recipients = note.content["authorids"]["value"]
        mail.send(skip_verify=True)
        print(f"Sent notification to paper {no}.")
    print(f"Sent emails to {num_emails} papers.")


def send_presentation_instructions(client):
    with open(
        os.path.join(ROOT_DIR, "msg", "presentation_instructions.txt"), "r"
    ) as f:
        message = f.read()

    email_accepted_papers(
        client, message, "[RSS2027] [Important] Presentation Upload is Overdue"
    )


def notify_award_candidates(client):
    mail = Emails(client)
    mail.subject = "[RSS 2027] Best Paper Finalist at RSS 2027"
    num_emails = 0
    for note in client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    ):
        no = note.number
        num_emails += 1
        title = note.content["title"]["value"]
        mail.message = (
            "Dear {{fullname}},\n\n"
            + f"""We are reaching out with exciting news. The RSS 2027 award committee has finalized their selection of the best paper finalists at RSS 2027. Your paper No {no} titled “{title}”, has been selected as a best paper finalist!

You can find more details about the award category your paper has been selected for at the following link: https://roboticsconference.org/program/awards/

The final decision about the winner in each category will be made during the main conference and winners will be announced during the Award Ceremony on June 24, 2025. 

Being selected as an award finalist at RSS 2027 is not a small feat. Congratulations on this achievement and best of luck with the last step of the selection process!

All the best,
The RSS 2027 Organizing Committee"""
        )
        mail.recipients = note.content["authorids"]["value"]
        mail.recipients.append("~Luca_Carlone1")
        mail.send(skip_verify=False)
        print(f"Sent notification to paper {no}.")
    print(f"Sent emails to {num_emails} papers.")


def notify_presenters_instructions(client):
    print("Reading author data...")
    mail = Emails(client)
    mail.subject = "[RSS 2027] Presenters' Instructions"
    with open(os.path.join(ROOT_DIR, "msg", "presenters_instructions.md"), "r") as f:
        mail.message = f.read()
    num_papers = 0
    authors = set()
    for note in client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    ):
        if not is_accepted(note):
            continue
        num_papers += 1
        authors.update(note.content["authorids"]["value"])

    print(f"Found {len(authors)} authors for {num_papers} accepted papers.")
    mail.recipients = list(authors)
    mail.send(skip_verify=False)


def notify_final_abstract_update(client):
    mail = Emails(client)
    num_emails = 0
    for note in client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    ):
        no = note.number
        if not is_accepted(note):
            continue

        num_emails += 1
        url = f"https://openreview.net/forum?id={note.forum}"
        mail.subject = f"[RSS27] Action Required: Update Abstract in OpenReview for RSS 2027 Proceedings for Paper {no}"
        mail.message = f"""Dear RSS 2027 Authors,

As we prepare the official proceedings for RSS 2027, we’ve identified a mismatch between some of the abstracts in the camera-ready PDFs and the abstracts entered in OpenReview during the revision process. To ensure the proceedings reflect the correct version of your work, we ask that you **update your abstract in OpenReview to match the abstract in your camera-ready paper**. 

Even if the abstract appears correct on the RSS 2027 website, you must still update your abstract in OpenReview. Thank you for helping us ensure the accuracy of the RSS 2027 proceedings.

You can find the 'Final Abstract Update' edit option for your paper Number {no} here: {url}

The deadline for this update is **July 11, 2025** (23:59 AoE). 

Best regards,
RSS 2027 Program Committee
        """
        mail.recipients = note.content["authorids"]["value"]
        mail.send(skip_verify=False)
        print(f"Sent notification to paper {no}.")
    print(f"Sent emails to {num_emails} papers.")


def remind_final_abstract_update(client):
    mail = Emails(client)
    num_emails = 0
    for note in client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    ):
        no = note.number
        if not is_accepted(note):
            continue

        if "confirmation_that_abstract_is_correct" in note.content:
            continue

        num_emails += 1
        url = f"https://openreview.net/forum?id={note.forum}"
        mail.subject = f"[RSS27] Action Required: Update Abstract in OpenReview for RSS 2027 Proceedings for Paper {no}"
        mail.message = f"""Dear RSS 2027 Authors,

As we prepare the official proceedings for RSS 2027, we’ve identified a mismatch between some of the abstracts in the camera-ready PDFs and the abstracts entered in OpenReview during the revision process. To ensure the proceedings reflect the correct version of your work, we ask that you **update your abstract in OpenReview to match the abstract in your camera-ready paper**. 

Even if the abstract appears correct on the RSS 2027 website, **you must still confirm that your abstract is correct in OpenReview**. Thank you for helping us ensure the accuracy of the RSS 2027 proceedings.

You can find the 'Final Abstract Update' edit option for your paper Number {no} here: {url}

The deadline for this update was **July 11, 2025** (23:59 AoE). Please update your abstract as soon as possible.

Best regards,
RSS 2027 Program Committee
        """
        mail.recipients = note.content["authorids"]["value"]
        mail.send(skip_verify=True)
        print(f"Sent notification to paper {no}.")
    print(f"Sent emails to {num_emails} papers.")


def main():
    # decisions = read_decisions_from_csv()
    # save_decisions_to_csv(decisions)
    # analyze_decisions(decisions)
    client = setup_client()
    # notify_final_decision(client)
    # notify_conditional_accept(client)
    # remind_registration(client)
    # send_presentation_instructions(client)
    # notify_award_candidates(client)
    # notify_presenters_instructions(client)
    # notify_final_abstract_update(client)
    remind_final_abstract_update(client)


if __name__ == "__main__":
    main()
