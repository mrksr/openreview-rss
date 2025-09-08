
from matplotlib import pyplot as plt
from .sessions import Sessions, Session
import numpy as np

"""
Tools to analyze and inspect the results of the AC meeting matching process.
"""

def get_name(ac_id):
    """
    Approximate name from OpenReview ID for better legibility.
    """
    if ac_id.find("~") != 0:
        return ac_id
    splits = ac_id.split("_")
    return splits[0][1:] + " " + splits[1][0] + "."

def verify_assignment_conflicts(ac_assignments, sac_assignments, conflicts):
    """
    Check if there are already conflicts in the assignments.
    """
    found = [] # List of conflicts. [(ac_id, paper_id)]
    for p, ac_id in ac_assignments.items():
        if ac_id in conflicts[p]:
            found.append((ac_id, p))
    for p, sac_id in sac_assignments.items():
        if sac_id in conflicts[p]:
            found.append((sac_id, p))
    if found:
        print(f"Found {len(found)} conflicts in initial assignment:")
        for ac_id, paper_id in found:
            print(f"- {paper_id} has a conflict with {ac_id}")
    else:
        print("No conflicts found in initial assignment.")

def verify_conflicts(sessions : Sessions, conflicts):
    conlicts = [] # List of conflicts. [(session_no, ac_id, paper_id)]
    for i, s in enumerate(sessions.sessions):
        for p in s.papers:
            for ac in list(s.acs) + list(s.sacs):
                if ac in conflicts[p]:
                    conlicts.append((i, ac, p))
    if conlicts:
        print(f"Found {len(conlicts)} conflicts:")
        for i, ac, p in conlicts:
            print(f"- Session {i+1}: {ac} has a conflict with paper {p}")
    else:
        print("No conflicts found.")


def compute_group_assignment_stats(sessions : Sessions):
    """
    Compute the statistics of the group assignments in the sessions.
    """
    stats = {}
    stats["papers_per_session"] = [len(s.papers) for s in sessions.sessions]
    stats["acs_per_session"] = [len(s.acs) for s in sessions.sessions]
    sessions_per_ac = {}
    for session in sessions.sessions:
        for ac in session.acs:
            if ac not in sessions_per_ac:
                sessions_per_ac[ac] = 0
            sessions_per_ac[ac] += 1
    stats["sessions_per_ac"] = sessions_per_ac
    return stats

def print_stat(vals):
    if isinstance(vals, dict):
        vals = list(vals.values())
    print(f"- Min: {np.nanmin(vals):.02f}")
    print(f"- Max: {np.nanmax(vals):.02f}")
    print(f"- Mean: {np.nanmean(vals):.02f}")
    print(f"- Median: {np.nanmedian(vals):.02f}")

def print_breakout_groups(sessions : Sessions, max_papepers_on_line=6):
    # Print table with breakout groups.
    max_num_papers = max([len(s.papers) for s in sessions.sessions])
    if max_num_papers > max_papepers_on_line:
        max_num_papers = max_papepers_on_line
    SPACING = max_num_papers * 3 + (max_num_papers - 1) * 2 + 3
    HEAD_SPACING = 10
    total_width = HEAD_SPACING + sessions.num_sacs * SPACING
    print(" Breakout Groups ".center(total_width, "="))
    row = "SAC".ljust(HEAD_SPACING) 
    for sac in sessions.sacs:
        row += f"| {get_name(sac)}".ljust(SPACING)
    print(row)
    for i in range(sessions.num_sessions):
        print("-" * total_width)
        # Papers.
        overflow = []
        row = f"Session {i+1}".ljust(HEAD_SPACING)
        for sac in sessions.sacs:
            data = sessions.get_by_key(sac, i)
            papers = [str(p) for p in data.papers]
            if len(papers) > max_papepers_on_line:
                overflow.append(papers[max_papepers_on_line:])
                papers = papers[:max_papepers_on_line]
            else:
                overflow.append([])
            row += f"| {', '.join([str(p) for p in papers])}".ljust(SPACING)
        print(row)
        # Overflow.
        while sum([len(o) for o in overflow]) > 0:
            row = " " * HEAD_SPACING
            for j, papers in enumerate(overflow):
                row += f"| {', '.join([str(p) for p in papers[:max_papepers_on_line]])}".ljust(SPACING)
                overflow[j] = papers[max_papepers_on_line:]
            print(row)

        # ACs.
        ac_list = {sac : sorted(list(sessions.get_by_key(sac,i).acs)) for sac in sessions.sacs}
        max_acs = max([len(ac_list[sac]) for sac in sessions.sacs])
        for j in range(max_acs):
            row = " ".ljust(HEAD_SPACING)
            for sac in sessions.sacs:
                acs = ac_list[sac]
                if j < len(acs):
                    row += f"| {get_name(acs[j])}".ljust(SPACING)
                else:
                    row += "|".ljust(SPACING)
            print(row)
    print("=" * total_width)



