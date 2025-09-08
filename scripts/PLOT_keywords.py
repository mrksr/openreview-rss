from matplotlib import pyplot as plt
from AC_status import read_ac_status
from utils.setup_client import setup_client
from utils.paths import VENUE, ROOT_DIR
from utils.parse_notes import is_accepted
import numpy as np
import pickle
import os


def get_ac_keywords(only_primary_kw=False):
    acs = read_ac_status()
    keywords = {}  # keyword: {order : [acs] }
    AC_no_kw = []
    EM_AC_no_kw = []
    for ac in acs:
        if ac["role"] != "Area_Chairs" or ac["decision"] != "Accepted":
            continue
        for i, kw in enumerate(ac["keywords"]):
            no = "emergency" if ac["emergency"] else i
            if kw not in keywords:
                keywords[kw] = {}
            if no not in keywords[kw]:
                keywords[kw][no] = []
            keywords[kw][no].append(ac["id"])

            if only_primary_kw:
                break

        if not ac["keywords"]:
            if ac["emergency"]:
                EM_AC_no_kw.append(ac["id"])
            else:
                AC_no_kw.append(ac["id"])
    print(
        f"Read {len(acs)} ACs. {len(AC_no_kw)} ACs without keywords, {len(EM_AC_no_kw)} emergency ACs without keywords."
    )
    return keywords


def get_sub_keywords(client, only_primary_kw=False):
    # Only 'active' submissions
    submissions = client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})

    keywords = {}
    num_kws = [0] * 4
    for sub in submissions:
        paper_nr = sub.number
        paper_kw = sub.content["keywords"]["value"]
        num_kws[np.min([len(paper_kw) - 1, 3])] += 1
        for i, kw in enumerate(paper_kw):
            if kw not in keywords:
                keywords[kw] = {}
            if i not in keywords[kw]:
                keywords[kw][i] = []
            keywords[kw][i].append(paper_nr)

            if only_primary_kw:
                break

    print(f"Read {len(submissions)} submissions. Papers with N keywords:")
    for i in range(4):
        print(f"  {i+1}{'+' if i==3 else ''}: {num_kws[i]}")
    return keywords


def plot_ac_vs_sub_kws(keywords, ac_kw, sub_kw):
    colors = ["b", "lawngreen", "gold", "lightgray", "r"]
    x = np.arange(len(keywords))
    plt.figure(figsize=(10, 12))

    # Format data to table.
    for plot_no, data in enumerate([ac_kw, sub_kw]):
        vals = np.zeros((len(keywords), 5))
        plt.subplot(2, 1, plot_no + 1)
        for i, kw in enumerate(keywords):
            if kw not in data:
                continue
            for j in data[kw]:
                if j == "emergency":
                    vals[i, 4] = len(data[kw][j])
                else:
                    vals[i, int(np.min([j, 3]))] = len(data[kw][j])

        # Plot data.
        current = np.zeros(len(keywords))
        for i in range(5):
            plt.bar(x, vals[:, i], color=colors[i], bottom=current)
            current += vals[:, i]
        plt.ylabel(f"Number of {['ACs', ''][plot_no]}")
        plt.xticks(x, [])

        # Also print the raw data.
        print(
            f"{(['AC', 'Submission'][plot_no]+' Keywords'):<90}{'First':<8}{'Second':<8}{'Third':<8}{'4+':<8}Emergency Total"
        )
        for i, kw in enumerate(keywords):
            print(
                f"{kw:<90}{int(vals[i][0]):<8}{int(vals[i][1]):<8}{int(vals[i][2]):<8}{int(vals[i][3]):<8}{int(vals[i][4]):<10}{int(sum(vals[i]))}"
            )

        # Legend
        if plot_no == 0:
            plt.legend(["First", "Second", "Third", "4+", "Emergency"], ncol=5)
    plt.xticks(x, keywords, rotation=90)
    plt.tight_layout(rect=[0, 0, 1, 1])
    plt.show()


