# openreview
Python Scripts for OpenReview for RSS 2025.

## Table of Contents
- [**Setup**](#setup)
- [**Running Scripts**](#running-scripts)
    - [Important Disclaimers](#️-important-disclaimers)
    - [Using the Repository](#using-the-repository)

- [**Credits**](#credits)

## Setup

1. Install dependencies:
    ```bash
    pip install openreview-py gitpython tqdm
    ```

2. Clone the repository:
    ```bash
    git clone git@github.com:rssrobotics/openreview.git
    cd openreview
    ```

3. Create a `private/credentials.json` file containing your OpenReview credentials. The access right of this account will determine what the scripts can see.
    ```json
    { "username": "???",
      "password": "???" }
    ```

## Running Scripts

### ⚠️ **Important Disclaimers** 
- These scripts were developed for RSS 2025 and certain file formats (e.g., the committee worksheets etc) that may be specific to RSS 2025.
- The scripts were designed for `openreview-py` `v1.51.2`. Changes in functionality may have occured since then (and already occured during development).
- Many of the scripts **execute actions directly on OpenReview**. While we tried to safeguard sensitive actions always carefully check the scripts you want to run before running, as they may execute **sensitive actions** such as desk rejects or emailing all authors etc.
- Conferences are hectic and many of the scripts perform individual actions and may have been alterated and reworked during development. While we hope they help we do currently not actively maintain the repository.
- As program chair, the credentials of your account will have **super user** power and have access to essentially all and potentially **confidential data**. These scripts will also have that access and power, so make sure no confidential data is made visible or is shared before running.

### Using the Repository 
Please read the disclaimers above first and use at your own risk :)

The scripts are designed to execute individual actions that are useful over the couse of a conference. The repository is structured into the following directories:

```
openreview/
├── scripts/         # Main Python scripts for interacting with OpenReview.
├── data/            # Public data files for the conference.
├── private/         # User-specific credentials and confidential files. Almost all data is read from and written to this directory. This directory is not tracked.
├── msg/             # Messages that are emailed to authors via code or openreview (copy+paste).
├── forms/           # Coniguration options for openreview stages and settings as json.
```

The scripts have a prefix indicating the main topic of functionality, which roughly corresponds to openreview stages.

```
AC   - Area Chair recruitment and setup.
REV  - Reviewer recruitmet, setup, and tracking.
SAC  - Senior Area Chair recruitment and paper assignment (could not yet be handled via native OpenReview).
SUB  - Submissions and introspection.
ACM  - Area Chair Meeting setup, processing, and live support.
DEC  - Decisions.
POST - Postprocessing after the conference.
PLOT - Plotting and visualization tools.
```

Individual scripts can be run using:
```bash
python3 openreview/my_script.py
```
All scripts are designed to be executable, whereas frequently used functionality and tools can be found in the subdirectory `utils`. Typically, the `main()` function of each script contains several actions that can be called or are commented out. These can often be run in sequence or separately, depending on the need.


## Credits
This repository was developed by [Lukas Schmid](https://schmluk.github.io/) with some inspiration from RSS 2024 by [Kavi Katuwandeniya](https://www.linkedin.com/in/kavindie-katuwandeniya) and inputs from [Luca Carlone](https://lucacarlone.mit.edu/), among many others.
