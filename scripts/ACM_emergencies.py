from utils.paths import ROOT_DIR
import os
import pickle
from ACM_matching_energy.sessions import Session, Sessions
from ACM_matching_energy.data import load_data
import openreview
from ACM_matching_energy.inspection import print_breakout_groups, get_name
from datetime import datetime
from DEC_disable_rejected_papers import stamp_from_time
from REV_ratings import get_ratings, RATINGS
import csv
from matplotlib import pyplot as plt
import numpy as np

from utils.setup_client import setup_client
from utils.paths import VENUE
rating_to_int = {v: k for k, v in RATINGS.items()}

# Data Loading.
DATA_PATH = os.path.join(ROOT_DIR, "private", "matching", "data_relaxed") # data_relaxed, data_strict
SOLUTION_PATH = os.path.join(ROOT_DIR, "private", "matching", "final.p") # Path to the final solution.


"""
Mixed pickles of tools and functions for emergency scheduling and updating during the AC meeting.
"""



def deploy_to_openreview(client, secondary_acs):
    # Get user confirmation.
    print("Deploying secondary AC assignments to OpenReview.")
    for paper, ac in secondary_acs.items():
        print(f"Paper {paper} -> {ac}")
    print(f"Assignments: '{SOLUTION_PATH}'")
    print("Are you sure you want to continue? (y/n)")
    confirm = input().strip().lower()
    if confirm != "y":
        print("Aborting deployment.")
        return

    paper_no_to_id = {p.number: p.id for p in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})}
    paper_id_to_no = {v: k for k, v in paper_no_to_id.items()}

    # Delete edges tool if needed.
    # current_edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Assignment", groupby="head")
    # for edge in current_edges:
    #     for val in edge["values"]:
    #         paper_no = paper_id_to_no.get(val["head"], None)
    #         if not paper_no:
    #             continue
    #         ac = val["tail"]
    #         if ac in secondary_acs.values():
    #             print(f"Paper {paper_no} -> {ac}, edge ID: {val['id']}")
    #             print(f"Removing current assignment for paper {paper_no} -> {ac}")
    #             client.delete_edges(id=str(val["id"]), invitation=f"{VENUE}/Area_Chairs/-/Assignment")

    edges = []
    for paper_no, ac in secondary_acs.items():
        edges.append(openreview.Edge(
            invitation=f"{VENUE}/Area_Chairs/-/Assignment",
            head=paper_no_to_id[paper_no],
            tail=ac,
            weight=1,
            signatures=[
                f"{VENUE}/Program_Chairs"
            ],
            readers=[
                VENUE,
                f"{VENUE}/Submission{paper_no}/Senior_Area_Chairs",
                ac,
            ],
            writers=[
                VENUE,
                f"{VENUE}/Submission{paper_no}/Senior_Area_Chairs",
            ],
            nonreaders=[
                f"{VENUE}/Submission{paper_no}/Authors"
            ]
        ))
    # client.post_edges(edges)
    i = 0
    for paper_no, ac in secondary_acs.items():
        client.add_members_to_group(f"{VENUE}/Submission{paper_no}/Area_Chairs", [ac])
        print(f"Updatind submission {paper_no} with AC {ac} ({i+1}/{len(secondary_acs)})", end="\r")
        i += 1
    print(f"Deployed {i} SAC session papers to OpenReview.")

def deploy_sac_to_openreview(client, sessions):
    i = 0
    for sess in sessions.sessions:
        for p in sess.papers:
            client.add_members_to_group(f"{VENUE}/Submission{p}/Senior_Area_Chairs", list(sess.sacs))
            print(f"Updatind submission {p} with SAC { list(sess.sacs)[0]} ({i})", end="\r")
            i += 1


def print_sessions_with_remote_acs(sessions : Sessions, primary_acs, secondary_acs):
    remote_acs = set([])
    asia = set([])

    remote_sessions = []
    for i, sess in enumerate(sessions.sessions):
        if sess.acs & remote_acs:
            remote_sessions.append(i)

    print(f"Sessions with remote ACs: {len(remote_sessions)}")
    print(f"- {', '.join([str(s) for s in remote_sessions])}")

    # Check number of primary and secondary ACs from Asia in each session.
    rows = [i for i in range(sessions.num_sessions)]
    data = {i: {"primary": set(), "secondary": set()} for i in rows}
    for i, sess in enumerate(sessions.sessions):
        sac, row = sessions.keys_from_idx(i)
        for p in sess.papers:
            if primary_acs[p] in asia:
                data[row]["primary"].add(primary_acs[p])
            if secondary_acs[p] in asia:
                data[row]["secondary"].add(secondary_acs[p])
    print(f"Sessions with primary and secondary ACs from Asia:")
    for i, v in data.items():
        print(f"Session {i}: {len(v['primary'])} primary, {len(v['secondary'])} secondary, {len(v['secondary'].union(v['primary']))} unique primary or secondary ACs from Asia.")
        print(f"- primary: {', '.join([str(ac) for ac in v['primary']])} ")
        print(f"- secondary: {', '.join([str(ac) for ac in v['secondary']])} ")