def plot_accepted_kws(
    client, only_first_kw=True, include_rejected=True, lazy=True, horizontal=True
):
    cache_file = os.path.join(ROOT_DIR, "private", "cache", "accepted_keywords.pkl")
    if lazy and os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            paper_kws, keywords, accepted, rejected = pickle.load(f)
    else:
        # Ensure the cache directory exists
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        # Get all keywords.
        paper_kws = {}
        keywords = set()
        notes = client.get_all_notes(
            content={"venueid": f"{VENUE}/Submission"}, details="replies"
        )
        accepted = set()
        rejected = set()
        for paper in notes:
            kws = paper.content["keywords"]["value"]
            paper_kws[paper.number] = kws
            keywords.update(kws)
            if is_accepted(paper):
                accepted.add(paper.number)
            else:
                rejected.add(paper.number)
        keywords = sorted(list(keywords), reverse=True)

        # Save to cache
        with open(cache_file, "wb") as f:
            pickle.dump((paper_kws, keywords, accepted, rejected), f)

    # Format to rows of plots.
    data = []
    for papers in [accepted, rejected] if include_rejected else [accepted]:
        kw_data = {kw: 0 for kw in keywords}
        for p in papers:
            for kw in paper_kws[p]:
                kw_data[kw] += 1
                if only_first_kw:
                    break
        data.append(np.array([kw_data[kw] for kw in keywords]))

    colors = ["deepskyblue", "lightgray"]
    plt.figure(figsize=(15, 12) if horizontal else (12, 15))
    plt.rcParams.update({"font.size": 18})
    ax = plt.gca()

    # Sort keywords and data by accepted count (first row in data)
    sort_data = data[0].copy()
    if include_rejected:
        sort_data += data[1]
    if not horizontal:
        sort_data = -sort_data
    sort_idx = np.argsort(sort_data)
    sorted_keywords = [keywords[i] for i in sort_idx]
    sorted_data = [d[sort_idx] for d in data]

    # Stacked vertical bar plot.
    x = np.arange(len(sorted_keywords))
    current_bottom = np.zeros(len(sorted_keywords))
    num_papers = 0
    for i, kw_data in enumerate(sorted_data):
        if horizontal:
            p = plt.barh(x, kw_data, color=colors[i], left=current_bottom, alpha=0.5)
        else:
            p = plt.bar(x, kw_data, color=colors[i], bottom=current_bottom, alpha=0.5)
        num_papers += kw_data
        current_bottom += kw_data
        ax.bar_label(p, fontsize=18, color="black", label_type="center")

    print(sum(num_papers))

    short_labels = {
        "Cognitive Modeling & Knowledge Representation for Robots": "Cognitive Modeling & Knowledge Representation",
        "Field Robotics (e.g., Aerial, Agricultural, Construction, Space, Underwater Robotics)": "Field Robotics",
    }
    if horizontal:
        plt.yticks(x, [short_labels.get(kw, kw) for kw in sorted_keywords])
        plt.xlabel("Number of Papers")
    else:
        plt.xticks(x, [short_labels.get(kw, kw) for kw in sorted_keywords], rotation=90)
        plt.ylabel("Number of Papers")
    if include_rejected:
        plt.legend(["Accepted", "Rejected"])
    plt.title(
        ("Primary Keyword" if only_first_kw else "All Keywords")
        + (" of Accepted Papers" if not include_rejected else "")
    )
    plt.tight_layout(rect=[0, 0, 1, 1])
    plt.show()


def main():
    client = None
    # client = setup_client()
    # kw = json.load(open("data/keywords.json"))
    # only_primary_kw = False
    # ac_kw = get_ac_keywords(only_primary_kw)
    # sub_kw = get_sub_keywords(client, only_primary_kw)
    # plot_ac_vs_sub_kws(kw, ac_kw, sub_kw)

    plot_accepted_kws(client, only_first_kw=True, include_rejected=True, lazy=True)


if __name__ == "__main__":
    main()
