from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR

import csv
import os


# Where to write the output.
STATUS_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "AC_assignments.csv")

"""
Write a CSV of ACs assigned to papers.
"""


def write_ac_status(client, output_file=STATUS_OUTPUT_FILE):
    # Paper Nos.
    paper_nos = {
        p.id: p.number
        for p in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    }
    # Assignments.
    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Assignment", groupby="head"
    )
    acs = {}  # {paper_no: ac}
    for edge in edges:
        for val in edge["values"]:
            paper_id = val["head"]
            ac_id = val["tail"]
            if paper_id not in paper_nos:
                print(f"Warning: Paper ID {paper_id} not found in paper numbers.")
                continue
            acs[paper_nos[paper_id]] = ac_id

    print(f"Read {len(acs)} papers for {len(set(acs.values()))} ACs.")

    with open(output_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Paper No", "AC"])
        for paper_no, ac_id in acs.items():
            writer.writerow([paper_no, ac_id])

    print(f"Wrote Area Chairs assignments to {output_file}.")


def main():
    client = setup_client()
    write_ac_status(client)


if __name__ == "__main__":
    main()
