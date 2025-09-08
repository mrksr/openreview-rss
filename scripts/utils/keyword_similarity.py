KW_WEIGHTS = [1.0, 0.75, 0.5, 0.25]  # Weights for first, second, third and 4+ keywords.


def keyword_similarity(kw_1: list, kw_2: list):
    """
    Compute the similarity between two lists of keywords.

    Parameters
    ----------
    kw_1 : list of str
        List of keywords ofthe source.
    kw_2 : list of str
        List of keywords to compare to.

    Returns
    -------
    float
        Similarity between the two lists of keywords.
    """
    kws = set(kw_1).intersection(kw_2)
    return sum(
        [
            KW_WEIGHTS[min(kw_1.index(kw), 3)] * KW_WEIGHTS[min(kw_2.index(kw), 3)]
            for kw in kws
        ]
    )


def test():
    # Perfect 3-kw match.
    kws_1 = ["robotics", "perception", "control"]
    kws_2 = ["robotics", "perception", "control"]
    assert keyword_similarity(kws_1, kws_2) == 1.8125

    # Much overlap.
    kws_1 = ["robotics", "perception", "control", "planning"]
    kws_2 = ["robotics", "control", "planning", "manipulation"]
    assert keyword_similarity(kws_1, kws_2) == 1.5

    # First overlap.
    kws_1 = ["robotics", "perception", "control", "planning"]
    kws_2 = ["robotics", "learning"]
    assert keyword_similarity(kws_1, kws_2) == 1.0

    # Long list, low overlap.
    kws_1 = ["robotics", "perception", "control", "planning", "learning"]
    kws_2 = ["control", "learning"]
    assert keyword_similarity(kws_1, kws_2) == 0.6875

    # No overlap.
    kws_1 = ["robotics", "perception", "control", "planning", "learning"]
    kws_2 = ["manipulation", "vision"]
    assert keyword_similarity(kws_1, kws_2) == 0.0
    print("All tests passed!")


if __name__ == "__main__":
    test()
