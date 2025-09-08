from utils.setup_client import setup_client
from utils.paths import VENUE
from datetime import datetime
import matplotlib.pyplot as plt


def get_withdrawals(client):
    venue_group = client.get_group(VENUE)
    withdrawn_id = venue_group.content["withdrawn_venue_id"]["value"]
    submissions = client.get_all_notes(
        content={"venueid": withdrawn_id}, details="directReplies"
    )
    print(f"Found {len(submissions)} withdrawals.")
    papers = {}  # timestamp: paper_no
    for note in submissions:
        for reply in note.details["directReplies"]:
            if reply["invitations"][0].endswith("-/Withdrawal"):
                created = datetime.fromtimestamp(reply["tcdate"] / 1000)
                papers[created] = note.number
    return papers


def get_desk_rejected(client):
    submissions = client.get_all_notes(
        invitation=f"{VENUE}/-/Desk_Rejected_Submission", details="directReplies"
    )
    print(f"Found {len(submissions)} desk rejected papers.")
    papers = {}
    for note in submissions:
        for reply in note.details["directReplies"]:
            if reply["invitations"][0].endswith("-/Desk_Rejection"):
                created = datetime.fromtimestamp(reply["tcdate"] / 1000)
                papers[created] = note.number
    return papers


def print_withdrawals(withdrawals):
    for created, number in sorted(withdrawals.items()):
        print(f"{created.strftime('%Y-%m-%d %H:%M:%S')} - Paper {number}")


def print_paper_stats(withdrawals, desk_rejected):
    submission_deadline = datetime(2025, 2, 1, 11, 59, 59)
    # Print number of desk rejected papers before submission deadline.
    print(f"Submission deadline: {submission_deadline}")
    print(f"Desk rejected papers: {len(desk_rejected)}")
    print(
        f"- before deadline: {len([t for t in desk_rejected if t < submission_deadline])}"
    )
    print(
        f"- after deadline: {len([t for t in desk_rejected if t >= submission_deadline])}"
    )
    # Print number of withdrawals before submission deadline.
    print(f"Withdrawals: {len(withdrawals)}")
    print(
        f"- before deadline: {len([t for t in withdrawals if t < submission_deadline])}"
    )
    print(
        f"- after deadline: {len([t for t in withdrawals if t >= submission_deadline])}"
    )


def plot_withdrawals(withdrawals):
    num_withdrawals = {}
    for t in withdrawals:
        num_withdrawals[t.date()] = num_withdrawals.get(t.date(), 0) + 1
    times = sorted(num_withdrawals.keys())
    key_dates = {
        "Abstract": datetime(2025, 1, 18),
        "Submission": datetime(2025, 1, 25),
        "Supplementary": datetime(2025, 2, 1),
        "First Decision": datetime(2025, 3, 18),
        "Rebuttal": datetime(2025, 3, 25),
    }
    key_dates = {k: v.date() for k, v in key_dates.items()}
    all_dates = times + list(key_dates.values())
    xlim = (min(all_dates), max(all_dates))

    # Plot withdrawals on date.
    plt.figure(figsize=(10, 6))
    plt.bar(times, [num_withdrawals[t] for t in times])
    plt.ylabel("Number of withdrawals")
    plt.xlim(xlim)
    plt.xticks(
        [k for k in key_dates.values()],
        [k for k in key_dates.keys()],
        rotation=90,
        color="r",
    )

    # Plot cumulative withdrawals.
    cum_withdrawals = []
    for t in times:
        cum_withdrawals.append(sum([num_withdrawals[tt] for tt in times if tt <= t]))
    plt.twinx()
    plt.plot(times, cum_withdrawals, color="gray", linestyle="-")
    plt.xlim(xlim)
    plt.ylabel("Total withdrawals")
    plt.xticks(
        [k for k in key_dates.values()],
        [k for k in key_dates.keys()],
        rotation=30,
        color="r",
    )

    for event, key_date in key_dates.items():
        plt.axvline(key_date, color="r", linestyle="--", label=event)
    plt.title("Withdrawals over time")
    plt.tight_layout()
    plt.show()


def main():
    client = setup_client()
    desk_rejected = get_desk_rejected(client)
    withdrawals = get_withdrawals(client)
    print_withdrawals(withdrawals)
    print_paper_stats(withdrawals, desk_rejected)
    plot_withdrawals(withdrawals)


if __name__ == "__main__":
    main()
