from utils.setup_client import setup_client
from utils.paths import VENUE
from utils.messaging import Emails, deadline_reminder, signature
from AC_status import read_ac_status
from datetime import datetime


"""
Read a list of ACs and their status from a CSV file and send expertise selection reminders.
"""


def send_bid_invitation(acs, client):
    mail = Emails()
    mail.subject = "[RSS25] Area Chair Bidding Started"
    mail.message = (
        "Dear {{fullname}},\n\nArea Chair Bidding has now started. You can access the bidding here: https://openreview.net/invitation?id=roboticsfoundation.org/RSS/2025/Conference/Area_Chairs/-/Bid\n\nBidding on papers allows you to express preference and disinclination for papers that you would like to handle or would like to avoid handling. Your bids will be taken into account by the Senior Area Chairs when assigning papers to Area Chairs.\n\nBidding is optional but highly encouraged so your assigned papers fit well with your expertise and invited reviewers.\n\nBidding is open until Jan 26 AoE.\n\n"
        + signature()
    )
    mail.recipients = [ac["id"] for ac in acs]
    mail.send(client)


def send_bid_reminder(acs, client):
    # Get all AC who already bid.
    with_bid = set()
    edges = client.get_grouped_edges(f"{VENUE}/Area_Chairs/-/Bid", groupby="head")
    for edge in edges:
        for val in edge["values"]:
            with_bid.add(val["tail"])

    recipients = [ac["id"] for ac in acs if ac["id"] not in with_bid]

    mail = Emails()
    mail.subject = "[RSS25] Reminder: Area Chair Bidding"
    mail.message = (
        "Dear {{fullname}},\n\nArea Chair Bidding is still open till Jan 26 AoE. You can access the bidding here: https://openreview.net/invitation?id=roboticsfoundation.org/RSS/2025/Conference/Area_Chairs/-/Bid\n\nBidding on papers allows you to express preference and disinclination for papers that you would like to handle or would like to avoid handling. Your bids will be taken into account by the Senior Area Chairs when assigning papers to Area Chairs.\n\nBidding is optional but highly encouraged so your assigned papers fit well with your expertise and invited reviewers.\n\nBidding is still open until Jan 26 AoE.\n\n"
        + signature()
    )
    mail.recipients = recipients
    mail.send(client)


def filter_acs(acs):
    # Filter out ACs that are not accepted and senior acs.
    return [
        ac for ac in acs if ac["role"] == "Area_Chairs" and ac["decision"] == "Accepted"
    ]


def main():
    client = setup_client()
    acs = read_ac_status()
    acs = filter_acs(acs)
    # send_bid_invitation(acs, client)
    send_bid_reminder(acs, client)


if __name__ == "__main__":
    main()
