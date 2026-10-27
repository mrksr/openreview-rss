import openreview
import datetime
from utils.setup_client import setup_client
from utils.paths import VENUE, TEST_VENUE


def main():
    """
    Script to create a registration stage for Senior Area Chairs. These instructions require the old API and were provided by OpenReview support.
    """
    TARGET_GROUP = f"{VENUE}/Senior_Area_Chairs"  # Test: f"{TEST_VENUE}/Senior_Area_Chairs"
    REQUEST_FORM_ID = "pAjP-mkFPfb" # Test: "rIjQAtPaX-z"
    start_date = datetime.datetime.now()
    due_date = datetime.datetime(2025,1,11,11,59)
    instructions = 'As a Senior Area Chair, please complete the following two tasks to complete the registration:\n\n1) Update your OpenReview profile. This information will be used to avoid conflicts of interests (CoI). You can find your OpenReview profile here: https://openreview.net/profile, or by clicking on your name in the top right corner. Afterwards click "Edit Profile" and complete all sections.\n\n2) Complete your Expertise Selection by importing your relevant papers to OpenReview. This information will be used to compute affinity scores and match papers to ACs and reviewers. You can find your expertise selection here: https://openreview.net/invitation?id=roboticsfoundation.org/RSS/2027/Conference/Senior_Area_Chairs/-/Expertise_Selection, or by navigating to "Tasks->RSS 2027->Senior Area Chair Registration" in the top right corner.\n\n3) Please select at least 3 RSS Keywords that describe your expertise in decreasing order of priority. These will be used to match papers to SACs, ACs and reviewers.\n\nThank you for serving as an Area Chair for RSS 2027, we\'re excited to have you on board!'
    name = "Registration"
    title = "Senior Area Chair Registration"
    additional_fields = {
        "keyword_selection": {
            "order": 4,
            "description": "Please specify at least 3 keywords in decreasing order of importance.",
            "value": {
                "param": {
                    "type": "string[]",
                    "optional": False,
                    "input": "select",
                    "enum": [
                        "Assembly, Logistics and Manufacturing",
                        "Assistive, Entertainment and Service Robots",
                        "Autonomous Vehicle Navigation & Mobile Robots",
                        "Bioinspired Robots",
                        "Control & Dynamics",
                        "Cognitive Modeling & Knowledge Representation for Robots",
                        "Field Robotics (e.g., Aerial, Agricultural, Construction, Space, Underwater Robotics)",
                        "Formal Methods for Robotics",
                        "Grasping & Manipulation",
                        "Human-Robot Interaction",
                        "Humanoid & Walking Robots",
                        "Mechanisms & Design",
                        "Medical Robotics",
                        "Multi-Robot & Networked Systems",
                        "Robot Learning: Foundation Models",
                        "Robot Learning: Reinforcement Learning",
                        "Robot Learning: Imitation Learning",
                        "Robot Learning: Model Learning",
                        "Robot Learning: Datasets and Benchmarks",
                        "Robot Modeling & Simulation",
                        "Perceptual Learning",
                        "Robot Perception, Sensing & Vision",
                        "Robot Planning",
                        "Robot State Estimation, Localization & Mapping",
                        "Soft Robots",
                    ],
                }
            },
        }
    }

    # Setup the client.
    client = setup_client(old_api=True, test_venue=False)
    venue = openreview.helpers.get_conference(
        client, request_form_id=REQUEST_FORM_ID, setup=False
    )

    # Check if the registration stage already exists.
    for r in venue.registration_stages:
        if r.committee_id == TARGET_GROUP:
            print(f" '{TARGET_GROUP}' registration stage already exists.")
            r.start_date = start_date
            r.due_date = due_date
            r.instructions = instructions
            r.name = name
            r.title = title
            r.additional_fields = additional_fields
            return

    # Otherwise create a new registration stage.
    print(f"Creating registration stage for '{TARGET_GROUP}'.")
    venue.registration_stages.append(
        openreview.stages.RegistrationStage(
            committee_id=TARGET_GROUP,
            name=name,
            start_date=start_date,
            due_date=due_date,
            instructions=instructions,
            title=title,
            additional_fields=additional_fields,
        )
    )
    venue.create_registration_stages()
    print("Registration stage created.")


if __name__ == "__main__":
    main()
