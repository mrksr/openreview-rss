from utils.setup_client import setup_client
from utils.paths import ROOT_DIR, VENUE
from utils.parse_notes import is_accepted
from utils.messaging import is_email_address
import os
import pickle
import openreview
from matplotlib import pyplot as plt
import numpy as np
from collections import Counter


CACHE_FILE = os.path.join(ROOT_DIR, "private", "cache", "region_data.p")
PRIVATE_DATA_FILE = os.path.join(ROOT_DIR, "private", "additional_region_data.p")

# Regions
COUNTRIES = [
    "AE",
    "AF",
    "AL",
    "AM",
    "AT",
    "AU",
    "BR",
    "CA",
    "CH",
    "CN",
    "CZ",
    "DE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HK",
    "IL",
    "IN",
    "IT",
    "JP",
    "KR",
    "NL",
    "RS",
    "SE",
    "SG",
    "TH",
    "TW",
    "US",
    "PT",
    "TR",
    "BE",
    "VN",
    "PL",
    "RU",
    "LK",
    "BG",
]

COUNTRY_TO_CONTINENT = {
    "AF": "Asia",
    "AE": "Asia",
    "AL": "Europe",
    "AM": "Asia",
    "AT": "Europe",
    "AU": "Oceania",
    "BR": "South America",
    "CA": "North America",
    "CH": "Europe",
    "CN": "Asia",
    "CZ": "Europe",
    "DE": "Europe",
    "ES": "Europe",
    "FI": "Europe",
    "FR": "Europe",
    "GB": "Europe",
    "GR": "Europe",
    "HK": "Asia",
    "IL": "Asia",
    "IN": "Asia",
    "IT": "Europe",
    "JP": "Asia",
    "KR": "Asia",
    "NL": "Europe",
    "RS": "Europe",
    "SE": "Europe",
    "SG": "Asia",
    "TH": "Asia",
    "TW": "Asia",
    "US": "North America",
    "PT": "Europe",
    "TR": "Asia",
    "BE": "Europe",
    "VN": "Asia",
    "PL": "Europe",
    "RU": "Europe",
    "LK": "Asia",
    "BG": "Europe",
}

CONTINENT_COLORS = {
    "North America": "#4DAF4A",  # Green
    "Asia": "#E41A1C",  # Red
    "Europe": "#377EB8",  # Blue
    "Oceania": "#984EA3",  # Purple
    "South America": "#FF7F00",  # Orange
    "Africa": "#FFFF33",  # Yellow
    "Unknown": "#B0B0B0",  # Gray for unknown
}

AFFILIATION_TO_COUNTRY = {}  # email domain: country
OVERRIDE_FIRST_AUTHORS = {}  # paper_no: country
OVERRIDE_LAST_AUTHORS = {}  # paper_no: country


def get_region(profile):
    history = profile.content.get("history", [])
    if not history:
        return None
    return history[0]["institution"].get("country", None)


def read_papers(client, only_accepted=True, lazy=True):
    # Lazy loading of data.
    if lazy and os.path.exists(CACHE_FILE):
        print(f"Loading cached data from '{CACHE_FILE}'...")
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)

    # ID, authors, affiliation, titles.
    submissions = client.get_all_notes(
        content={"venueid": f"{VENUE}/Submission"}, details="replies"
    )
    data = {}  # {paper_no: regions: list, accepted: bool}

    print("Reading regional data...")
    for sub in submissions:
        # Only accepted papers.
        paper_nr = sub.number
        accepted = is_accepted(sub)
        if only_accepted and not accepted:
            continue

        author_ids = sub.content["authorids"]["value"]
        profiles = openreview.tools.get_profiles(client, author_ids)
        regions = []
        for p in profiles:
            region = get_region(p)
            if region is None:
                # If no region found, use the email domain as a fallback.
                region = p.content["emailsConfirmed"][0].split("@")[-1]
            regions.append(region)

        if len(regions) != len(author_ids):
            print(
                f"Warning: Mismatch in author IDs {len(author_ids)} and regions {len(regions)} for paper {paper_nr}."
            )
        data[paper_nr] = {"regions": regions, "accepted": accepted}

    print(f"Found {len(data)} papers.")
    print(f"Caching data to '{CACHE_FILE}'...")
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)

    return data


