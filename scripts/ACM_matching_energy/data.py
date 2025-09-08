import pickle
import os
import csv
from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
from AC_status import read_ac_status
from .sessions import Sessions

"""
Data io tools for the AC meeting matching.
"""


def get_papers_for_discussion():
    # Read the papers from the ratings file.
    papers = []
    with open(os.path.join(ROOT_DIR, "private", "review_ratings.csv"), "r") as f:
        reader = csv.reader(f)
        # Papers are ordered by preference.
        headers = None
        for row in reader:
            if headers is None:
                headers = row
                continue
            papers.append({headers[i]: data for i,data in enumerate(row)})
         
    # Get the remaining papers.
    candidate_papers = [int(p["Paper No"]) for p in papers if p["AC Decision"] in ["Discuss",""] and p["First Round Decision"] == "Invited for Rebuttal"]
    return candidate_papers
            

def get_matching_data(client, papers, additional_sacs=[]):
    # Get all assignments, affinity scores and COIs for these papers.
    affinities = {paper_no: {} for paper_no in papers} # {paper_no: {(s)ac_id: affinity_score}}
    conflicts = {paper_no: set() for paper_no in papers}    # {paper_no: set((s)ac_ids)}
    ac_assignments = {}
    sac_assignments = {}

    # Get all AC data for each submission.
    print("Loading matching data from OpenReview...")
    open_review_papers = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    paper_id_to_no = {p.forum: p.number for p in open_review_papers if p.number in papers}

    # Get all ACs and SACs.
    all_acs = sorted([ac for ac in client.get_group(f"{VENUE}/Area_Chairs").members])
    all_sacs = [sac for sac in client.get_group(f"{VENUE}/Senior_Area_Chairs").members]
    all_sacs = sorted(all_sacs + additional_sacs)

    # Affinity scores. This should exhaust all papers and ACs.
    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Affinity_Score", groupby="head"
    ) + client.get_grouped_edges(
        f"{VENUE}/Senior_Area_Chairs/-/Affinity_Score", groupby="head")
    for edge in edges:
        for val in edge["values"]:
            paper_id = paper_id_to_no.get(val["head"],None)
            if paper_id:
                affinities[paper_id][val["tail"]] = val["weight"]

    # Conflicts.
    edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Conflict", groupby="head") +  client.get_grouped_edges(f"{VENUE}/Senior_Area_Chairs/-/Conflict", groupby="head")
    for edge in edges:
        for val in edge["values"]:
            paper_id = paper_id_to_no.get(val["head"],None)
            if paper_id:
                conflicts[paper_id].add(val["tail"])

    # AC Assignments.
    edges = client.get_grouped_edges(
        f"{VENUE}/Area_Chairs/-/Assignment", groupby="head"
    )
    for edge in edges:
        for val in edge["values"]:
            paper_id = paper_id_to_no.get(val["head"],None)
            if paper_id:
                ac_assignments[paper_id] = val["tail"]

    # SAC Assignments.
    edges = client.get_grouped_edges(
        f"{VENUE}/Senior_Area_Chairs/-/Assignment", groupby="head"
    )
    for edge in edges:
        for val in edge["values"]:
            paper_id = paper_id_to_no.get(val["head"],None)
            if paper_id :
                sac_assignments[paper_id] =  val["tail"]

    return affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs      

def load_data(target_dir, force_recompute=False, extra_papers=[]):
    # Check for lazy loading.
    pickle_file = os.path.join(target_dir, "matching_data.p")
    if os.path.exists(pickle_file) and not force_recompute:
        with open(pickle_file, "rb") as f:
            return pickle.load(f)
        
    # Load data from OpenReview.
    client = setup_client()
    papers = get_papers_for_discussion()
    papers = sorted(list(set(papers + extra_papers)))
    affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = get_matching_data(client, papers, additional_sacs=["~Luca_Carlone1", "~Amanda_Prorok1"])

    # If needed: fix conflict in initial assignments.
    for paper, ac in ac_assignments.items():
        conflicts[paper].discard(ac)
    for paper, sac in sac_assignments.items():
        conflicts[paper].discard(sac)

    # Save to cache and output files.
    with open(pickle_file, "wb") as f:
        pickle.dump((papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs), f)
    save_matching_data_to_csv(papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs, target_dir)

    return papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs

