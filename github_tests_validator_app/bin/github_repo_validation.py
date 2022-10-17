from typing import Any, Dict, List, Union

import logging

from github import ContentFile
from github_tests_validator_app.config import (
    GH_PAT,
    GH_TESTS_FOLDER_NAME,
    GH_TESTS_REPO_NAME,
    GH_WORKFLOWS_FOLDER_NAME,
    commit_ref_path,
    default_message,
)
from github_tests_validator_app.lib.connectors.github_client import GitHubConnector
from github_tests_validator_app.lib.connectors.sqlalchemy_client import SQLAlchemyConnector, User


def get_event(payload: Dict[str, Any]) -> str:
    for event in commit_ref_path:
        if event in payload:
            return str(event)
    return ""


def get_user_branch(payload: Dict[str, Any], trigger: Union[str, None] = None) -> Any:
    trigger = get_event(payload) if not trigger else trigger
    if not trigger:
        # Log error
        # FIXME
        # Archive the payload
        # FIXME
        logging.error("Couldn't find the user branch, maybe the trigger is not managed")
        return None

    path = commit_ref_path[trigger].copy()
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


def get_user_github_connector(user: User, payload: Dict[str, Any]) -> Union[GitHubConnector, None]:

    if not user:
        return None

    github_user_branch = get_user_branch(payload)
    if github_user_branch is None:
        return None

    return GitHubConnector(user, payload["repository"]["full_name"], github_user_branch)


def compare_folder(
    user_github: GitHubConnector, solution_repo: GitHubConnector, folder: str
) -> Any:

    user_contents = user_github.repo.get_contents(folder, ref=user_github.BRANCH_NAME)

    if isinstance(user_contents, ContentFile.ContentFile) and user_contents.type == "submodule":
        solution_last_commit = solution_repo.get_last_hash_commit()
        user_commit = user_contents.sha
        return solution_last_commit == user_commit

    user_hash = user_github.get_hash(folder)
    solution_hash = solution_repo.get_hash(folder)
    return user_hash == solution_hash


def validate_github_repo(
    user_github_connector: GitHubConnector,
    gsheet: SQLAlchemyConnector,
    payload: Dict[str, Any],
    event: str,
) -> None:

    logging.info(f"Connecting to repo : {GH_TESTS_REPO_NAME}")

    tests_github_connector = GitHubConnector(
        user=user_github_connector.user,
        repo_name=GH_TESTS_REPO_NAME
        if GH_TESTS_REPO_NAME
        else user_github_connector.repo.parent.full_name,
        branch_name="main",
        access_token=GH_PAT,
    )

    logging.info(f"Connecting to repo : {user_github_connector.repo.parent.full_name}")

    original_github_connector = GitHubConnector(
        user=user_github_connector.user,
        repo_name=user_github_connector.repo.parent.full_name,
        branch_name="main",
        access_token=GH_PAT,
    )
    if not tests_github_connector:
        gsheet.add_new_repository_validation(
            user_github_connector.user,
            False,
            payload,
            event,
            "[ERROR]: cannot get the tests github repository.",
        )
        logging.error("[ERROR]: cannot get the tests github repository.")
        return
    if not original_github_connector:
        gsheet.add_new_repository_validation(
            user_github_connector.user,
            False,
            payload,
            event,
            "[ERROR]: cannot get the original github repository.",
        )
        logging.error("[ERROR]: cannot get the original github repository.")
        return

    workflows_havent_changed = compare_folder(
        user_github_connector, original_github_connector, GH_WORKFLOWS_FOLDER_NAME
    )
    tests_havent_changed = compare_folder(
        user_github_connector, tests_github_connector, GH_TESTS_FOLDER_NAME
    )

    # Add valid repo result on Google Sheet
    gsheet.add_new_repository_validation(
        user_github_connector.user,
        workflows_havent_changed,
        payload,
        event,
        default_message["valid_repository"]["workflows"][str(workflows_havent_changed)],
    )
    gsheet.add_new_repository_validation(
        user_github_connector.user,
        tests_havent_changed,
        payload,
        event,
        default_message["valid_repository"]["tests"][str(tests_havent_changed)],
    )

    tests_conclusion = "success" if tests_havent_changed else "failure"
    tests_message = default_message["valid_repository"]["tests"][str(tests_havent_changed)]
    workflows_conclusion = "success" if workflows_havent_changed else "failure"
    workflows_message = default_message["valid_repository"]["workflows"][
        str(workflows_havent_changed)
    ]

    if event == "pull_request":
        issue = user_github_connector.repo.get_issue(number=payload["pull_request"]["number"])
        issue.create_comment(tests_message)
        user_github_connector.repo.create_check_run(
            name=tests_message,
            head_sha=payload["pull_request"]["head"]["sha"],
            status="completed",
            conclusion=tests_conclusion,
        )
        user_github_connector.repo.create_check_run(
            name=workflows_message,
            head_sha=payload["pull_request"]["head"]["sha"],
            status="completed",
            conclusion=workflows_conclusion,
        )
        issue.create_comment(workflows_message)
    elif event == "pusher":
        user_github_connector.repo.create_check_run(
            name=tests_message,
            head_sha=payload["after"],
            status="completed",
            conclusion=tests_conclusion,
        )
        user_github_connector.repo.create_check_run(
            name=workflows_message,
            head_sha=payload["after"],
            status="completed",
            conclusion=workflows_conclusion,
        )
