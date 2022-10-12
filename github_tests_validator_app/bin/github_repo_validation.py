from typing import Any, Dict, List, Union

import logging

from github import ContentFile
from github_tests_validator_app.config import (
    GH_PAT,
    GH_TESTS_FOLDER_NAME,
    GH_TESTS_REPO_NAME,
    GH_WORKFLOWS_FOLDER_NAME,
    default_message,
)
from github_tests_validator_app.lib.connectors.github_connector import GitHubConnector
from github_tests_validator_app.lib.connectors.google_sheet import GSheetConnector
from github_tests_validator_app.lib.models.users import GitHubUser

commit_sha_path: Dict[str, List[str]] = {
    "pull_request": ["pull_request", "head", "ref"],
    "pusher": ["ref"],
    "workflow_job": [],
}


def get_event(payload: Dict[str, Any]) -> str:
    for event in commit_sha_path:
        if event in payload:
            return event
    return ""


def get_student_branch(payload: Dict[str, Any], trigger: Union[str, None] = None) -> Any:
    trigger = get_event(payload) if not trigger else trigger
    if not trigger:
        # Log error
        # FIXME
        # Archive the payload
        # FIXME
        logging.error("Couldn't find the student branch, maybe the trigger is not managed")
        return None

    path = commit_sha_path[trigger].copy()
    branch = payload
    while path:

        try:
            branch = branch[path.pop(0)]
        except KeyError as key_err:
            logging.error(key_err)
            return None
        except Exception as err:
            logging.error(err)
            return None

    return branch


def get_student_github_connector(
    student: GitHubUser, payload: Dict[str, Any]
) -> Union[GitHubConnector, None]:

    if not student:
        return None

    github_student_branch = get_student_branch(payload)
    if github_student_branch is None:
        return None

    return GitHubConnector(student, payload["repository"]["name"], github_student_branch)


def compare_folder(
    student_github: GitHubConnector, solution_repo: GitHubConnector, folder: str
) -> Any:

    student_contents = student_github.repo.get_contents(folder, ref=student_github.BRANCH_NAME)

    if (
        isinstance(student_contents, ContentFile.ContentFile)
        and student_contents.type == "submodule"
    ):
        solution_last_commit = solution_repo.get_last_hash_commit()
        student_commit = student_contents.sha
        return solution_last_commit == student_commit

    student_hash = student_github.get_hash(folder)
    solution_hash = solution_repo.get_hash(folder)
    return student_hash == solution_hash


def validate_github_repo(
    student_github_connector: GitHubConnector, gsheet: GSheetConnector, payload: Dict[str, Any]
) -> None:

    tests_github_connector = GitHubConnector(
        user=student_github_connector.user,
        repo_name=GH_TESTS_REPO_NAME
        if GH_TESTS_REPO_NAME
        else student_github_connector.repo.parent.full_name,
        branch_name="main",
        access_token=GH_PAT,
    )
    original_github_connector = GitHubConnector(
        user=student_github_connector.user,
        repo_name=student_github_connector.repo.parent.full_name,
        branch_name="main",
        access_token=GH_PAT,
    )
    if not tests_github_connector:
        gsheet.add_new_repo_valid_result(
            student_github_connector.user,
            False,
            "[ERROR]: cannot get the tests github repository.",
        )
        logging.error("[ERROR]: cannot get the tests github repository.")
        return
    if not original_github_connector:
        gsheet.add_new_repo_valid_result(
            student_github_connector.user,
            False,
            "[ERROR]: cannot get the original github repository.",
        )
        logging.error("[ERROR]: cannot get the original github repository.")
        return

    workflows_havent_changed = compare_folder(
        student_github_connector, original_github_connector, GH_WORKFLOWS_FOLDER_NAME
    )
    tests_havent_changed = compare_folder(
        student_github_connector, tests_github_connector, GH_TESTS_FOLDER_NAME
    )

    # Add valid repo result on Google Sheet
    gsheet.add_new_repo_valid_result(
        student_github_connector.user,
        workflows_havent_changed,
        default_message["valid_repository"]["workflows"][str(workflows_havent_changed)],
    )
    gsheet.add_new_repo_valid_result(
        student_github_connector.user,
        tests_havent_changed,
        default_message["valid_repository"]["tests"][str(tests_havent_changed)],
    )

    # Update Pull Request
    if "pull_request" in payload:
        issue = student_github_connector.repo.get_issue(number=payload["pull_request"]["number"])
        tests_conclusion = "success" if tests_havent_changed else "failure"
        tests_message = default_message["valid_repository"]["tests"][str(tests_havent_changed)]
        issue.create_comment(tests_message)
        student_github_connector.repo.create_check_run(
            name=tests_message,
            head_sha=payload["pull_request"]["head"]["sha"],
            status="completed",
            conclusion=tests_conclusion,
        )
        workflows_conclusion = "success" if workflows_havent_changed else "failure"
        workflows_message = default_message["valid_repository"]["workflows"][
            str(workflows_havent_changed)
        ]
        student_github_connector.repo.create_check_run(
            name=workflows_message,
            head_sha=payload["pull_request"]["head"]["sha"],
            status="completed",
            conclusion=workflows_conclusion,
        )
        issue.create_comment(workflows_message)
