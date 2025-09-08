from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
import os
import shutil
import openreview

OUTPUT_PATH = os.path.join(ROOT_DIR, "private", "submission_pdfs")


def get_submission_pdfs(client, lazy=True):
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    submissions = client.get_all_notes(invitation=f"{VENUE}/-/Submission")
    num_pdfs = 0
    print("Downloading submission PDFs...")
    for i, note in enumerate(submissions):
        if note.content.get("pdf", {}).get("value"):
            f = client.get_attachment(note.id, "pdf")
            outfile = os.path.join(OUTPUT_PATH, f"{note.number:03d}.pdf")
            print(
                f"Downloading pdf for {note.number} ({i}/{len(submissions)})", end="\r"
            )
            if os.path.exists(outfile) and lazy:
                continue
            with open(outfile, "wb") as op:
                op.write(f)
            num_pdfs += 1
    print(f"Downloaded {num_pdfs} submission PDFs.")


def copy_accepted_demo_pdfs(client, src_dir, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    # Only accepted papers.
    submissions = client.get_all_notes(
        invitation=f"{VENUE}/-/Submission", details="replies"
    )
    num_pdfs = 0
    print("Downloading submission PDFs...")
    for note in submissions:
        if note.content["category"]["value"] != "Demo":
            continue

        # Only accepted papers.
        decision = None
        for reply in note.details["replies"]:
            if f"{VENUE}/Submission{note.number}/-/Decision" in reply["invitations"]:
                decision = reply["content"]["decision"]["value"]
        if decision != "Accepted":
            continue

        # Copy the PDF file.
        src_file = os.path.join(src_dir, f"{note.number:03d}.pdf")
        dest_file = os.path.join(dest_dir, f"{note.number:03d}.pdf")
        if os.path.exists(src_file):
            shutil.copy(src_file, dest_file)
            num_pdfs += 1
            print(f"Copied pdf for {note.number} ({num_pdfs})")
        else:
            print(f"PDF for {note.number} not found.")
    print(f"Copied {num_pdfs} accepted demo PDFs.")


def download_accepted(client, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    num_pdfs = 0
    for note in client.get_all_notes(
        invitation=f"{VENUE}/-/Submission", details="replies"
    ):
        # Only accepted papers.
        decision = None
        for reply in note.details["replies"]:
            if f"{VENUE}/Submission{note.number}/-/Decision" in reply["invitations"]:
                decision = reply["content"]["decision"]["value"]
        if decision != "Accepted":
            continue

        # Download the PDF file.
        f = client.get_attachment(note.id, "pdf")
        outfile = os.path.join(dest_dir, f"{note.number:03d}.pdf")
        print(f"Downloading pdf for {note.number}.")
        with open(outfile, "wb") as op:
            op.write(f)
        num_pdfs += 1
    print(f"Downloaded {num_pdfs} award candidate PDFs.")


def download_award_candidateds(client, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    num_pdfs = 0
    for note in client.get_all_notes(
        invitation=f"{VENUE}/-/Submission", details="replies"
    ):
        # Only accepted papers.
        decision = None
        award_candidate = None
        for reply in note.details["replies"]:
            if f"{VENUE}/Submission{note.number}/-/Decision" in reply["invitations"]:
                decision = reply["content"]["decision"]["value"]
            if f"{VENUE}/Submission{note.number}/-/Meta_Review" in reply["invitations"]:
                if award_candidate is not None:
                    print(
                        f"Overwriting award candidate for paper {note.number}: {award_candidate} -> {reply['content']['award_candidate']['value']}"
                    )
                award_candidate = reply["content"]["award_candidate"]["value"]
        if decision != "Accepted" or award_candidate == "No":
            continue

        # Download the PDF file.
        f = client.get_attachment(note.id, "pdf")
        outfile = os.path.join(dest_dir, f"{note.number:03d}.pdf")
        print(f"Downloading pdf for {note.number}.")
        with open(outfile, "wb") as op:
            op.write(f)
        num_pdfs += 1
    print(f"Downloaded {num_pdfs} award candidate PDFs.")


def download_final_materials(client, dest_dir, lazy=True):
    os.makedirs(dest_dir, exist_ok=True)
    num_pdfs = 0
    num_supps = 0
    for note in client.get_all_notes(
        invitation=f"{VENUE}/-/Submission", details="replies"
    ):
        # Only accepted papers.
        decision = None
        for reply in note.details["replies"]:
            if f"{VENUE}/Submission{note.number}/-/Decision" in reply["invitations"]:
                decision = reply["content"]["decision"]["value"]
        if decision != "Accepted":
            continue

        # Download the final materials PDF file.
        pdf_file = os.path.join(dest_dir, f"{note.number:03d}.pdf")
        if not os.path.exists(pdf_file) or not lazy:
            print(f"Downloading pdf for {note.number}.")
            f = client.get_attachment(note.id, "pdf")
            with open(pdf_file, "wb") as op:
                op.write(f)
            num_pdfs += 1

        # Supplementary materials.
        supp_file = os.path.join(dest_dir, f"{note.number:03d}.zip")
        if not os.path.exists(supp_file) or not lazy:
            print(f"Downloading supplementary materials for {note.number}.")
            try:
                f = client.get_attachment(note.id, "supplementary_material")
            except openreview.OpenReviewException as e:
                continue
            with open(supp_file, "wb") as op:
                op.write(f)
            num_supps += 1
    print(f"Downloaded {num_pdfs} PDFs and {num_supps} supplementary materials.")


def main():
    client = setup_client()
    # get_submission_pdfs(client)
    # copy_accepted_demo_pdfs(client, os.path.join(OUTPUT_PATH, "Accept"), os.path.join(OUTPUT_PATH, "accepted_demos"))
    # download_award_candidateds(client, os.path.join(OUTPUT_PATH, "AwardCandidates"))
    # download_final_materials(client, os.path.join(OUTPUT_PATH, "FinalMaterials"))
    download_accepted(client, os.path.join(OUTPUT_PATH, "Accept"))


if __name__ == "__main__":
    main()
