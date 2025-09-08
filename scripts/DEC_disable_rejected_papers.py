from utils.setup_client import setup_client
from utils.paths import VENUE
from datetime import datetime



# Conversion of OpenReview time stamps.
def time_from_stamp(stamp : int):
    return datetime.fromtimestamp(stamp / 1000)

def stamp_from_time(time : datetime):
    return int(time.timestamp() * 1000)

            
def disable_meta_review_for_rejected_papers(client):
    papers =  client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}, details="replies")
    print(f"Found {len(papers)} papers.")

    # Get all rejected papers.
    rejected_paper_nos = set()
    for p in papers:
        for r in p.details["replies"]:
            if f"{VENUE}/Submission{p.number}/-/Decision" not in r["invitations"]:
                continue
            decision = r["content"]["decision"]["value"]
            if decision == "Rejected":
                rejected_paper_nos.add(p.number)
                break
    print(f"Found {len(rejected_paper_nos)} rejected papers.")

    # Disable the meta review invitation for rejected papers by setting the invitation expiration date in the past.
    for i, p in enumerate(sorted(rejected_paper_nos)):
        meta_review_invitation = f"{VENUE}/Submission{p}/-/Meta_Review"
        inv = client.get_invitation(meta_review_invitation)
        inv.expdate = stamp_from_time(datetime(2025, 1, 1))
        client.post_invitation_edit(f"{VENUE}/-/Edit", invitation=inv, signatures=[f"{VENUE}/Program_Chairs"])
        print(f"Disabled meta review for paper {p} ({i+1}/{len(rejected_paper_nos)}).")
    print(f"Disabled meta review for {len(rejected_paper_nos)} papers.")
        

def main():
    client = setup_client()
    disable_meta_review_for_rejected_papers(client)


if __name__ == "__main__":
    main()
