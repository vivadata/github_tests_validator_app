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


def get_user_github_connector(
    user_data: Dict[str, Any], payload: Dict[str, Any]
) -> Union[GitHubConnector, None]:

    if not user_data:
        return None

    github_user_branch = get_user_branch(payload)
    if github_user_branch is None:
        return None

    return GitHubConnector(user_data, payload["repository"]["full_name"], github_user_branch)


def compare_folder(
    user_github: GitHubConnector, solution_repo: GitHubConnector, folder: str
) -> Any:

    logging.info(f"BRANCH NAME: {user_github.BRANCH_NAME}")
    user_contents = user_github.repo.get_contents(folder, ref=user_github.BRANCH_NAME)

    if isinstance(user_contents, ContentFile.ContentFile) and user_contents.type == "submodule":
        solution_last_commit = solution_repo.get_last_hash_commit()
        user_commit = user_contents.sha
        return solution_last_commit == user_commit

    user_hash = user_github.get_hash(folder)
    solution_hash = solution_repo.get_hash(folder)
    logging.info(f"user_hash = {user_hash}")
    logging.info(f"solution_hash = {solution_hash}")
    return user_hash == solution_hash


def validate_github_repo(
    user_github_connector: GitHubConnector,
    sql_client: SQLAlchemyConnector,
    payload: Dict[str, Any],
    event: str,
) -> None:
    
    # Fetch the test results JSON from GitHub Actions artifact
    tests_results_json = user_github_connector.get_tests_results_json()
    if tests_results_json is None:
        logging.error("Validation failed due to missing or invalid test results artifact.")
        tests_passed = False
        failed_tests_summary = "No test results found."
    else:
        # Determine if tests have failed and prepare a summary
        tests_failed = tests_results_json.get("tests_failed", 0)
        tests_passed = tests_failed == 0
        failed_tests_summary = ""
        if tests_failed > 0:
            failed_tests = tests_results_json.get("tests", [])
            for test in failed_tests:
                if test.get("outcome") == "failed":
                    failed_tests_summary += (
                        f"- Test: {test.get('nodeid')} failed with message: "
                        f"{test.get('call', {}).get('crash', {}).get('message', 'No message')}\n"
                    )

        
    logging.info(f"Connecting to TEST repo : {GH_TESTS_REPO_NAME}")

    if user_github_connector.repo.parent:
        original_repo_name = user_github_connector.repo.parent.full_name
        logging.info(f"Connecting to ORIGINAL repo : {original_repo_name}")
    else:
        original_repo_name = user_github_connector.repo.full_name
        logging.info(f"Repository '{original_repo_name}' is not a fork, connecting to the same repository.")
        
    tests_github_connector = GitHubConnector(
        user_data=user_github_connector.user_data,
        repo_name=GH_TESTS_REPO_NAME
        if GH_TESTS_REPO_NAME
        else original_repo_name,
        branch_name="feat/ci_workflow",
        access_token=GH_PAT,
    )
    
    original_github_connector = GitHubConnector(
        user_data=user_github_connector.user_data,
        repo_name=original_repo_name,
        branch_name="feat/ci_workflow",
        access_token=GH_PAT,
    )
    
    if not tests_github_connector:
        sql_client.add_new_repository_validation(
            user_github_connector.user_data,
            False,
            payload,
            event,
            "[ERROR]: cannot get the tests github repository.",
        )
        logging.error("[ERROR]: cannot get the tests github repository.")
        return
    
    if not original_github_connector:
        sql_client.add_new_repository_validation(
            user_github_connector.user_data,
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
    # tests_havent_changed = compare_folder(
    #     user_github_connector, tests_github_connector, GH_TESTS_FOLDER_NAME
    # ) #TODO: Uncomment this line to enable tests FOLDER validation
    tests_havent_changed = tests_passed

    # Add valid repo result on Google Sheet
    sql_client.add_new_repository_validation(
        user_github_connector.user_data,
        workflows_havent_changed,
        payload,
        event,
        default_message["valid_repository"]["workflows"][str(workflows_havent_changed)],
    )
    
    sql_client.add_new_repository_validation(
        user_github_connector.user_data,
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
        pull_request = user_github_connector.repo.get_pull(number=payload["pull_request"]["number"])
        # Create a Check Run with detailed test results in case of failure
        user_github_connector.repo.create_check_run(
            name="Validation Tests Result",
            head_sha=payload["pull_request"]["head"]["sha"],
            status="completed",
            conclusion=tests_conclusion,
            output={
                "title": "Validation Tests Result",
                "summary": tests_message,
                "text": failed_tests_summary if not tests_havent_changed else "",
            }
        )
        user_github_connector.repo.create_check_run(
            name="Workflow Validation",
            head_sha=payload["pull_request"]["head"]["sha"],
            status="completed",
            conclusion=workflows_conclusion,
            output={
                "title": "Workflow Validation Result",
                "summary": workflows_message,
            }
        )
        pull_request.create_issue_comment(tests_message)
        pull_request.create_issue_comment(workflows_message)
    elif event == "pusher":
        user_github_connector.repo.create_check_run(
            name="Validation Tests Result",
            head_sha=payload["after"],
            status="completed",
            conclusion=tests_conclusion,
            output={
                "title": "Validation Tests Result",
                "summary": tests_message,
                "text": failed_tests_summary if not tests_havent_changed else "",
            }
        )
        user_github_connector.repo.create_check_run(
            name="Workflow Validation",
            head_sha=payload["after"],
            status="completed",
            conclusion=workflows_conclusion,
            output={
                "title": "Workflow Validation Result",
                "summary": workflows_message,
            }
        )
