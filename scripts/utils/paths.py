import git

VENUE = "roboticsfoundation.org/RSS/2025/Conference"
TEST_VENUE = "roboticsfoundation.org/RSS/2025/Test"


def get_root_dir():
    git_repo = git.Repo(__file__, search_parent_directories=True)
    git_root = git_repo.git.rev_parse("--show-toplevel")
    return git_root


ROOT_DIR = get_root_dir()
