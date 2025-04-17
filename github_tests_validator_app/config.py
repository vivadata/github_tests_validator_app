from typing import Dict, List, cast

import logging
import os

import google.cloud.logging
from dotenv import load_dotenv

load_dotenv()

if os.getenv("LOGGING", "").replace("\r\n", "").replace("\r", "") == "LOCAL":
    FORMAT = "%(asctime)s - %(levelname)s: %(message)s"
    DATEFMT = "%H:%M:%S"
    logging.basicConfig(
        format=FORMAT,
        level=logging.INFO,
        datefmt=DATEFMT,
    )

    if logging.getLogger("uvicorn") and logging.getLogger("uvicorn").handlers:
        logging.getLogger("uvicorn").removeHandler(logging.getLogger("uvicorn").handlers[0])

else:
    logging_client = google.cloud.logging.Client()
    logging_client.get_default_handler()
    logging_client.setup_logging()



commit_ref_path: Dict[str, List[str]] = {
    "pull_request": ["pull_request", "head", "ref"],
    "pusher": ["ref"],
    "workflow_job": ["workflow_job", "head_branch"]
}

# GitHub
GH_APP_ID = cast(str, os.getenv("GH_APP_ID", "")).replace("\r\n", "").replace("\r", "")
GH_APP_KEY = cast(str, os.getenv("GH_APP_KEY", "").replace("\\n", "\n"))
GH_PAT = cast(str, os.getenv("GH_PAT", "")).replace("\r\n", "").replace("\r", "")

SQLALCHEMY_URI = cast(str, os.getenv("SQLALCHEMY_URI", "")).replace("\r\n", "").replace("\r", "").replace('"', '').replace("\n", "").replace("\\n", "").strip()
# SQLALCHEMY_URI="sqlite:///./test.db"

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
