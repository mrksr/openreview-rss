from utils.setup_client import setup_client
from utils.paths import VENUE
from utils.messaging import is_openreview_id
import openreview


def get_max_papers(client):
    max_papers = {}  # reviewer_id: max_papers
    for edge in client.get_grouped_edges(
        f"{VENUE}/Reviewers/-/Custom_Max_Papers", groupby="tail"
    ):
        for val in edge["values"]:
            rev_id = val["tail"]
            max_papers[rev_id] = val["weight"]
    print(f"Found {len(max_papers)} custom max papers assignments.")
    return max_papers


def set_max_papers(client, current_max_papers):
    # Set max papers for all reviewers that don't have a max to 4.
    edges = []
    skipped = 0
    for rev in client.get_group(f"{VENUE}/Reviewers").members:
        if not is_openreview_id(rev):
            skipped += 1
            continue

        if rev in current_max_papers:
            continue

        edges.append(
            openreview.api.Edge(
                invitation=f"{VENUE}/Reviewers/-/Custom_Max_Papers",
                head=f"{VENUE}/Reviewers",
                tail=rev,
                signatures=[f"{VENUE}/Program_Chairs"],
                weight=4,
            )
        )
    print(f"Skipped {skipped} non-openreview ids.")
    print(f"Setting {len(edges)} max papers to 4.")
    client.post_edges(edges)


def main():
    client = setup_client()
    current_max_papers = get_max_papers(client)
    set_max_papers(client, current_max_papers)


if __name__ == "__main__":
    main()
