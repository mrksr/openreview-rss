from utils.setup_client import setup_client

# from utils.paths import VENUE
from utils.desk_reject import VENUE
from utils.desk_reject import DeskReject


CONFIRMATION_FIELDS = [
    "confirmation_of_submission_requirements",
    "additional_requirements_for_demo_papers",
    "additional_requirements_for_science_or_systems_papers",
]

REQUIREMENTS = {
    "Science/Systems Paper": [
        "I have carefully read the submission instructions and prepared my paper accordingly.",
        'I have included a "Limitations" section in my paper.',
        "This work contains novel research that was not previously published or submitted elsewhere.",
        "I have anonymized my paper for double blind review.",
        "There are no external links in my paper.",
    ],
    "Demo": [
        "I have carefully read the submission instructions and prepared my paper accordingly.",
        'I have included a "Limitations" section in my paper.',
        "This work contains novel research that was not previously published or submitted elsewhere.",
        'The title of my demo paper starts with "Demonstrating" (e.g. "Demonstrating Large Language Models on Robots").',
    ],
}


def get_all_submissions(client):
     # Only 'active' submissions
    return client.get_all_notes(content={"venueid": f"{VENUE}/Submission"})


def check_submissions(submissions):
    data = {}  # ID: {category, missing_confirmations, has_pdf, id}
    for sub in submissions:
        paper_nr = sub.number
        category = sub.content["category"]["value"]
        confirmations = set()
        for field in CONFIRMATION_FIELDS:
            confirmations.update(sub.content.get(field, {"value": []})["value"])

        data[paper_nr] = {
            "category": category,
            "missing_confirmations": [
                c for c in REQUIREMENTS[category] if c not in confirmations
            ],
            "has_pdf": sub.content.get("pdf", {}).get("value") is not None,
            "id": sub.id,
        }

    print(f"Checked {len(submissions)} submissions.")
    return data


def print_submission_stats(check_data, print_missing=False):
    categories = ["Science/Systems Paper", "Demo"]
    complete = {c: set() for c in categories}
    incomplete = {c: set() for c in categories}
    no_pdf = {c: set() for c in categories}
    for id, data in check_data.items():
        if data["has_pdf"] is False:
            no_pdf[data["category"]].add(id)
        elif len(data["missing_confirmations"]) > 0:
            incomplete[data["category"]].add(id)
            # Print all papers missing confirmations.
            if print_missing:
                print(
                    f"- {id}: misses {len(data['missing_confirmations'])} ({', '.join(data['missing_confirmations'])})"
                )
        else:
            complete[data["category"]].add(id)

    # Print Summary.
    print(f"{'Type':<30}{'Complete':<10}{'No PDF':<10}{'Incomplete':<10}")
    for c in categories:
        print(
            f"{c:<30}{len(complete[c]):<10}{len(no_pdf[c]):<10}{len(incomplete[c]):<10}"
        )
    print(
        f"{'Total':<30}{sum([len(complete[c])for c in categories]):<10}{sum([len(no_pdf[c]) for c in categories]):<10}{sum([len(incomplete[c]) for c in categories]):<10}"
    )


def test_dr():
    dr = DeskReject(setup_client())
    paper_numbers = [2]
    message = "Desk rejected due to missing confirmations."
    dr.reject_papers(paper_numbers, message)


def main():
    client = setup_client()
    submissions = get_all_submissions(client)
    checks = check_submissions(submissions)
    print_submission_stats(checks, print_missing=False)


if __name__ == "__main__":
    main()
    # test_dr()
