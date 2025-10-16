from typing import Any, Dict, List, Optional

import json
import operator
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import reduce

from github_tests_validator_app.config import SQLALCHEMY_URI, commit_ref_path
from sqlmodel import JSON, Column, Field, Relationship, Session, SQLModel, create_engine
from google.cloud import bigquery


class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    organization_or_user: str
    url: str
    created_at: datetime = Field(default=datetime.now(ZoneInfo("Europe/Paris")))


class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_run"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    organization_or_user: str

    repository: str
    branch: str
    created_at: datetime = Field(default=datetime.now(ZoneInfo("Europe/Paris")))
    total_tests_collected: int
    total_passed_test: int
    total_failed_test: int
    total_error_test: int
    duration: float
    info: str

    user_id: int = Field(foreign_key="user.id")


class WorkflowRunDetail(SQLModel, table=True):
    __tablename__ = "workflow_run_detail"
    __table_args__ = {"extend_existing": True}

    created_at: datetime = Field(default=datetime.now(ZoneInfo("Europe/Paris")))
    organization_or_user: str = Field(primary_key=True)
    file_path: str = Field(primary_key=True)
    test_name: str = Field(primary_key=True)
    challenge_name: str 
    repository: str = Field(primary_key=True)
    branch: str
    script_name: str
    outcome: str
    setup: str = Field(default="{}")
    call: str = Field(default="{}")
    teardown: str = Field(default="{}")

    workflow_run_id: int = Field(foreign_key="workflow_run.id")


class RepositoryValidation(SQLModel, table=True):
    __tablename__ = "repository_validation"
    __table_args__ = {"extend_existing": True}

    repository: str = Field(primary_key=True)
    branch: str
    created_at: datetime = Field(default=datetime.now(ZoneInfo("Europe/Paris")))
    organization_or_user: str
    is_valid: bool
    info: str = Field(primary_key=True)

    user_id: int = Field(foreign_key="user.id")