def get_affinities(session : Session, affinities, include_sac_affinities=True):
    # Get the affinities for a given session.
    affs = [affinities[paper_no].get(ac, np.nan) for paper_no in session.papers for ac in session.acs]
    if include_sac_affinities:
        affs.extend([affinities[paper_no].get(sac, np.nan) for paper_no in session.papers for sac in session.sacs])
    return affs


def analyze_breakout_groups(sessions : Sessions, affinities, sac_assignments, include_sac_affinities=True):
    # analyze the breakout groups.
    print(" Breakout Session Overview ".center(80, "="))

    # TODO: At some point maybve factor out.
    aff = [] # all affinities
    sessions_scores = []
    ac_affs = {}
    paper_affs = {}
    for sess in sessions.sessions:
        local_affs = get_affinities(sess, affinities, include_sac_affinities)
        if not np.all(np.isnan(local_affs)):
            sessions_scores.append(np.nanmean(local_affs))
            aff.extend(local_affs)
        # TODO: Not pretty.
        for paper_no in sess.papers:
            for ac in sess.acs:
                if paper_no not in paper_affs:
                    paper_affs[paper_no] = []
                if ac not in ac_affs:
                    ac_affs[ac] = []
                affinty = affinities[paper_no].get(ac, None)
                if affinty is not None:
                    paper_affs[paper_no].append(affinty)
                    ac_affs[ac].append(affinty)
    ac_affs =[np.nanmean(affs) for affs in ac_affs.values() if not np.all(np.isnan(affs))]
    paper_affs = [np.nanmean(affs) for affs in paper_affs.values() if not np.all(np.isnan(affs))]
    print("Individual affinity scores:")
    print(f"- Min: {np.nanmin(aff):.02f}")
    print(f"- Max: {np.nanmax(aff):.02f}")
    print(f"- Mean: {np.nanmean(aff):.02f}")
    print(f"- Median: {np.nanmedian(aff):.02f}")
    print("Mean affinity by session:")
    print(f"- Min: {np.nanmin(sessions_scores):.02f}")
    print(f"- Max: {np.nanmax(sessions_scores):.02f}")
    print(f"- Mean: {np.nanmean(sessions_scores):.02f}")
    print(f"- Median: {np.nanmedian(sessions_scores):.02f}")
    print("Mean affinity by paper:")
    print(f"- Min: {np.nanmin(paper_affs):.02f}")
    print(f"- Max: {np.nanmax(paper_affs):.02f}")
    print(f"- Mean: {np.nanmean(paper_affs):.02f}")
    print(f"- Median: {np.nanmedian(paper_affs):.02f}")
    print("Mean affinity by AC:")
    print(f"- Min: {np.nanmin(ac_affs):.02f}")
    print(f"- Max: {np.nanmax(ac_affs):.02f}")
    print(f"- Mean: {np.nanmean(ac_affs):.02f}")
    print(f"- Median: {np.nanmedian(ac_affs):.02f}")

    # Balance of papers to sessions.
    stats = compute_group_assignment_stats(sessions)
    titles = {"papers_per_session" : "Num Papers per Session", "acs_per_session" : "Num ACs per Session"
             , "sessions_per_ac" : "Num Sessions per AC"}
    
    for key, title in titles.items():
        print(f"{title}:")
        print_stat(stats[key])

    # SAC matching.
    sacs_matched = []
    for session in sessions.sessions:
        # Assume single SAC
        sacs_matched.extend([sac_assignments[p] == list(session.sacs)[0] for p in session.papers if p in sac_assignments])
    print(f"SACs matched: {sum(sacs_matched)}/{len(sacs_matched)} ({sum(sacs_matched)/len(sacs_matched)*100:.1f}%)")

def analyze_assignments(assignments, affinities):
    ass = {paper_no: ac for paper_no, ac in assignments.items() if ac is not None}
    load = {ac: 0 for ac in assignments.values()}
    for ac in ass.values():
        load[ac] += 1
    aff =[affinities[paper_no].get(ac,0) for paper_no,ac in ass.items()]
    print(" Secondary AC Assignment Overview ".center(80, "="))
    print(f"Total papers: {len(assignments)}")
    print(f"Total ACs: {len(load)}")
    print(f"Load:")
    print(f"- Min: {min(load.values())}")
    print(f"- Max: {max(load.values())}")
    print(f"- Mean: {sum(load.values())/len(load):.2f}")
    print(f"- Median: {sorted(load.values())[len(load)//2]}")
    print(f"Affinity:")
    print(f"- Min: {min(aff):.2f}")
    print(f"- Max: {max(aff):.2f}")
    print(f"- Mean: {sum(aff)/len(aff):.2f}")
    print(f"- Median: {sorted(aff)[len(aff)//2]}")


