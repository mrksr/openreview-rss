from utils.setup_client import setup_client
from utils.profiles import ProfileMatcher
from utils.paths import VENUE, ROOT_DIR
from utils.keyword_similarity import keyword_similarity
from AC_status import read_ac_status
import openreview
import os
import csv

# Where to store the matching output.
OUTPUT_FILE = os.path.join(ROOT_DIR, "private", "SAC_Matching.csv")

# Which matching configuration to read.
SELECTED_AC_MATCHING = "AC_Matching_Final"

# Which matching to write the configuration to.
OUTPUT_AC_MATCHING = "AC_Matching_Deploy"

# Assignment sheet to read and deploy.
ASSIGNMENT_SHEET = os.path.join(
    ROOT_DIR, "private", "RSS2025 - SAC Matching - Matching.csv"
)


def set_max_papers(client, ac_id, max_papers):
    # Set individual max num papers for Area Chairs
    client.post_edge(
        openreview.api.Edge(
            invitation=f"{VENUE}/Area_Chairs/-/Custom_Max_Papers",
            head=f"{VENUE}/Area_Chairs",
            tail=ac_id,
            signatures=[f"{VENUE}/Program_Chairs"],
            weight=max_papers,
        )
    )


def get_papers(client):
    # Get all active submissions.
    papers = {}  # id: number, authors, title, keywords, category
    for paper in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}):
        papers[paper.id] = {
            "number": paper.number,
            "authors": paper.content["authors"]["value"],
            "authors_ids": paper.content["authorids"]["value"],
            "title": paper.content["title"]["value"],
            "keywords": paper.content["keywords"]["value"],
            "category": paper.content["category"]["value"],
        }
    print(f"Read {len(papers)} active papers.")
    return papers


def get_sac_assignments(client):
    edges = client.get_grouped_edges(
        f"{VENUE}/Senior_Area_Chairs/-/Assignment", groupby="head"
    )

    assignments = {}  # id: sac
    for edge in edges:
        data = edge["values"][0]
        sac_id = data["tail"]
        assignments[data["head"]] = sac_id.split("_")[0][1:]  # Get name
    print(f"Read {len(assignments)} SAC assignments.")
    return assignments


def get_ac_data(client, papers):
    ac_ids = set()
    ac_data = {
        paper_id: {
            "affinity": {},
            "conflicts": set(),
            "bids": {},
            "assignment": None,
        }
        for paper_id in papers
    }

    # Get all AC data for each submission.
    print("Getting AC data from OpenReview...")

    # Affinity scores. This should exhaust all papers and ACs.
    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Affinity_Score", groupby="head"
    )
    for edge in edges:
        for val in edge["values"]:
            paper_id = val["head"]
            ac_id = val["tail"]
            ac_data[paper_id]["affinity"][ac_id] = val["weight"]
            ac_ids.add(ac_id)

    # Conflicts.
    edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Conflict", groupby="head")
    for edge in edges:
        for val in edge["values"]:
            paper_id = val["head"]
            ac_id = val["tail"]
            ac_data[paper_id]["conflicts"].add(ac_id)
            ac_ids.add(ac_id)

    # Bids.
    edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Bid", groupby="head")
    bid_scores = {"Very Low": 1, "Low": 2, "Neutral": 3, "High": 4, "Very High": 5}
    for edge in edges:
        for val in edge["values"]:
            paper_id = val["head"]
            if paper_id not in ac_data:
                continue  # Ignore withdrawn or DR'd papers
            ac_id = val["tail"]
            ac_data[paper_id]["bids"][ac_id] = bid_scores[val["label"]]
            ac_ids.add(ac_id)

    # Assignments.
    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Proposed_Assignment", groupby="head"
    )
    for edge in edges:
        for val in edge["values"]:
            if val["label"] != SELECTED_AC_MATCHING:
                continue
            paper_id = val["head"]
            ac_id = val["tail"]
            print(f"{paper_id},{ac_id.split('_')[0][1:]}")
            ac_data[paper_id]["assignment"] = ac_id
            ac_ids.add(ac_id)

    print(f"Read {len(ac_data)} AC data for {len(ac_ids)} ACs.")

    pm = ProfileMatcher(client, ac_ids)
    names = {ac_id: pm.get_name(ac_id) for ac_id in ac_ids}
    return ac_data, names


def get_ac_keywords():
    ac_list = read_ac_status()
    ac_kws = {}
    for ac in ac_list:
        ac_kws[ac["id"]] = ac["keywords"]
    print(f"Read {len(ac_kws)} AC keywords.")
    return ac_kws


