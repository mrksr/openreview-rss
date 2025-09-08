from utils.paths import ROOT_DIR
import os
import pickle
import time
import numpy as np
import csv
from ACM_matching_energy.sessions import Session, Sessions
from ACM_matching_energy.energy_matcher import EnergyMatcher
from ACM_matching_energy.data import load_data, load_csv_results, load_keywords
from ACM_matching_energy.inspection import (
    print_breakout_groups,
    verify_conflicts,
    analyze_breakout_groups,
    analyze_assignments,
    verify_assignment_conflicts,
    plot_assignments,
    plot_breakout_groups,
    plot_optimization_stats,
    plot_ac_sessions,
    get_name
)
from utils.setup_client import setup_client
from utils.paths import VENUE
import openreview

"""
Compute Matchings for the AC meeting discussion phase:
1. Identify papers for discussion.
2. Get all affinity and CoI scores.
3. Assign secondary ACs to papers.
4. Build matchings for discussion groups.
"""

# Data Loading.
DATA_PATH = os.path.join(ROOT_DIR, "private", "matching", "data_relaxed") # data_relaxed, data_strict
EXTRA_PAPERS = []

# Secondary AC assignment parameters.
SECOND_AC_MAX_LOAD = 4
PRE_ASSIGN_SECONDARY_ACS = False # If true, assign secondary ACs to papers optimally and then match the sessions. Otherwise, assign them during the matching process.

# Session parameters.
NUM_SESSIONS = 3 # Number of sequential breakout sessions.
NUM_PAPERS_PER_SESSION = 6 # Maximum number of papers per session.
MAX_NUM_ACS_PER_SESSION = 9 # Maximum number of ACs per session. Does not include the SAC.
ADD_OVERFLOW_SESSION = True # If true, add an overflow session.
MAX_PAPERS_IN_OVERFLOW_SESSION = 3 # Maximum number of papers in the overflow session.


# Breakout Group Matching Parameters
ITERATIONS = 20000000 # Number of retries to find a valid assignment. (10000~3min, 50000~15min, 100000~30min)
NUM_THREADS = None # Number of threads to use for the matching. Use None for all threads. This runs num iterations in every thread!
PREFER_ASSIGNED_SAC = False # Prefer the assigned SAC for a paper.
SECOND_ACS_GREEDY = True # Use greedy assignment for secondary ACs.
INCLUDE_SAC_AFFINITIES = True # Include SAC affinities in the matching process.
AVERAGE_PER_SESSION = True # Use average affinity per session for the energy function. If false, use the total affinity.
CHECKPOINT_EVERY = 10000 if ITERATIONS > 10000 else 0 # If >0, save the matching every CHECKPOINT_EVERY iterations.


def parse_session_to_csv():
    # Session to analyze.
    with open(os.path.join(ROOT_DIR, "private", "matching", "final.p"), "rb") as f:
        sess, sec_acs, stats, duration = pickle.load(f)

    # Load keywords and data.
    paper_kws, ac_kws = load_keywords()
    papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = load_data(DATA_PATH)
    print(f"Found {len(papers)} papers for discussion.")

    # Save to CSV.
    output_file = os.path.join(ROOT_DIR, "private", "matching", "session_analysis.csv")
    save_session_analysis_to_csv(sess, paper_kws, ac_kws, affinities, sec_acs, output_file)


