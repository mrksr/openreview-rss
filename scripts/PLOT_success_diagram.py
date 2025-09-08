import plotly.graph_objects as go

# Labels
labels = {
    0: "Submissions",
    1: "Withdrawn",
    2: "Received",
    3: "Desk Rejected",
    4: "Reviewed",
    5: "Rejected After Review",
    6: "Invited for Rebuttal",
    7: "Rejected After Rebuttal",
    8: "Accepted After Rebuttal",
    9: "Discussed at Area Chair Meeting",
    10: "Rejected After Area Chair Meeting",
    11: "Accepted After Area Chair Meeting",
    12: "Final Rejected",
    13: "Final Accepted",
}

# Numbers
num_submissions = 768
num_withdrawn = 101
num_desk_rejected = 112
num_rejected_after_review = 147
num_rejected_after_rebuttal = 129
num_accepted_after_rebuttal = 111
num_rejected_acm = 116
num_accepted_acm = 52

num_received = num_submissions - num_withdrawn
num_reviewed = num_received - num_desk_rejected
num_rebuttal = num_reviewed - num_rejected_after_review
num_acm = num_rebuttal - num_rejected_after_rebuttal - num_accepted_after_rebuttal


packets = [
    ("Submissions", "Withdrawn", num_withdrawn, "#cccccc"),
    ("Submissions", "Received", num_received, "#66b3ff"),
    ("Received", "Desk Rejected", num_desk_rejected, "#ff6666"),
    ("Received", "Reviewed", num_reviewed, "#9999ff"),
    ("Reviewed", "Rejected After Review", num_rejected_after_review, "#ff9999"),
    ("Reviewed", "Invited for Rebuttal", num_rebuttal, "#94c3f8"),
    (
        "Invited for Rebuttal",
        "Rejected After Rebuttal",
        num_rejected_after_rebuttal,
        "#ffccaa",
    ),
    (
        "Invited for Rebuttal",
        "Accepted After Rebuttal",
        num_accepted_after_rebuttal,
        "#99ff99",
    ),
    ("Invited for Rebuttal", "Discussed at Area Chair Meeting", num_acm, "#c2c2f0"),
    (
        "Discussed at Area Chair Meeting",
        "Accepted After Area Chair Meeting",
        num_accepted_acm,
        "#99ffcc",
    ),
    (
        "Discussed at Area Chair Meeting",
        "Rejected After Area Chair Meeting",
        num_rejected_acm,
        "#ffdd99",
    ),
    ("Desk Rejected", "Final Rejected", num_desk_rejected, "#ff6666"),
    ("Rejected After Review", "Final Rejected", num_rejected_after_review, "#ff9999"),
    (
        "Rejected After Rebuttal",
        "Final Rejected",
        num_rejected_after_rebuttal,
        "#ffccaa",
    ),
    (
        "Rejected After Area Chair Meeting",
        "Final Rejected",
        num_rejected_acm,
        "#ffdd99",
    ),
    (
        "Accepted After Rebuttal",
        "Final Accepted",
        num_accepted_after_rebuttal,
        "#99ff99",
    ),
    (
        "Accepted After Area Chair Meeting",
        "Final Accepted",
        num_accepted_acm,
        "#99ffcc",
    ),
]

label_to_key = {v: k for k, v in labels.items()}

labels = [
    f" {num_submissions} Submissions",
    f" {num_withdrawn} Withdrawn",
    f" {num_received} Received",
    f" {num_desk_rejected} Desk Rejected",
    f" {num_reviewed} Reviewed",
    f" {num_rejected_after_review} Rejected After Review",
    f" {num_rebuttal} Invited for Rebuttal",
    f" {num_rejected_after_rebuttal} Rejected After Rebuttal",
    f" {num_accepted_after_rebuttal} Accepted After Rebuttal",
    f" {num_acm} Discussed at Area Chair Meeting",
    f" {num_rejected_acm} Rejected After Area Chair Meeting",
    f" {num_accepted_acm} Accepted After Area Chair Meeting",
    f" {num_desk_rejected+num_rejected_after_review + num_rejected_after_rebuttal + num_rejected_acm} Final Rejected",
    f" {num_accepted_acm+num_accepted_after_rebuttal} Final Accepter",
]

fig = go.Figure(
    data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color="black",
            ),
            link=dict(
                source=[label_to_key[p[0]] for p in packets],
                target=[label_to_key[p[1]] for p in packets],
                value=[p[2] for p in packets],
                color=[p[3] for p in packets],
            ),
        )
    ]
)

fig.update_layout(title_text="Success Flow Diagram", font_size=14)
fig.show(renderer="browser")
