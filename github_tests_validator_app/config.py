from typing import Dict, List, cast

import logging
import os

import google.cloud.logging
from dotenv import load_dotenv

load_dotenv()

if os.getenv("LOGGING", "").replace("\r\n", "").replace("\r", "") == "GCP":
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


commit_ref_path: Dict[str, List[str]] = {
    "pull_request": ["pull_request", "head", "ref"],
    "pusher": ["ref"],
    "workflow_job": ["workflow_job", "head_branch"]
}

# GitHub
GH_APP_ID = cast(str, os.getenv("GH_APP_ID", "")).replace("\r\n", "").replace("\r", "")
GH_APP_KEY = cast(str, os.getenv("GH_APP_KEY", "").replace("\\n", "\n"))
GH_PAT = cast(str, os.getenv("GH_PAT", "")).replace("\r\n", "").replace("\r", "")

SQLALCHEMY_URI = cast(str, os.getenv("SQLALCHEMY_URI", "")).replace("\r\n", "").replace("\r", "").replace('"', '')
SQLALCHEMY_URI="sqlite:///./test.db"

GH_TESTS_REPO_NAME = (
    cast(str, os.getenv("GH_TESTS_REPO_NAME", "")).replace("\r\n", "").replace("\r", "")
)
GH_TESTS_FOLDER_NAME = "/01-Data-Types-and-Data-Structures/01-Challenges/02-Rugby_Premiership/tests"
GH_WORKFLOWS_FOLDER_NAME = ".github/workflows"
GH_API = "https://api.github.com/repos"
GH_ALL_ARTIFACT_ENDPOINT = "actions/artifacts"

# Log message
default_message: Dict[str, Dict[str, Dict[str, str]]] = {
    "valid_repository": {
        "tests": {
            "True": "tests",
            "False": "tests",
        },
        "workflows": {
            "True": "workflows",
            "False": "workflows",
        },
    },
}