def save_matching_data_to_csv(papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs, target_dir):
    # Save the data to a CSV file.
    papers = sorted(papers)

    # Affinities.
    with open(os.path.join(target_dir, "A.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(["AC Affinities"] + papers)
        for ac in all_acs:
            writer.writerow([ac] + [affinities[paper].get(ac, 0) for paper in papers])
    with open(os.path.join(target_dir, "A_S.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(["SAC Affinities"] + papers)
        for sac in all_sacs:
            writer.writerow([sac] + [affinities[paper].get(sac, 0) for paper in papers])

    # Conflicts.
    with open(os.path.join(target_dir, "C.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(["AC Conflicts"] + papers)
        for ac in all_acs:
            writer.writerow([ac] + [1 if ac in conflicts[paper] else 0 for paper in papers])
    with open(os.path.join(target_dir, "C_S.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(["SAC Conflicts"] + papers)
        for sac in all_sacs:
            writer.writerow([sac] + [1 if sac in conflicts[paper] else 0 for paper in papers])

    # Assignments.
    with open(os.path.join(target_dir, "P.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(["P"] + papers)
        for ac in all_acs:
            writer.writerow([ac] + [1 if ac == ac_assignments.get(paper) else 0 for paper in papers])
    with open(os.path.join(target_dir, "P_S.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(["SAC Assignments"] + papers)
        for sac in all_sacs:
            writer.writerow([sac] + [1 if sac == sac_assignments.get(paper) else 0 for paper in papers])
    print(f"Saved matching data to '{os.path.join(ROOT_DIR, 'private', 'matching')}'.")

def load_csv_results(target_dir):
    # Load the optimization results from the CSV files.

    # Load the session data. These are ordered since the CSV uses only ordering not the IDs.
    acs = []
    sacs = []
    papers = []
    with open(os.path.join(target_dir, "A.csv"), "r") as f:
        reader = csv.reader(f)
        headers = next(reader)
        papers = [int(p) for p in headers[1:]]
        for row in reader:
            acs.append(row[0])
    with open(os.path.join(target_dir, "A_S.csv"), "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            sacs.append(row[0])

    # Load the solution.
    num_sessions = 0
    num_acs = len(acs)
    ac_data = {ac : set() for ac in acs}
    sac_data = {sac : set() for sac in sacs}
    paper_data = {}
    with open(os.path.join(target_dir, "X.csv"), "r") as f:
        reader = csv.reader(f)
        # ACs to Sessions.
        for i, row in enumerate(reader):
            num_sessions = len(row)
            for j, val in enumerate(row):
                if val == "1":
                    ac_data[acs[i]].add(j) if i < num_acs else sac_data[sacs[i - num_acs]].add(j)
    with open(os.path.join(target_dir, "Y.csv"), "r") as f:
        reader = csv.reader(f)
        # Papers to Sessions.
        for i, row in enumerate(reader):
            for j, val in enumerate(row):
                if val == "1":
                    paper_data[papers[i]] = j
                    
    # Create the sessions.
    sacs.append("Standout")
    num_sessions = int(num_sessions / len(sacs) )
    sessions = Sessions(num_sessions, sacs, 0)

    # Session remapping for.
    remapping = {}
    for sac, sess in sac_data.items():
        for session in sess:
            session_no = session // sessions.num_sacs
            remapping[session] = sessions.idx_from_keys(sac, session_no)
    for i in range(num_sessions):
        remapping[(i+1) * sessions.num_sacs -1] = sessions.idx_from_keys("Standout", i)
    
    # Assign papers and ACs to sessions.
    for paper, session in paper_data.items():
        sessions.get(remapping[session]).papers.add(paper)
    for ac, sess in ac_data.items():
        for session in sess:
            sessions.get(remapping[session]).acs.add(ac)


    # Load the secondary AC assignments.
    secondary_acs = {}
    with open(os.path.join(target_dir, "S.csv"), "r") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for i, row in enumerate(reader):
            for j, val in enumerate(row[1:]):
                if val == "1":
                    secondary_acs[papers[j]] = acs[i]
    return sessions, secondary_acs


def load_keywords(lazy=True, cache_file=os.path.join(ROOT_DIR, "private", "matching", "keywords.p")):
    if lazy and os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return pickle.load(f)
  
    client = setup_client()
    submissions = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})

    paper_kw = {sub.number: set(sub.content["keywords"]["value"]) for sub in submissions}
    print(f"Read {len(submissions)} paper keywords.")

    acs = read_ac_status()
    ac_kw = {}  
    for ac in acs:
        ac_kw[ac["id"]] = set(ac.get("keywords", []))
    print(f"Read {len(acs)} AC keywords.")

    # Save to cache.
    print(f"Saved {len(paper_kw)} paper and {len(ac_kw)} AC keywords to '{cache_file}'.")
    with open(cache_file, "wb") as f:
        pickle.dump((paper_kw, ac_kw), f)
    return paper_kw, ac_kw
            


