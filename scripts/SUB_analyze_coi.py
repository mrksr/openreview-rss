from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
import os
import csv
import hashlib



"""
For all Submissions check how many CoI they have with ACs and SACs and how many co-author conflicts they have.
"""

def main(client, outfile=os.path.join(ROOT_DIR, "private", "paper_conflicts.csv")):
    # Get all papers.
    notes = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    paper_id_to_no = {p.id: p.number for p in notes }
    
    # Conflicts.
    num_conflicts = {p: 0 for p in paper_id_to_no.values()}
    edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Conflict", groupby="head") +  client.get_grouped_edges(f"{VENUE}/Senior_Area_Chairs/-/Conflict", groupby="head")
    for edge in edges:
        for val in edge["values"]:
            paper_no = paper_id_to_no.get(val["head"],None)
            if paper_no:
                num_conflicts[paper_no] += 1

    # AC Authored.
    acs = set(client.get_group(f"{VENUE}/Senior_Area_Chairs").members + client.get_group(f"{VENUE}/Area_Chairs").members)
    ac_authored = {sub.number:set(sub.content["authorids"]["value"]) & acs for sub in notes}

    # Save to csv.
    with open(outfile, "w") as f:
        writer = csv.writer(f)
        header = ["Paper No", "Num OpenReview Conflicts", "AC Authored", "Anonymous ID"]
        writer.writerow(header)
        for no, data in sorted(num_conflicts.items()):
            anon_id = no
            if ac_authored[no]:
                # Generate a hash for the paper number to anonymize it.
                # This is a simple way to anonymize the paper number, but not secure.
                # For a more secure approach, consider using a cryptographic hash function.
                h = hashlib.sha3_512() 
                h.update(str(no).encode())
                anon_id = f"An{h.hexdigest()[:6]}"
            writer.writerow([no, data, ";".join(ac_authored[no]), anon_id])
    print(f"Saved conflicts for {len(num_conflicts)} papers to '{outfile}'.")


if __name__ == "__main__":
    client = setup_client()
    main(client)