class SQLAlchemyConnector:
    def __init__(self) -> None:
        logging.info("Using SQLALCHEMY_URI: %s", SQLALCHEMY_URI.strip())
        self.engine = create_engine(SQLALCHEMY_URI)
        SQLModel.metadata.create_all(self.engine)

    def add_new_user(self, user_data: Dict[str, Any]) -> None:
        user = User(**user_data)
        with Session(self.engine) as session:
            try:
                # Use merge to handle insert or update
                session.merge(user)
                session.commit()
                logging.info("User added successfully.")
            except Exception as e:
                session.rollback()
                raise e

    def add_new_repository_validation(
        self,
        user_data: Dict[str, Any],
        result: bool,
        payload: Dict[str, Any],
        event: str,
        info: str = "",
    ) -> None:
        logging.info(f"Adding new repository validation ...")
        repository_validation = RepositoryValidation(
            repository=payload["repository"]["full_name"],
            branch=reduce(operator.getitem, commit_ref_path[event], payload).replace("refs/heads/", ""),
            created_at=datetime.now(ZoneInfo("Europe/Paris")),
            organization_or_user=user_data["organization_or_user"],
            user_id=user_data["id"],
            is_valid=result,
            info=info,
        )
        with Session(self.engine) as session:
            try:
                session.merge(repository_validation)
                session.commit()
                logging.info("Repository validation added successfully.")
            except Exception as e:
                session.rollback()
                logging.error(f"Error adding repository validation: {e}")
                raise e

    def add_new_pytest_summary(
        self,
        artifact: Dict[str, Any],
        workflow_run_id: int,
        user_data: Dict[str, Any],
        repository: str,
        branch: str,
        info: str,
    ) -> None:
        logging.info(f"Adding new pytest summary ...")
        pytest_summary = WorkflowRun(
            id=workflow_run_id,
            organization_or_user=user_data["organization_or_user"],
            user_id=user_data["id"],
            repository=repository,
            branch=branch,
            duration=artifact.get("duration", None),
            total_tests_collected=artifact.get("summary", {}).get("collected", None),
            total_passed_test=artifact.get("summary", {}).get("passed", None),
            total_failed_test=artifact.get("summary", {}).get("failed", 0),
            total_error_test=artifact.get("summary", {}).get("error", 0),
            info=info,
        )
        with Session(self.engine) as session:
            try:
                session.merge(pytest_summary)
                session.commit()
                logging.info("Pytest summary added successfully.")
            except Exception as e:
                session.rollback()
                logging.error(f"Error adding pytest summary: {e}")
                raise e


    def add_new_pytest_detail(
            self,
            repository: str,
            branch: str,
            results: List[Dict[str, Any]],
            workflow_run_id: int,
        ) -> None:
        
        summaries = [
                    dict(
                        created_at=datetime.now(ZoneInfo("Europe/Paris")).isoformat(),
                        organization_or_user=repository.split("/")[0],
                        repository=repository,
                        branch=branch,
                        workflow_run_id=workflow_run_id,
                        file_path=test["file_path"],
                        test_name=test["test_name"],
                        script_name=test["script_name"],
                        challenge_name=test["challenge_name"],
                        outcome=test["outcome"],
                        setup=json.dumps(test["setup"]),
                        call=json.dumps(test["call"]),
                        teardown=json.dumps(test["teardown"]),
                    )
                    for test in results
        ] 
        
        client        = bigquery.Client()
        dataset       = SQLALCHEMY_URI.split("/")[-1]
        main_table    = f"{dataset}.workflow_run_detail"
        staging_table = f"{dataset}.staging_workflow_run_detail_{workflow_run_id}"

        
        create_staging_sql = f"""
        CREATE TABLE `{staging_table}` 
        LIKE `{main_table}`;
        """
        
        try:
            logging.info("Creating staging table...")
            client.query(create_staging_sql).result()
        except Exception as e:
            logging.error(f"Error creating staging table: {e}")
            raise e

        try:
            logging.info("Inserting data into staging table...")
            errors = client.insert_rows_json(staging_table, summaries)
            if errors:
                raise RuntimeError(errors)
        except Exception as e:
            logging.error(f"Error inserting data into staging table: {e}")
            raise e

        # 2) MERGE depuis staging vers la table principale
        merge_sql = f"""
        MERGE `{main_table}` AS T
        USING `{staging_table}` AS S
        ON T.organization_or_user = S.organization_or_user
        AND T.file_path           = S.file_path
        AND T.test_name           = S.test_name
        AND T.repository          = S.repository
        WHEN MATCHED THEN
        UPDATE SET
            created_at           = S.created_at,
            branch               = S.branch,
            workflow_run_id      = S.workflow_run_id,
            script_name          = S.script_name,
            challenge_name       = S.challenge_name,
            outcome              = S.outcome,
            setup                = S.setup,
            call                 = S.call,
            teardown             = S.teardown
        WHEN NOT MATCHED THEN
        INSERT (created_at, organization_or_user, repository, branch,
                workflow_run_id, file_path, test_name, script_name,
                challenge_name, outcome, setup, call, teardown)
        VALUES (S.created_at, S.organization_or_user, S.repository, S.branch,
                S.workflow_run_id, S.file_path, S.test_name, S.script_name,
                S.challenge_name, S.outcome, S.setup, S.call, S.teardown)
        """
        
        try:
            logging.info("Merging data from staging to main table...")
            client.query(merge_sql).result()
        except Exception as e:
            logging.error(f"Error merging data: {e}")
            raise e

        
        cleanup_sql = f"""
        DROP TABLE `{staging_table}`;
        """
        
        try:
            logging.info("Dropping staging table...")
            job = client.query(cleanup_sql)
            job.result()
        except Exception as e:
            logging.error(f"Error cleaning up staging table: {e}")
            raise e

        logging.info("Pytest details added successfully.")
        