def write_ac_paper_data(
    papers, sac_assignments, ac_data, ac_names, ac_kws, exclude_papers=[]
):
    ac_names = {k: v for k, v in sorted(ac_names.items(), key=lambda item: item[1])}
    header = [
        "Paper No",
        "ID",
        "Title",
        "Authors",
        "Authors IDs",
        "Keywords",
        "Category",
        "Senior Area Chair",
        "Initial Area Chair",
    ]
    header.extend(ac_names.values())
    header.extend(["Rec1", "Rec2", "Rec3", "Rec4", "Rec5"])
    with open(OUTPUT_FILE, "w") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for paper_id, paper in papers.items():
            # Skip ignored papers.
            if paper["number"] in exclude_papers:
                continue

            # Get data.
            sac_id = sac_assignments.get(paper_id, "")
            ac_paper_data = ac_data[paper_id]
            row = [
                paper["number"],
                paper_id,
                paper["title"],
                ", ".join(paper["authors"]),
                ";".join(paper["authors_ids"]),
                ";".join(paper["keywords"]),
                paper["category"],
                sac_id,
                ac_names.get(ac_paper_data.get("assignment"), "None"),
            ]

            # Get relation data for each AC.
            for ac_id in ac_names.keys():
                if ac_id in ac_paper_data["conflicts"]:
                    row.append(";CoI;")
                else:
                    bid = ac_paper_data["bids"].get(ac_id, "-")
                    affinity = (
                        f"{ac_paper_data['affinity'][ac_id]:.2f}"
                        if ac_id in ac_paper_data["affinity"]
                        else "-"
                    )
                    kw = (
                        f"{keyword_similarity(paper['keywords'], ac_kws[ac_id]):.2f}"
                        if ac_id in ac_kws and len(ac_kws[ac_id]) > 0
                        else "-"
                    )
                    row.append(f"{bid};{affinity};{kw}")

            # Get recommended ACs.
            recs = []
            scores = {
                ac_id: ac_paper_data["affinity"].get(ac_id, 0)
                + ac_paper_data["bids"].get(ac_id, 3)  # Check neutral default
                for ac_id in ac_names
            }
            scores = [
                id[0]
                for id in sorted(
                    scores.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ]
            for ac_id in scores:
                if ac_id in ac_paper_data["conflicts"]:
                    continue
                recs.append(ac_names[ac_id])
                if len(recs) >= 5:
                    break
            row.extend(recs)
            writer.writerow(row)
    print(f"Wrote paper data to '{OUTPUT_FILE}'.")


def read_sac_matching():
    assignments = {}  # paper_no: ac_name
    with open(ASSIGNMENT_SHEET, "r") as f:
        reader = csv.reader(f)
        skip_rows = 2
        for row in reader:
            if skip_rows > 0:
                skip_rows -= 1
                continue
            assignments[int(row[1])] = row[6]
    print(f"Read {len(assignments)} rows from '{ASSIGNMENT_SHEET}'.")
    return assignments


def setup_sac_matching_sheet(client):
    # Read all data from OpenReview.
    papers = get_papers(client)
    ac_data, ac_names = get_ac_data(client, papers)
    sac_assignments = get_sac_assignments(client)
    ac_kws = get_ac_keywords()

    # Additional configurations.
    write_ac_paper_data(papers, sac_assignments, ac_data, ac_names, ac_kws)


def deploy_sac_matching_sheet(client):
    assignments = read_sac_matching()  # paper_no: ac_name
    papers = get_papers(client)
    paper_ids = {
        paper["number"]: paper_id for paper_id, paper in papers.items()
    }  # no: id
    acs = client.get_group(f"{VENUE}/Area_Chairs").members
    pm = ProfileMatcher(client, acs)
    ac_names = {pm.get_name(ac_id): ac_id for ac_id in acs}  # name: id
    ac_names["Roberto Martin-Martin"] = "~Roberto_Martín-Martín1"  # Fix encoding issue
    print(f"Read {len(ac_names)} AC names.")

    # Clear existing edges.
    client.delete_edges(
        invitation=f"{VENUE}/Area_Chairs/-/Proposed_Assignment",
        label=OUTPUT_AC_MATCHING,
    )

    # Write new edges.
    num_assigned = 0
    num_paper_not_found = 0
    num_ac_not_found = 0
    edges = []
    for paper_no, ac_name in assignments.items():
        paper_id = paper_ids.get(paper_no)
        if not paper_id:
            print(f"Paper {paper_no} not found.")
            num_paper_not_found += 1
            continue
        ac_id = ac_names.get(ac_name)
        if not ac_id:
            print(f"AC {ac_name} not found.")
            num_ac_not_found += 1
            continue

        edges.append(
            openreview.Edge(
                invitation=f"{VENUE}/Area_Chairs/-/Proposed_Assignment",
                head=paper_id,
                tail=ac_id,
                label=OUTPUT_AC_MATCHING,
                weight=1,
                signatures=[
                    "roboticsfoundation.org/RSS/2025/Conference/Program_Chairs"
                ],
                readers=[
                    "roboticsfoundation.org/RSS/2025/Conference",
                    f"roboticsfoundation.org/RSS/2025/Conference/Submission{paper_no}/Senior_Area_Chairs",
                    ac_id,
                ],
                writers=[
                    "roboticsfoundation.org/RSS/2025/Conference",
                    f"roboticsfoundation.org/RSS/2025/Conference/Submission{paper_no}/Senior_Area_Chairs",
                ],
                nonreaders=[
                    f"roboticsfoundation.org/RSS/2025/Conference/Submission{paper_no}/Authors"
                ],
            )
        )
        print(f"Assigned paper {paper_no} to {ac_name}.")
        num_assigned += 1
    print("Posting to OpenReview...")
    client.post_edges(edges)
    print(f"Assigned {num_assigned} papers.")
    print(f"Failed to find {num_paper_not_found} papers.")
    print(f"Failed to find {num_ac_not_found} ACs.")


def check_sheet_status(client):
    assignments = read_sac_matching()
    papers = get_papers(client)
    sheet_nos = set(assignments.keys())
    paper_nos = set([paper["number"] for paper in papers.values()])
    missing_papers = sheet_nos - paper_nos
    print(f"Found {len(missing_papers)} removed papers still in sheet.")
    for p in missing_papers:
        print(f"- {p}")
    missing_sheets = paper_nos - sheet_nos
    print(f"Found {len(missing_sheets)} missing papers in sheet.")
    for p in missing_sheets:
        print(f"- {p}")
    print(
        f"Found {len(sheet_nos.intersection(paper_nos))} papers correctly listed in sheet."
    )


def main():
    client = setup_client()

    # set_max_papers(client, "~AC_ID", 1234)
    # setup_sac_matching_sheet(client)

    # check_sheet_status(client)

    deploy_sac_matching_sheet(client)


if __name__ == "__main__":
    main()
