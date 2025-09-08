import openreview
from utils.paths import VENUE

"""
Class that allows and guards desk rejections.
NOTE: This will not automatically send emails to authors 
"""


class DeskReject:
    def __init__(self, client):
        self.client = client
        self._dr_name = client.get_group(VENUE).content["desk_rejection_name"]["value"]

    def reject_papers(self, paper_numbers, message):
        # Verify setup correct.
        if len(paper_numbers) == 0:
            print("No papers specified to desk reject.")
            return
        if not message:
            print("No message specified. Aborted.")
            return

        # Get user confirmation before sending.
        while True:
            answer = input(
                f"Desk reject {len(paper_numbers)} papers? (y/n) (l: list papers, p: print message): "
            )
            if answer.lower() in ["l", "list"]:
                print("Papers to be desk rejected:")
                submissions = self.client.get_all_notes(
                    invitation=f"{VENUE}/-/Submission"
                )
                for p in paper_numbers:
                    sub = next(x for x in submissions if x.number == p)
                    print(
                        f"- Submission {p}: \"{sub.content['title']['value']}\" by {', '.join(sub.content['authors']['value'])}"
                    )
                continue

            if answer.lower() in ["p", "print"]:
                print(f"Desk reject message: '{message}'")
                continue

            if answer.lower() not in ["y", "yes"]:
                print("Desk rejection aborted.")
                return
            else:
                break

        # Double confirm, DRs are serious.
        answer = input(
            f"Are you sure to desk reject {len(paper_numbers)} papers? (y/n): "
        )
        if answer.lower() not in ["y", "yes"]:
            print("Desk rejection aborted.")
            return

        print("Desk rejecting papers...")
        num_rejected = 0
        for paper_nr in paper_numbers:
            try:
                self.client.post_note_edit(
                    invitation=f"{VENUE}/Submission{paper_nr}/-/{self._dr_name}",
                    signatures=[f"{VENUE}/Program_Chairs"],
                    note=openreview.api.Note(
                        content={"desk_reject_comments": {"value": message}},
                    ),
                )
                num_rejected += 1
            except openreview.OpenReviewException as e:
                if e.args[0]["name"] == "TooManyError":
                    print(f"- Submission {paper_nr} is already desk rejected.")
                else:
                    print(f"- Submission {paper_nr} failed to desk reject: {e}")

        print(f"Desk rejected {num_rejected} papers.")
