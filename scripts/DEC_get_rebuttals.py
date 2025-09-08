from utils.setup_client import setup_client
from utils.paths import VENUE
from datetime import datetime



# Conversion of OpenReview time stamps.
def time_from_stamp(stamp : int):
    return datetime.fromtimestamp(stamp / 1000)

def stamp_from_time(time : datetime):
    return int(time.timestamp() * 1000)

            
def get_papers_with_rebuttals(client):
    papers =  client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
    print(f"Found {len(papers)} papers.")

    # Get all rejected papers.
    rejected_paper_nos = set()
    with_rebuttal = set()
    for p in papers:
        for r in p.details["replies"]:
            if f"{VENUE}/Submission{p.number}/-/Decision" in r["invitations"]:
                # Decision.
                decision = r["content"]["decision"]["value"]
                if decision == "Rejected":
                    rejected_paper_nos.add(p.number)
            if f"{VENUE}/Submission{p.number}/-/Rebuttal" in r["invitations"]:
                with_rebuttal.add(p.number)

    active_papers = set([p.number for p in papers]) - rejected_paper_nos
    print(f"- {len(rejected_paper_nos)} rejected papers.")
    print(f"- {len(active_papers)} active papers.")
    print(f"  - {len(with_rebuttal)} with rebuttals.")
    without_rebuttal = active_papers - with_rebuttal
    print(f"  - {len(without_rebuttal)} without rebuttals.")
    if without_rebuttal and len(without_rebuttal) < 20:
        print("Papers without rebuttal:")
        for p in sorted(list(without_rebuttal)):
            print(f"- Paper {p} has no rebuttal.")
        

def main():
    client = setup_client()
    get_papers_with_rebuttals(client)


if __name__ == "__main__":
    main()
