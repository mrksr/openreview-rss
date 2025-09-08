from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
import os
import csv

ASSIGNMENT_OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "second_meta_review_progress.csv")


def get_decisions(client):
    data = {} # {paper_no : first_round_decision, suggested_decision, paper_id}
    papers =  client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
    for paper in papers:
        paper_no = paper.number
        inv = f"{VENUE}/Submission{paper_no}/-/"
        paper_data = {"paper_id": paper.forum}
        for reply in paper.details["replies"]:
            if f"{inv}Meta_Review" in reply["invitations"]:
                # Meta review
                decision = reply["content"].get("suggested_decision", {}).get("value")
                if decision:
                    paper_data["suggested_decision"] = decision
            if f"{inv}Decision" in reply["invitations"]:
                # First round decision
                paper_data["first_round_decision"] = reply["content"]["decision"]["value"]
        data[paper_no] = paper_data
    print(f"Found {len(data)} papers.")
    return data


def get_ac_assignments(client, decisions):
    # AC Assignments.
    ac_assignments = {}
    paper_id_to_no = {v["paper_id"]: k for k, v in decisions.items()}

    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Assignment", groupby="head"
    )
    for edge in edges:
        for val in edge["values"]:
            paper_id = paper_id_to_no.get(val["head"],None)
            if not paper_id:
                continue
            ac_id = val["tail"]
            ac_assignments[paper_id] = ac_id
    print(f"Found {len(ac_assignments)} AC assignments.")
    return ac_assignments

def print_ac_progress(decisions, acs):
    # For each AC get the number of completed and pending suggested decisions.
    ac_data = {} # ac_id : completed, pending.
    total_completed = 0
    total_pending = 0
    for paper_no, data in decisions.items():
        if data["first_round_decision"] == "Rejected":
            continue
        ac_id = acs[paper_no]
        if ac_id not in ac_data:
            ac_data[ac_id] = {"completed": set(), "pending": set()}
        if "suggested_decision" in data:
            ac_data[ac_id]["completed"].add(paper_no)
        else:
            ac_data[ac_id]["pending"].add(paper_no)
    # Sort by number of completed and pending decisions.
    ac_data = sorted(ac_data.items(), key=lambda x: len(x[1]["pending"]), reverse=True)

    # Print the results.
    print("AC ID".ljust(27) + "Miss\tDone\tTotal\tPending Paper Nos")
    for ac_id, data in ac_data:
        pending = len(data["pending"])
        completed = len(data["completed"])
        total_pending += pending
        total_completed += completed
        missing = ', '.join(sorted([str(x) for x in data['pending']]))
        print(f"{ac_id}".ljust(27) + f"{pending}\t{completed}\t{pending + completed}\t{'(' + missing + ')' if pending > 0 else ''}")
    print(f"Total".ljust(27)+f"{total_pending}\t{total_completed}\t{total_pending + total_completed}")

def save_ac_progress(decisions, acs):
    # Sort by AC and paper No.
    ac_data = {}  # {ac: [paper_id1, suggested_decision1, ...)]} 
    for paper_no, data in decisions.items():
        if data["first_round_decision"] == "Rejected":
            continue
        ac_id = acs[paper_no]
        if ac_id not in ac_data:
            ac_data[ac_id] = []
        if "suggested_decision" in data :
            ac_data[ac_id].extend([paper_no, data["suggested_decision"]])
        else:
            ac_data[ac_id].extend([paper_no, "Missing"])

    # Save to csv.
    with open(ASSIGNMENT_OUTPUT_FILE, "w") as f:
        writer = csv.writer(f)
        header = ["AC"] + ["Paper", "Decision"] * 12
        writer.writerow(header)
        for ac_id, papers in ac_data.items():
            row = [ac_id] + papers + [""] * (12 - len(papers))
            writer.writerow(row)

    print(f"Saved data to '{ASSIGNMENT_OUTPUT_FILE}'.")



def main():
    client = setup_client()
    decisions = get_decisions(client)
    acs = get_ac_assignments(client, decisions)
    print_ac_progress(decisions, acs)
    save_ac_progress(decisions, acs)

if __name__ == "__main__":
    main()
