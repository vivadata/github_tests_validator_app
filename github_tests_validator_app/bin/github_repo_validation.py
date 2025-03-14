from typing import Any, Dict, List, Union

import logging

from github import ContentFile
from github_tests_validator_app.config import (
    GH_PAT,
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
    github_user_branch = "main"
    logging.info(f"User branch : {github_user_branch}")
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
    logging.info(f"is valid = {user_hash == solution_hash}")
    return user_hash == solution_hash


def validate_github_repo(
    user_github_connector: GitHubConnector,
    sql_client: SQLAlchemyConnector,
    payload: Dict[str, Any],
    event: str,
) -> None:

    if user_github_connector.repo.parent:
        original_repo_name = user_github_connector.repo.parent.full_name
        logging.info(f"Connecting to ORIGINAL repo : {original_repo_name}")
    else:
        original_repo_name = user_github_connector.repo.full_name
        logging.info(f"Repository '{original_repo_name}' is not a fork, connecting to the same repository.")
        
    
    original_github_connector = GitHubConnector(
        user_data=user_github_connector.user_data,
        repo_name=original_repo_name,
        branch_name="main",
    )

    
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


    workflows_conclusion = "success" if workflows_havent_changed else "failure"
    workflows_message = default_message["valid_repository"]["workflows"][
        str(workflows_havent_changed)
    ]
    logging.info(f"Workflows conclusion: {workflows_conclusion}")
    

    sql_client.add_new_repository_validation(
        user_github_connector.user_data,
        workflows_havent_changed,
        payload,
        event,
        workflows_message,
    )
    