def copy_pdfs_under_discussion(papers):
    src_path = os.path.join(ROOT_DIR, "private", "submission_pdfs")
    dest_path = os.path.join(src_path, "under_discussion")
    for paper in papers:
        file_no = f"{paper:03d}.pdf"
        os.makedirs(dest_path, exist_ok=True)
        # Copy the file to the destination.
        src_file = os.path.join(src_path, file_no)
        dest_file = os.path.join(dest_path, file_no)
        if os.path.exists(src_file):
            os.system(f"cp {src_file} {dest_file}")
        else:
            print(f"File '{src_file}' does not exist.")


def reorder_table(sessions : Sessions):
    new_sac_order = ['~Jeannette_Bohg1', '~Liam_Paull1', '~Luca_Carlone1', '~Maya_Çakmak1', '~Ramanarayan_Vasudevan1', '~Jana_Tumova1', '~Amanda_Prorok1', '~Van_Ho1']
    # print_breakout_groups(sessions)
    sessions.reorder_sacs(new_sac_order)
    print_breakout_groups(sessions)
    urls = ['https://tinyurl.com/RSS2025-Jeannette','https://tinyurl.com/RSS2025-Liam','https://tinyurl.com/RSS2025-Luca','http://tinyurl.com/RSS2025-Maya','https://tinyurl.com/RSS2025-Ram','https://tinyurl.com/RSS2025-Jana',
'https://tinyurl.com/RSS2025-Amanda','https://tinyurl.com/RSS2025-Van']
    urls = {sac : u for sac, u in zip(new_sac_order, urls)}
    for j in range(4):
        for i, idx in enumerate(sessions.indices_for_session(j)):
            sess = sessions.get(idx)
            # Print the session as raw text.
            sac = list(sess.sacs)[0]
            print(f"Session {i+1+j*8}: (SAC: {get_name(sac)}, Group {i+1}, {urls[sac]})")
            print(', '.join([str(p) for p in sess.papers]))
            print(', '.join([get_name(ac) for ac in sess.acs]))
    

def disable_meta_review(client, papers):
    """
    Disable editing of final meta reviews for all papers not in the discussion list (input).
    """
    under_discussion = set(papers)

    num_disabled = 0
    all_papers = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    for paper in all_papers:
        paper_no = paper.number
        if paper_no in under_discussion:
            continue

        meta_review_invitation = f"{VENUE}/Submission{paper_no}/-/Meta_Review"
        inv = client.get_invitation(meta_review_invitation)
        inv.expdate = stamp_from_time(datetime(2025, 4, 1))
        client.post_invitation_edit(f"{VENUE}/-/Edit", invitation=inv, signatures=[f"{VENUE}/Program_Chairs"])
        print(f"Disabled meta review for paper {paper_no}.")
        num_disabled += 1
    print(f"Disabled meta review for {num_disabled}/{len(all_papers)} papers.")


