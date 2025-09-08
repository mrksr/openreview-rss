from utils.paths import VENUE


def get_decision(note):
    for r in note.details["replies"]:
        if f"{VENUE}/Submission{note.number}/-/Decision" in r["invitations"]:
            # Decisions are unique.
            return r["content"]["decision"]["value"]
    return None


def is_accepted(note):
    for r in note.details["replies"]:
        if f"{VENUE}/Submission{note.number}/-/Decision" in r["invitations"]:
            # Decision.
            decision = r["content"]["decision"]["value"]
            if decision == "Rejected":
                return False
            elif decision == "Accepted":
                return True
    return None


def get_reviews(note):
    reviews = []
    for r in note.details["replies"]:
        if f"{VENUE}/Submission{note.number}/-/Official_Review" in r["invitations"]:
            reviews.append(r)
    return reviews


def get_meta_reviews(note):
    meta_reviews = []
    for r in note.details["replies"]:
        if f"{VENUE}/Submission{note.number}/-/Meta_Review" in r["invitations"]:
            meta_reviews.append(r)
    return meta_reviews
