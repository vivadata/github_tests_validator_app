from typing import Any, Dict, List, Tuple, Union

import logging
from datetime import datetime

from github_tests_validator_app.config import (default_message)

from github_tests_validator_app.lib.connectors.github_client import GitHubConnector
from github_tests_validator_app.lib.connectors.sqlalchemy_client import SQLAlchemyConnector


def get_user_artifact(
    user_github_connector: GitHubConnector,
    sql_client: SQLAlchemyConnector,
    all_user_artifact: Dict[str, Any],
    payload: Dict[str, Any],
) -> Any:

    workflow_run_id = payload["workflow_job"]["run_id"]
    artifact_info = user_github_connector.get_artifact_info_from_artifacts_with_worflow_run_id(
        all_user_artifact["artifacts"], workflow_run_id
    )
    if not artifact_info:
        sql_client.add_new_pytest_summary(
            {},
            workflow_run_id,
            user_github_connector.user_data,
            user_github_connector.REPO_NAME,
            user_github_connector.BRANCH_NAME,
            info="[ERROR]: Cannot find the artifact of Pytest result on GitHub user repository.",
        )
        logging.error(
            "[ERROR]: Cannot find the artifact of Pytest result on GitHub user repository."
        )
        return None

    # Read Artifact
    artifact_resp = user_github_connector.get_artifact(artifact_info)
    artifact = user_github_connector.get_artifact_from_format_zip_bytes(artifact_resp.content)
    if not artifact:
        sql_client.add_new_pytest_summary(
            {},
            workflow_run_id,
            user_github_connector.user_data,
            user_github_connector.REPO_NAME,
            user_github_connector.BRANCH_NAME,
            info="[ERROR]: Cannot read the artifact of Pytest result on GitHub user repository.",
        )
        logging.error(
            "[ERROR]: Cannot read the artifact of Pytest result on GitHub user repository."
        )
        return None

    return artifact


def get_test_information(path: str) -> Tuple[str, str, str]:

    list_path_name = path.split("::")
    file_path = list_path_name[0]
    script_name = list_path_name[0].split("/")[-1]
    test_name = list_path_name[1]
    return file_path, script_name, test_name


def parsing_pytest_summaries(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    pytest_summaries = []
    for test in results:
        # if not test["outcome"] == "error":
        file_path, script_name, test_name = get_test_information(test["nodeid"])
        pytest_summaries.append(
            {   
                "challenge_name": test["keywords"][-2],
                "file_path": file_path,
                "script_name": script_name,
                "test_name": test_name,
                "outcome": test["outcome"],
                "setup": test["setup"],
                "call": test.get("call", {}),
                "teardown": test.get("teardown", {}),
            }
        )
    return pytest_summaries


def send_user_pytest_summaries(
    user_github_connector: GitHubConnector,
    sql_client: SQLAlchemyConnector,
    payload: Dict[str, Any],
    event: str,
) -> None:

    # Get all artifacts
    all_user_artifact = user_github_connector.get_all_artifacts()
    if not all_user_artifact:
        message = f"[ERROR]: Cannot get all artifact on repository {user_github_connector.REPO_NAME} of user {user_github_connector.user_data['organization_or_user']}."
        if all_user_artifact["total_count"] == 0:
            message = f"[ERROR]: No artifact on repository {user_github_connector.REPO_NAME} of user {user_github_connector.user_data['organization_or_user']}."
        sql_client.add_new_pytest_summary(
            {},
            payload["workflow_job"]["run_id"],
            user_github_connector.user_data,
            user_github_connector.REPO_NAME,
            user_github_connector.BRANCH_NAME,
            info=message,
        )
        logging.error(message)
        return

    # Get user artifact
    artifact = get_user_artifact(user_github_connector, sql_client, all_user_artifact, payload)
    # logging.info(f"User artifact: {artifact}")
    if not artifact:
        logging.info("[ERROR]: Cannot get user artifact.")
        return


    # Check if workflow detected changes in the tests
    tests_havent_changed = not "differences" in artifact
    
    sql_client.add_new_repository_validation(
        user_github_connector.user_data,
        tests_havent_changed,
        payload,
        event,
        default_message["valid_repository"]["tests"][str(tests_havent_changed)],
    )

    if not tests_havent_changed:
        logging.info(f"[ERROR] Differences in tests file found: {artifact['differences'].split()[-2]}")
        logging.info(f"Sending the police to arrest {user_github_connector.user_data['organization_or_user']}")
        return
    else:
        logging.info(f"Tests haven't changed, no need to send the police to arrest {user_github_connector.user_data['organization_or_user']}")
    
    # Send summary user results to Google Sheet
    sql_client.add_new_pytest_summary(
        artifact,
        payload["workflow_job"]["run_id"],
        user_github_connector.user_data,
        user_github_connector.REPO_NAME,
        user_github_connector.BRANCH_NAME,
        info="Result of user tests",
    )

    # Parsing artifact / challenge results
    pytest_summaries = parsing_pytest_summaries(artifact["tests"])
    # logging.info(f'pytest summaries: {pytest_summaries}')
    # Send new results to Big Query
    sql_client.add_new_pytest_detail(
        repository=user_github_connector.REPO_NAME,
        branch=user_github_connector.BRANCH_NAME,
        results=pytest_summaries,
        workflow_run_id=payload["workflow_job"]["run_id"],
    )