def save_session_analysis_to_csv(sess, paper_kws, ac_kws, affinities, sec_acs, output_file):
    client = setup_client()
    paper_hash = { p.number : p.id for p in client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})}

    def pad(list, length=6):
        return list + [""] * (length - len(list))
    with open(output_file, "w") as f:
        writer = csv.writer(f)
        for i, session in enumerate(sess.sessions):
            writer.writerow([f"Session {i}"])
            papers = sorted(list(session.papers))
            writer.writerow(["Paper No", ""] + pad([f"=hyperlink(\"https://openreview.net/forum?id={paper_hash[p]}\",{p})" for p in papers]) + [""] * 7)
            writer.writerow(["Paper KWS", ""] + pad(['; '.join(paper_kws.get(p, [])) for p in papers]) + ["Affs"] + [""] * 6)
            acs = list(session.sacs) + sorted(list(session.acs))
            for ac in acs:
                ac_name = get_name(ac)
                writer.writerow([ac_name, '; '.join(ac_kws.get(ac, []))] + pad([len(paper_kws[p] & ac_kws.get(ac,set())) for p in papers]) + [ac_name] + pad([affinities[paper].get(ac, 0) for paper in papers]))
    print(f"Saved session analysis to '{output_file}'.")

    # Save Secondary ACs.
    sec_ac_file = os.path.join(ROOT_DIR, "private", "matching", "secondary_acs.csv")
    with open(sec_ac_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Paper", "Secondary AC", "Affinity", "Num KW", "Paper KWS", "AC KWS"])
        for paper, ac in dict(sorted(sec_acs.items())).items():
            paper_kw = paper_kws.get(paper, set())
            ac_kw = ac_kws.get(ac, set())
            writer.writerow([f"=hyperlink(\"https://openreview.net/forum?id={paper_hash[paper]}\",{paper})", ac, affinities[paper].get(ac, 0), len(paper_kw & ac_kw),'; '.join(paper_kw), '; '.join(ac_kw)])
    print(f"Saved secondary ACs to '{sec_ac_file}'.")


def compare_solutions():
    papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = load_data(DATA_PATH)
    milp_sol, optimal_sec_acs = load_csv_results()

    files = [ "second_affs_10k_random", "second_affs_10k_greedy"]
    names = [ "Previous", "AC Energy"]
    add_optimal = True
    colors = ['g', 'b', 'y']


    sessions = []
    second_acs = []
    for file in files:
        with open(os.path.join(ROOT_DIR, "private", "matching", f"{file}.p"), "rb") as f:
            sess, sec_acs, stats, duration = pickle.load(f)
            sessions.append(sess)
            second_acs.append(sec_acs)
    if add_optimal:
        sessions.append(milp_sol)
        second_acs.append(optimal_sec_acs)
        # names.append("Optimal Pre-Computed")
        names.append("MILP")


    # ------ Compare Energy and MILP solutions. ------
    # plot_breakout_groups([milp_sol, energy_sol], affinities, labels=["MILP", "Energy"])
    # plot_assignments([milp_sol, energy_sol], [milp_secondary_acs,energy_secondary_acs], ac_assignments, sac_assignments, affinities, all_acs, labels=["MILP", "Energy"])

    # ------ Compare num Iterations ------
    # plot_assignments(sessions, second_acs, ac_assignments, sac_assignments, affinities, all_acs, labels=names, colors=colors)
    plot_breakout_groups(sessions, affinities, labels=names, colors=colors)


def plot_milp_solution():
    papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = load_data(DATA_PATH, force_recompute=True)
    matching, secondary_acs = load_csv_results()
    print_breakout_groups(matching)
    verify_conflicts(matching, conflicts)
    # analyze_breakout_groups(matching, affinities, sac_assignments, include_sac_affinities=INCLUDE_SAC_AFFINITIES)
    analyze_assignments(secondary_acs, affinities)

    # Plot overview of the results.
    # plot_breakout_groups(matching, affinities)


def plot_checkpoint(file_path):
    papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = load_data(DATA_PATH)
    with open(file_path, "rb") as f:
        matching, secondary_acs, stats, duration = pickle.load(f)
    # print_breakout_groups(matching)
    verify_conflicts(matching, conflicts)
    # analyze_breakout_groups(matching, affinities, sac_assignments, include_sac_affinities=INCLUDE_SAC_AFFINITIES)
    # analyze_assignments(secondary_acs, affinities)

    # Plot overview of the results.
    # plot_optimization_stats(stats)
    plot_assignments([matching], [secondary_acs], ac_assignments, sac_assignments, affinities, all_acs)
    # plot_breakout_groups([matching], affinities)

    matching.add_standout_session(all_acs)
    print_breakout_groups(matching)



def run_energy_matcher():
     # Load all the data.
    papers, affinities, conflicts, ac_assignments, sac_assignments, all_acs, all_sacs = load_data(DATA_PATH)#, force_recompute=True, extra_papers=EXTRA_PAPERS)
    ac_assignments = {k: set([v]) for k, v in ac_assignments.items()}
    sac_assignments = {k: set([v]) for k, v in sac_assignments.items()}
    print(f"Found {len(papers)} papers for discussion.")

    # Load keypoint scores.
    paper_kws, ac_kws = load_keywords()
    kw_affinities = {p: {ac: min(len(paper_kws.get(p, set()) & ac_kws.get(ac, set())), 3) for ac in all_acs + all_sacs} for p in papers}     # {paper_no: {ac: score}}


    # Setup the sessions grid.
    papers_per_session = [NUM_PAPERS_PER_SESSION] * NUM_SESSIONS
    if ADD_OVERFLOW_SESSION:
        papers_per_session.append(MAX_PAPERS_IN_OVERFLOW_SESSION)
    num_sessions = NUM_SESSIONS + 1 if ADD_OVERFLOW_SESSION else NUM_SESSIONS
    sessions = Sessions(num_sessions, all_sacs, papers_per_session * len(all_sacs), MAX_NUM_ACS_PER_SESSION) 
    print(f"Created {num_sessions} sessions with {len(all_sacs)} SACs.")
    print(f"- Total {len(papers)} papers to fit into {sessions.max_total_papers()} slots.")
    print(f"- Total {len(all_acs)} AC to fit into {num_sessions} x {int(sessions.max_total_acs()/num_sessions)} ({sessions.max_total_acs()}) slots.")
    print(f"- Total {SECOND_AC_MAX_LOAD * len(all_acs)} seconday AC capacity for {len(papers)} papers.")

    # Setup the matcher configuration.
    matcher = EnergyMatcher()
    matcher.num_iterations = ITERATIONS
    matcher.prefer_assigned_sac = PREFER_ASSIGNED_SAC
    matcher.secondary_ac_max_load = SECOND_AC_MAX_LOAD
    matcher.second_ac_greedy = SECOND_ACS_GREEDY
    if NUM_THREADS is not None:
        matcher.num_threads = NUM_THREADS

    # Checkpointing.
    if CHECKPOINT_EVERY > 0:
        matcher.checkpoint_num_it = CHECKPOINT_EVERY
        matcher.checkpoint_file = os.path.join(ROOT_DIR, "private", "matching", "checkpoint.p")

    # Pre-assign secondary ACs to papers.
    if PRE_ASSIGN_SECONDARY_ACS:
        _, optimal_seoncd_acs = load_csv_results()
        matcher.assign_secondary_acs = False
        for p, ac in optimal_seoncd_acs.items():
            ac_assignments[p].add(ac)
    
    # Define the energy function. This is the obejctive that will be maximized.
    def energy(sessions: Session, secondary_acs: dict):
        session_affs = []
        session_kws = []
        for session in sessions.sessions:
            affs = [affinities[p].get(ac, 0) for p in session.papers for ac in session.acs]
            kw = [kw_affinities[p][ac] for p in session.papers for ac in session.acs]
            if INCLUDE_SAC_AFFINITIES:
                affs.extend([affinities[p].get(sac, 0) for p in session.papers for sac in session.sacs])
                session_kws.extend([kw_affinities[p][sac] for p in session.papers for sac in session.sacs])
            if affs:
                session_affs.append(np.mean(affs)) if AVERAGE_PER_SESSION else session_affs.extend(affs)
            if kw:
                session_kws.append(np.mean(kw)) if AVERAGE_PER_SESSION else session_kws.extend(kw)

        ac_affs = [affinities[paper][ac] for paper, ac in secondary_acs.items() if ac in affinities[paper]]

        return np.mean(session_affs) + 2* np.mean(ac_affs) + 2 * np.min(ac_affs) + 0.3 * np.mean(session_kws)

    # Solve the matching problem.
    matcher.energy_fn = energy
    matcher.setup_problem(sessions, papers, conflicts, affinities, ac_assignments, sac_assignments, set(all_acs))
    start = time.time()
    matching, secondary_acs = matcher.solve()
    duration = time.time() - start
    stats = matcher.get_optimization_stats()
    if PRE_ASSIGN_SECONDARY_ACS:
        secondary_acs = optimal_seoncd_acs

    # Save the results.
    with open(os.path.join(ROOT_DIR, "private", "matching", "results.p"), "wb") as f:
        pickle.dump((matching, secondary_acs, stats, duration), f)
    
    save_session_analysis_to_csv(matching, paper_kws, ac_kws, affinities, secondary_acs, os.path.join(ROOT_DIR, "private", "matching", "session_analysis.csv"))

    # Print results.
    matching.add_standout_session(all_acs)
    print_breakout_groups(matching)
    # verify_conflicts(matching, conflicts)
    # analyze_breakout_groups(matching, affinities, sac_assignments, include_sac_affinities=INCLUDE_SAC_AFFINITIES)
    # analyze_assignments(secondary_acs, affinities)
    # print(" Assignment Success ".center(80, "="))
    # print(f"Assigned {matching.total_papers()}/{len(papers)} papers to sessions.")
    # print(f"Assigned {len(secondary_acs)}/{len(papers)} secondary ACs.")

    # Plot overview of the results.
    # plot_ac_sessions(matching)
    plot_optimization_stats(stats)

def main():
    # run_energy_matcher()
    plot_checkpoint(os.path.join(ROOT_DIR, "private", "matching", "final.p"))
    # plot_milp_solution()
    # compare_solutions()
    # parse_session_to_csv()


if __name__ == "__main__":
    main()
