import csv
import os
from utils.paths import ROOT_DIR
from REV_ratings import RATINGS
import shutil

RATINGS_PATH = os.path.join(ROOT_DIR, "private", "review_ratings.csv")
OUTPUT_PATH = os.path.join(ROOT_DIR, "private", "submission_pdfs")
rating_to_int = {v: k for k, v in RATINGS.items()}


def main():
    with open(RATINGS_PATH, "r") as f:
        reader = csv.DictReader(f)
        ratings = {
            int(row["Paper No"]): {
                "first_round": row["First Round Decision"],
                "meta_review": row["Meta Review"],
                "ac_decision": row["AC Decision"],
                "acm_rating": row["AC Meeting Recommendation"],
            }
            for row in reader
        }
    print(f"Found {len(ratings)} ratings.")

    # Compute decisions.
    for data in ratings.values():
        if data["first_round"] == "Rejected":
            # Rejected first round.
            data["final_decision"] = "Reject"
            data["round"] = "first"
        elif not data["acm_rating"]:
            # Not disucssed at AC meeting.
            if data["ac_decision"] != "Discuss":
                data["final_decision"] = data["ac_decision"]
                data["round"] = "second"
            # Values not updated take the meta review value.
            elif rating_to_int[data["meta_review"]] < 4:
                data["final_decision"] = "Reject"
                data["round"] = "second (fallback)"
            else:
                data["final_decision"] = "Accept"
                data["round"] = "second (fallback)"
        else:
            # Discussed at AC meeting.
            if rating_to_int[data["acm_rating"]] < 4:
                data["final_decision"] = "Reject"
            else:
                data["final_decision"] = "Accept"
            data["round"] = "AC meeting"
    for r in ["Accept", "Reject"]:
        print(
            f"- {r}: {len([p for p, d in ratings.items() if d['final_decision'] == r])}"
        )
        for round in ["first", "second", "second (fallback)", "AC meeting"]:
            print(
                f"  - {round}: {len([p for p, d in ratings.items() if d['final_decision'] == r and d['round'] == round])}"
            )

    # Move all papers to acepted or rejected folders.
    for id, data in ratings.items():
        src = os.path.join(OUTPUT_PATH, f"{id:03d}.pdf")
        dest = os.path.join(OUTPUT_PATH, data["final_decision"], f"{id:03d}.pdf")
        shutil.move(src, dest)


if __name__ == "__main__":
    main()
