from typing import Dict, cast

import logging
import os

import google.cloud.logging
import yaml

if os.getenv("LOGGING", "").replace("\r\n", "") == "GCP":
    logging_client = google.cloud.logging.Client()
    logging_client.get_default_handler()
    logging_client.setup_logging()
else:
    FORMAT = "%(asctime)s - %(levelname)s: %(message)s"
    DATEFMT = "%H:%M:%S"
    logging.basicConfig(
        format=FORMAT,
        level=logging.INFO,
        datefmt=DATEFMT,
    )

    if logging.getLogger("uvicorn") and logging.getLogger("uvicorn").handlers:
        logging.getLogger("uvicorn").removeHandler(logging.getLogger("uvicorn").handlers[0])

# GitHub
GH_APP_ID = cast(str, os.getenv("GH_APP_ID", None)).replace("\r\n", "")
GH_APP_KEY = cast(str, os.getenv("GH_APP_KEY", None))
GH_PAT = cast(str, os.getenv("GH_PAT", None)).replace("\r\n", "")
GH_TESTS_REPO_NAME = cast(str, os.getenv("GH_TESTS_REPO_NAME", "")).replace("\r\n", "")
GH_TESTS_FOLDER_NAME = "tests"
GH_WORKFLOWS_FOLDER_NAME = ".github/workflows"
GH_API = "https://api.github.com/repos"
GH_ALL_ARTIFACT_ENDPOINT = "actions/artifacts"

# Google Drive
GDRIVE_MAIN_DIRECTORY_NAME = cast(str, os.getenv("GDRIVE_MAIN_DIRECTORY_NAME", "")).replace(
    "\r\n", ""
)

# Google Sheet
GDRIVE_HIERARCHY_PATH = "github_tests_validator_app/data/gdrive_hierarchy.yml"
with open(GDRIVE_HIERARCHY_PATH) as file:
    data = yaml.safe_load(file)

GDRIVE_SUMMARY_SPREADSHEET = data["gdrive_summary_spreadsheet"]
GSHEET_DETAILS_SPREADSHEET = data["gsheet_details_spreadsheet"]

# Log message
default_message: Dict[str, Dict[str, Dict[str, str]]] = {
    "valid_repository": {
        "tests": {
            "True": "Your folder `Test` is valid",
            "False": "Your folder `Test` has been modified and is no longer valid.",
        },
        "workflows": {
            "True": "Your folder `.github/workflows` is valid",
            "False": "Your folder `.github/workflows` has been modified and is no longer valid.",
        },
    },
}

# Common
CHALLENGE_DIR = "tests/tests/"
DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
USER_SHARE = os.getenv("USER_SHARE", "").replace("\r\n", "").split(",")
