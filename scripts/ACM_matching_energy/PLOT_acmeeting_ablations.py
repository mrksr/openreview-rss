import pickle
import os
import matplotlib.pyplot as plt
from utils.paths import ROOT_DIR
import numpy as np

USE_SAME_Y = True  # Use the same y-axis for all plots.
USE_X_TIME = True  # Use time as x-axis, otherwise use the number of iterations.
NUM_PAPERS = 144  # Number of papers to be assigned.
FILE = os.path.join(ROOT_DIR, "private", "matching", "ablations_100k.p")


def plot_ablation(methods, names, data, min_y=None, max_y=None):
    """
    Plot a panel of ablation results.
    """
    for i, m in enumerate(methods):
        x = data[m]["it"]
        if USE_X_TIME:
            x = np.array(x) * (data[m]["duration"] / -x[-1])
        y = data[m]["scores"]
        plt.plot(x, y, label=names[i])

    if min_y:
        plt.ylim(bottom=min_y)
    if max_y:
        plt.ylim(top=max_y)
    plt.xlabel("Time [s]" if USE_X_TIME else "Iterations")
    plt.ylabel("Score")
    plt.legend()


def main():
    # Load the ablation results.
    data = {}
    with open(os.path.join(FILE), "rb") as f:
        ablations = pickle.load(f)
        # Parse data format.
        for name, (matching, secondary_acs, stats, duration) in ablations.items():
            solution_found_at = None
            for i in range(len(stats)):
                if (
                    stats[i].best_num_papers == NUM_PAPERS
                    and stats[i].best_num_secondary_acs == NUM_PAPERS
                ):
                    solution_found_at = i
                    break
            data[name] = {}
            data[name]["duration"] = duration
            data[name]["scores"] = [s.best_score for s in stats[solution_found_at:]]
            data[name]["it"] = [s.iteration for s in stats[solution_found_at:]]

    # Plot the results.
    plt.figure(figsize=(16, 10))

    plt.subplot(1, 3, 1)
    plt.title("All")
    methods = [m for m in data]
    plot_ablation(methods, methods, data)

    plt.subplot(2, 3, 2)
    plt.title("Sampling Methods")
    methods = ["importance", "random", "greedy"]
    plot_ablation(methods, methods, data)

    plt.subplot(2, 3, 3)
    plt.title("Random Top-K")
    methods = ["greedy", "random_top3", "random_top5", "random_top10"]
    labels = ["K=1", "K=3", "K=5", "K=10"]
    plot_ablation(methods, labels, data)

    plt.subplot(2, 3, 5)
    plt.title("Importance Top-K")
    methods = ["greedy", "importance_top3", "importance_top5", "importance_top10"]
    labels = ["K=1", "K=3", "K=5", "K=10"]
    plot_ablation(methods, labels, data)

    plt.subplot(2, 3, 6)
    plt.title("Importance Factor")
    methods = [
        "random",
        "importance_f0.5",
        "importance",
        "importance_f2",
        "importance_f3",
        "greedy",
    ]
    labels = ["f=0", "f=0.5", "f=1", "f=2", "f=3", "f=inf"]
    plot_ablation(methods, labels, data)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