def read_anonymization():
    """
    Read the anonymization file and return a list of papers.
    """
    with open(os.path.join(ROOT_DIR, "private", "paper_conflicts.csv"), "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        ids = {}
        for row in reader:
            ids[int(row[0])] = row[3]
    return ids


def get_paper_discussion_csv(client, papers, sessions, ac_assignments):
    """
    Get the paper discussion CSV file.
    """
    ratings = get_ratings(client)
    ratings = {k: v for k, v in ratings.items() if k in papers}
    anon_ids = read_anonymization()
    discussed_on_44 = set()
    for i in range(2):
        for j in sessions.indices_for_session(i):
            discussed_on_44.update(sessions.get(j).papers)

    accept = set()
    # Save to csv.
    output_file = os.path.join(ROOT_DIR, "private", "ACM_discussion.csv")
    missing = {}
    with open(output_file, "w") as f:
        writer = csv.writer(f)
        header = ["Paper", "Category", "Review 1", "Review 2", "Review 3", "Review 4", "Review 5", "Meta Review", "Date","AC Meeting Recommendation"] 
        writer.writerow(header)
        for no, data in sorted(ratings.items()):
            row = [anon_ids[no], data["category"]]
            for i in range(5):
                if i < len(data["reviews"]):
                    rating = data["reviews"][i]["overall_recommendation"]["value"]
                    row.append(RATINGS[rating] if rating in RATINGS else rating)
                else:
                    row.append(" ")
            # Save meta review rating.
            rating = data["meta_review"]["overall_recommendation"]["value"]
            row.append(RATINGS[rating] if rating in RATINGS else rating)

            # Accept rule
            if rating_to_int[rating] >= 4:
                accept.add(no)

            # Save second meta review decision.
            row.append("4/4" if no in discussed_on_44 else "4/5")
            ac_meeting_decision = data["meta_review"].get("overall_recommendation_after_area_chair_meeting", {}).get("value")
            if not ac_meeting_decision:
                ac = ac_assignments[no]
                if ac in missing:
                    missing[ac].add(no)
                else:
                    missing[ac] = {no}
            row.append(ac_meeting_decision if ac_meeting_decision else " ")
            writer.writerow(row)

    print(f"Saved ratings to '{output_file}'.")
    for ac, papers in missing.items():
        print(f"AC {get_name(ac)} misses {len(papers)} papers: {', '.join([str(p) for p in papers])}")

    return accept



def check_reassignment(sessions : Sessions, prim_acs, seoncd_acs, conflicts, ac, new_sess_idx):
    # Find the original session.
    prim = set()
    sec = set()
    new_sac, new_row = sessions.keys_from_idx(new_sess_idx)
    prev_sac = None
    for i in sessions.indices_for_session(new_row):
        sess = sessions.get(i)
        if ac in sess.acs:
            # Check for primary and secondary ACs.
            for p in sess.papers:
                if prim_acs[p] == ac:
                    prim.add(p)
                if seoncd_acs[p] == ac:
                    sec.add(p)
            prev_sac = list(sess.sacs)[0]
            break
    # Check CoI in the new sessions
    sess = sessions.get(new_sess_idx)
    coi = set()
    for p in sess.papers:
        if ac in conflicts[p]:
            coi.add(p)

    # Print the results.
    print(f"Moving {ac} in session {new_row} (to {new_sac} from {prev_sac}):")
    print(f"- Is primary AC of papers: {', '.join([str(p) for p in prim])}")
    print(f"- Is secondary AC of papers: {', '.join([str(p) for p in sec])}")
    print(f"- CoI with papers: {', '.join([str(p) for p in coi])}")
    
def download_pdfs(client, papers):
    output_dir = os.path.join(ROOT_DIR, "private", "submission_pdfs_discussion")
    os.makedirs(output_dir, exist_ok=True)
    submissions = client.get_all_notes(invitation=f"{VENUE}/-/Submission")
    num_pdfs = 0
    print("Downloading submission PDFs...")
    for note in submissions:
        if note.number not in papers:
            continue
        if note.content.get("pdf", {}).get("value"):
            f = client.get_attachment(note.id, "pdf")
            with open(os.path.join(output_dir, f"{note.number:03d}.pdf"), "wb") as op:
                op.write(f)
            num_pdfs += 1
    print(f"Downloaded {num_pdfs} submission PDFs.")

def check_single_paper_coi(client, paper_no):
    open_review_papers = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})
    paper_id_to_no = {p.forum: p.number for p in open_review_papers}
    edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Conflict", groupby="head") +  client.get_grouped_edges(f"{VENUE}/Senior_Area_Chairs/-/Conflict", groupby="head")
    conflicts = set()
    for edge in edges:
        for val in edge["values"]:
            paper_id = paper_id_to_no.get(val["head"],None)
            if paper_id == paper_no:
                conflicts.add(val['tail'])
    # Print the results.
    print(f"Paper {paper_no} has conflicts with {len(conflicts)} ACs:")
    for ac in conflicts:
        print(f"- {ac}")

def print_coi_csv(client, papers, conflicts):
    anon_ids = read_anonymization()
    output_file = os.path.join(ROOT_DIR, "private", "acmeeting_coi.csv")
    with open(output_file, "w") as f:
        writer = csv.writer(f)
        header = ["Paper", "CoI"] 
        writer.writerow(header)
        for paper in papers:
            acs = conflicts[paper]
            row = [anon_ids[paper], ', '.join([get_name(ac) for ac in acs])]
            writer.writerow(row)
    print(f"Saved COI to '{output_file}'.")


def get_accepted_papers(client, papers_under_discussion):
    ratings = get_ratings(client)
    accepted_demo = set()
    accepted_ss = set()
    for no, data in ratings.items():
        if no in papers_under_discussion:
            continue
        meta_review = data["meta_review"]
        decision = meta_review.get("suggested_decision", {}).get("value")
        if decision != "Accept":
            continue
        accepted_demo.add(no) if data["category"] == "Demo" else accepted_ss.add(no)

    print(f"Accepted demos: {len(accepted_demo)}")
    print(f"Accepted Science/Systems: {len(accepted_ss)}")
    print(f"Total accepted papers: {len(accepted_demo) + len(accepted_ss)}")
    return accepted_demo, accepted_ss