def fix_data(data):
    for paper_no, d in data.items():
        for i, region in enumerate(d["regions"]):
            if region in AFFILIATION_TO_COUNTRY:
                d["regions"][i] = AFFILIATION_TO_COUNTRY[region]

        # Fix some known issues with authors.
        if paper_no in OVERRIDE_FIRST_AUTHORS:
            d["regions"][0] = OVERRIDE_FIRST_AUTHORS[paper_no]
        if paper_no in OVERRIDE_LAST_AUTHORS:
            d["regions"][-1] = OVERRIDE_LAST_AUTHORS[paper_no]


def get_slice(data, only_accepted=True, first_author=True):
    index = 0 if first_author else -1  # Otherwise last author.
    countries = [
        d["regions"][index] for d in data.values() if not only_accepted or d["accepted"]
    ]
    countries = [c if c is not None else "Unknown" for c in countries]
    continents = [COUNTRY_TO_CONTINENT.get(c, "Unknown") for c in countries]
    return countries, continents


def plot_distribution(values):
    sorted_items = sorted(Counter(values).items(), key=lambda x: x[1], reverse=True)
    labels = [item[0] for item in sorted_items]
    counts = np.array([item[1] for item in sorted_items])
    continents = [COUNTRY_TO_CONTINENT.get(c, c) for c in labels]
    colors = [CONTINENT_COLORS[c] for c in continents]
    bars = plt.bar(labels, counts, color=colors)

    # Create legend for continents
    unique_continents = sorted(
        set(continents),
        key=lambda x: (list(CONTINENT_COLORS.keys()).index(x)),
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=CONTINENT_COLORS[cont])
        for cont in unique_continents
    ]
    plt.legend(handles, unique_continents)
    plt.ylabel("Number of Papers")
    plt.semilogy()


def load_additional_data():
    if not os.path.exists(PRIVATE_DATA_FILE):
        print(
            f"Private data file '{PRIVATE_DATA_FILE}' does not exist, no efxtra data loaded."
        )

    with open(PRIVATE_DATA_FILE, "rb") as f:
        global AFFILIATION_TO_COUNTRY, OVERRIDE_FIRST_AUTHORS, OVERRIDE_LAST_AUTHORS
        AFFILIATION_TO_COUNTRY, OVERRIDE_FIRST_AUTHORS, OVERRIDE_LAST_AUTHORS = (
            pickle.load(f)
        )
    print(
        f"Loaded {len(AFFILIATION_TO_COUNTRY)} affiliations, "
        f"{len(OVERRIDE_FIRST_AUTHORS)} first author overrides, "
        f"{len(OVERRIDE_LAST_AUTHORS)} last author overrides from '{PRIVATE_DATA_FILE}'."
    )


def main():
    # Setup and load data.
    client = setup_client()
    load_additional_data()
    data = read_papers(client, only_accepted=False, lazy=True)
    fix_data(data)

    # Plotting the data.
    plt.figure(figsize=(15, 10))

    # Accepted papers by region
    countries, continents = get_slice(data, only_accepted=True, first_author=True)
    plt.subplot(2, 2, 1)
    plot_distribution(countries)
    plt.title("Distribution of Accepted Papers by Country")

    plt.subplot(2, 2, 2)
    plt.title("Distribution of Accepted Papers by Continent")
    plot_distribution(continents)

    # Submitted
    countries, continents = get_slice(data, only_accepted=False, first_author=True)
    plt.subplot(2, 2, 3)
    plot_distribution(countries)
    plt.title("Distribution of Submitted Papers by Country")
    plt.xticks(rotation=90)

    plt.subplot(2, 2, 4)
    plt.title("Distribution of Submitted Papers by Continent")
    plot_distribution(continents)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