def plot_breakout_groups(matchings, affinities, include_sac_affinities=True, subplots = None, bins=50, labels=None, colors=None):
    # Gather all data.
    if isinstance(matchings, Sessions):
        matchings = [matchings]
    if labels is None:
        labels = [f"Solution {k+1}" for k in range(len(matchings))]
    if colors is None:
        colors =['b', 'g', 'r', 'c', 'm', 'y', 'k']

    data = []
    for sessions in matchings:
        session_affs = {}
        ac_affs = {}
        sac_affs = {}
        paper_affs = {}
        for j, sess in enumerate(sessions.sessions):
            sess_affs = []
            for paper_no in sess.papers:
                for ac in sess.acs:
                    if paper_no not in paper_affs:
                        paper_affs[paper_no] = []
                    if ac not in ac_affs:
                        ac_affs[ac] = []
                    affinty = affinities[paper_no].get(ac, 0)
                    paper_affs[paper_no].append(affinty)
                    ac_affs[ac].append(affinty)
                    sess_affs.append(affinty)
                if include_sac_affinities:
                    for sac in sess.sacs:
                        if sac not in sac_affs:
                            sac_affs[sac] = []
                        affinty = affinities[paper_no].get(sac, 0)
                        paper_affs[paper_no].append(affinty)
                        sac_affs[sac].append(affinty)
                        sess_affs.append(affinty)
            session_affs[j] = sess_affs
        data.append({'session': session_affs, 'paper': paper_affs, 'ac': ac_affs, 'sac': sac_affs})
    
    # Plot the affinity scores.
    if subplots is None:
        plt.figure(figsize=(20, 12))
    group_name = ["Session", "Paper", "AC", "SAC"]
    fun_name = ["Min", "Mean", "Median", "Max"]
    bins = np.linspace(0, 1, bins)
    for i, group in enumerate(['session', 'paper', 'ac', 'sac']):
        for j, fun in enumerate([np.min, np.mean, np.median, np.max]):
            index = j*4+i+1
            if subplots is None:
                plt.subplot(len(group_name), len(fun_name),index)
            else:
                plt.subplot(subplots[index][0], subplots[index][1], subplots[index][2])
            plt.xlim(0, 1)
            for k, d in enumerate(data):
                vals = [fun(affs) if len(affs) >0 else 0 for affs in d[group].values()]
                plt.axvline(np.mean(vals), color=colors[k], linestyle='-', linewidth=2, alpha=1.0, label=None)
                plt.hist(vals, bins=bins, alpha=0.5, color=colors[k], edgecolor='black')
            plt.xlabel(f"{fun_name[j]} Affinity Scores")
            plt.ylabel(f"Number of {group_name[i]}s")
            plt.title(f"{fun_name[j]} Affinity Scores by {group_name[i]}")

            if len(labels) > 1:
                plt.legend(labels)

    if subplots is None:
        plt.tight_layout()
        plt.show()
    