def plot_kws(client, paper_lists):
    # papers: List of papers to plot on top of each other.
    # Get all keywords.
    paper_kws ={}
    keywords = set()
    for paper in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"}):
        kws = paper.content["keywords"]["value"]
        paper_kws[paper.number] = kws
        keywords.update(kws)
    keywords = sorted(list(keywords))

    data = []
    rejected = set(paper_kws.keys())
    for p in paper_lists:
        rejected = rejected - set(p)
    paper_lists.append(rejected)
    for papers in paper_lists:
        kw_data = {kw : 0 for kw in keywords}
        for p in papers:
            kw_data[paper_kws[p][0]] += 1
            # for kw in paper_kws[p]:
                # kw_data[kw] += 1
        data.append(np.array([kw_data[kw] for kw in keywords]))

    colors = ["b", "lawngreen", "r", "lightgray"] # "gold",
    x = np.arange(len(keywords))
    plt.figure(figsize=(10, 12))

    # Stacked bar plot.
    x = np.arange(len(keywords))
    current_bottom = np.zeros(len(keywords))
    for i, kw_data in enumerate(data):
        plt.bar(x, kw_data, color=colors[i], bottom=current_bottom)
        current_bottom += kw_data

    plt.legend(["Accepted", "Accept after Discussion", "Reject after Discussion", "Rejected"])
    
    plt.xticks(x, keywords, rotation=90)
    plt.tight_layout(rect=[0, 0, 1, 1])
    plt.show()


def find_breakout_for(sessions : Sessions, affinities, conflicts, secondary_ac, paper_no):
    new_sac_order = ['~Jeannette_Bohg1', '~Liam_Paull1', '~Luca_Carlone1', '~Maya_Çakmak1', '~Ramanarayan_Vasudevan1', '~Jana_Tumova1', '~Amanda_Prorok1', '~Van_Ho1']
    # print_breakout_groups(sessions)
    sessions.reorder_sacs(new_sac_order)
    breakout_sessions = [3,7,11,15,19,23,27,31]
    session_remap = [i for i in range(25,33)]
    print(session_remap)
    num_coi = []
    max_affinity = []
    sec_acs = []
    for i in breakout_sessions:
        sess = sessions.get(i)
        coi = set()
        max_aff = 0
        sec_ac = False
        for ac in sess.acs:
            if ac in conflicts[paper_no]:
                coi.add(ac)
            if ac in secondary_ac[paper_no]:
                sec_ac = True
            aff = affinities[paper_no].get(ac,0)
            max_aff = max(max_aff, aff)
        for sac in sess.sacs:
            if sac in conflicts[paper_no]:
                coi.add(sac)
            aff = affinities[paper_no].get(sac,0)
            max_aff = max(max_aff, aff)
        num_coi.append(coi)
        max_affinity.append(max_aff)
        sec_acs.append(sec_ac)

    print(f"Session options for paper {paper_no}:")
    for i, _ in enumerate(breakout_sessions):
        sec_ac_str = " [Secondary AC]" if sec_acs[i] else ""
        print(f"- S{session_remap[i]}: {len(num_coi[i])} ({', '.join([get_name(c) for c in num_coi[i]])}) CoI, max affinity: {max_affinity[i]:.2f}"+sec_ac_str)



def main():
    papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = load_data(DATA_PATH)
    with open(SOLUTION_PATH, "rb") as f:
        sessions, secondary_acs, stats, duration = pickle.load(f)
    
    # print_sessions_with_remote_acs(sessions, ac_assignments, secondary_acs)
    # copy_pdfs_under_discussion(papers)
    # reorder_table(sessions)

    client = setup_client()
    # deploy_to_openreview(client, secondary_acs)
    # deploy_sac_to_openreview(client, sessions)
    # disable_meta_review(client,papers)

    # check_reassignment(sessions, ac_assignments, secondary_acs, conflicts,"~AC_ID", 1234)
    # download_pdfs(client, papers)
    # check_single_paper_coi(client, 1234)
    # print_coi_csv(client, papers, conflicts)

    # find_breakout_for(sessions, affinities, conflicts, secondary_acs, 1234)


    # KWS
    # accept_after_discuss = get_paper_discussion_csv(client, papers, sessions, ac_assignments)
    # accepted_demo, accepted_ss = get_accepted_papers(client, papers)
    # plot_kws(client, [accepted_demo.union(accepted_ss), accept_after_discuss, set(papers).difference(accept_after_discuss)]) # pre-accepted,

    get_paper_discussion_csv(client, papers, sessions, ac_assignments)





if __name__ == "__main__":
    main()
