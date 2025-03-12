from typing import Any, Dict, List, Optional

import json
import operator
import logging
from datetime import datetime
from functools import reduce

from github_tests_validator_app.config import SQLALCHEMY_URI, commit_ref_path
from sqlmodel import JSON, Column, Field, Relationship, Session, SQLModel, create_engine


class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    organization_or_user: str
    url: str
    created_at: datetime = Field(default=datetime.now())


class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_run"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    organization_or_user: str

    repository: str
    branch: str
    created_at: datetime = Field(default=datetime.now())
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

    created_at: datetime = Field(primary_key=True, default=datetime.now())
    file_path: str = Field(primary_key=True)
    test_name: str = Field(primary_key=True)
    challenge_name: str 
    repository: str
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
    branch: str = Field(primary_key=True)
    created_at: datetime = Field(primary_key=True, default=datetime.now())
    organization_or_user: str
    is_valid: bool
    info: str

    user_id: int = Field(foreign_key="user.id")


class SQLAlchemyConnector:
    def __init__(self) -> None:
        logging.info("Using SQLALCHEMY_URI: %s", SQLALCHEMY_URI)
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
            created_at=datetime.now(),
            organization_or_user=user_data["organization_or_user"],
            user_id=user_data["id"],
            is_valid=result,
            info=info,
        )
        with Session(self.engine) as session:
            try:
                session.add(repository_validation)
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
                session.add(pytest_summary)
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
        logging.info(f"Adding new pytest details...")
        with Session(self.engine) as session:
            try:
                for test in results:
                    pytest_detail = WorkflowRunDetail(
                        created_at=datetime.now(),
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
                    session.add(pytest_detail)
                session.commit()
                logging.info("Pytest details added successfully.")
            except Exception as e:
                session.rollback()
                logging.error(f"Error adding pytest details: {e}")
                raise e