def plot_assignments(matchings, secondary_ac_assignments, ac_assignments, sac_assignments, affinities, all_acs, bins=50, labels=None, colors=None):
    # Plot the assignment loads. matchings and secondary_ac_assignments are lists of solutions, the rest is constant.
    plt.figure(figsize=(18, 10))
    bins = np.linspace(0, 1, bins)
    if colors is None:
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    if labels is None:
        labels = [f"Solution {i+1}" for i in range(len(matchings))]

    def plot_by_paper(assignments, color):
        vals = [affinities[p].get(ac, 0) for p, ac in assignments.items()]
        plt.hist(vals, bins=bins, color=color, edgecolor='black', alpha=0.5)
        plt.axvline(np.mean(vals), color=color, linestyle='-', linewidth=2, alpha=1.0, label=None)
        plt.xlim(0, 1)
        plt.xlabel("Affinity Score")
        plt.ylabel("Number of Papers")
        if len(labels) > 1:
            plt.legend(labels)

    def plot_by_ac(assignments, color):
        acs = set(assignments.values())
        vals =[ np.mean([affinities[p].get(a, 0) for p, a in assignments.items() if a == ac]) for ac in acs]
        plt.hist(vals, bins=bins, color=color, edgecolor='black', alpha=0.5)
        plt.axvline(np.mean(vals), color=color, linestyle='-', linewidth=2, alpha=1.0, label=None)
        plt.xlim(0, 1)
        plt.xlabel("Mean Affinity Score")
        plt.ylabel("Number of ACs")
        if len(labels) > 1:
            plt.legend(labels)

    # Plot the affinity scores.
    plt.subplot(2, 4, 1)
    plt.title("Primary AC Affinity Scores by Paper")
    plot_by_paper(ac_assignments, 'k')

    plt.subplot(2, 4, 5)
    plt.title("Primary AC Affinity Scores by AC")
    plot_by_ac(ac_assignments, 'k')

    # Plot the secondary AC affinities.
    plt.subplot(2, 4, 2)
    plt.title("Secondary AC Affinity Scores by Paper")
    for i, assignments in enumerate(secondary_ac_assignments):
        plot_by_paper(assignments, colors[i])
    
    plt.subplot(2, 4, 6)
    plt.title("Secondary AC Affinity Scores by AC")
    for i, assignments in enumerate(secondary_ac_assignments):
        plot_by_ac(assignments, colors[i])

    # Plot the SAC affinities.
    plt.subplot(2, 4, 3)
    plt.title("SAC Affinity Scores by Paper")
    sac_data=[]
    for i, sessions in enumerate(matchings):
        assignments={}
        for session in sessions.sessions:
            sac = list(session.sacs)[0] # Assumes single SAC
            if sac == "Standout":
                continue
            for p in session.papers:
                assignments[p] = sac
        sac_data.append(assignments)
        plot_by_paper(assignments, colors[i])

    plt.subplot(2, 4, 7)
    plt.title("SAC Affinity Scores by AC")
    for i, assignments in enumerate(sac_data):
        plot_by_ac(assignments, colors[i])

    # Plot the Secondary AC Loads.
    plt.subplot(2, 4, 4)
    plt.title("Secondary AC Load")
    for i, assignments in enumerate(secondary_ac_assignments):
        loads = [np.sum([ac == a for _, ac in assignments.items()]) for a in all_acs]
        x= np.arange(np.min(loads), np.max(loads)+1, 1)
        plt.bar(x, [np.sum([l == xx for l in loads]) for xx in x], width=0.8, alpha=0.5, color=colors[i], edgecolor='black')
        plt.axvline(np.mean(loads), color=colors[i], linestyle='-', linewidth=2, alpha=1.0, label=None)
    # plt.xlim(np.min(loads), np.max(loads))
    # plt.xticks()
    plt.xlabel("Secondry AC Load")
    plt.ylabel("Number of ACs")
    if len(labels) > 1:
        plt.legend(labels)

    # Number of SACs matched.
    plt.subplot(2, 4, 8)
    plt.title("SACs Matched")
    # Bar plot showing the percentage of papers matched with the correct SAC
    num_matched = []
    for i, sessions in enumerate(matchings):
        matched_papers = 0
        for session in sessions.sessions:
            sac = list(session.sacs)[0]  # Assumes single SAC
            matched_papers += sum([1 for p in session.papers if sac_assignments.get(p) == sac])
        num_matched.append(matched_papers)
                
    plt.bar(labels, num_matched, color=colors, edgecolor='black', alpha=0.7)
    plt.ylabel("Papers correctly matched with SAC")
    plt.legend()

    plt.tight_layout()
    plt.show()

def plot_optimization_stats(stats, subplot = None):
    stats = dict(sorted(stats.items()))
    it = list(stats.keys())
    num_papers = [s.num_papers for s in stats.values()]
    num_ac = [s.num_secondary_acs for s in stats.values()]
    scores = [s.energy for s in stats.values()]

    if subplot is None:
        plt.figure(figsize=(12, 6))
    else:
        plt.subplot(subplot[0], subplot[1], subplot[2])
    plt.plot(it, scores, color='r', label='Energy')
    plt.xlabel("Iteration")
    plt.ylabel("Energy")
    plt.scatter(it, scores, color='r')
    plt.twinx()
    plt.plot(it, num_papers, color='b', label='Papers')
    plt.plot(it, num_ac, color='g', label='Secondary ACs')
    plt.ylabel("Number of Papers")
    plt.title("Optimization Stats")
    plt.legend()
    if subplot is None:
        plt.tight_layout()
        plt.show()

def plot_ac_sessions(sessions : Sessions, subplots=None):
    stats = compute_group_assignment_stats(sessions)
    plt.figure(figsize=(12, 6))
    if subplots is None:
        plt.subplot(1, 2, 1)
    else:
        plt.subplot(subplots[0][0], subplots[0][1], subplots[0][2])
    plt.hist(stats["acs_per_session"], bins=30)
    plt.xlabel("Number of ACs per Session")
    plt.ylabel("Number of Sessions")
    plt.title("ACs per Session")

    if subplots is None:
        plt.subplot(1, 2, 2)
    else:
        plt.subplot(subplots[1][0], subplots[1][1], subplots[1][2])
    plt.hist(stats["sessions_per_ac"].values(), bins=30)
    plt.xlabel("Number of Sessions per AC")
    plt.ylabel("Number of ACs")
    plt.title("Sessions per AC")
    if subplots is None:
        plt.tight_layout()
        plt.show()
