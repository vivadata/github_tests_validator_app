from typing import Any, Dict, List, Optional

import operator
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
    duration: float
    info: str

    user_id: int = Field(foreign_key="user.id")


class WorkflowRunDetail(SQLModel, table=True):
    __tablename__ = "workflow_run_detail"
    __table_args__ = {"extend_existing": True}

    created_at: datetime = Field(primary_key=True, default=datetime.now())
    file_path: str = Field(primary_key=True)
    test_name: str = Field(primary_key=True)
    repository: str
    branch: str
    script_name: str
    outcome: str
    setup: Dict[str, Any] = Field(sa_column=Column(JSON), default={})
    call: Dict[str, Any] = Field(sa_column=Column(JSON), default={})
    teardown: Dict[str, Any] = Field(sa_column=Column(JSON), default={})

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
        self.engine = create_engine(SQLALCHEMY_URI)
        SQLModel.metadata.create_all(self.engine)

    def add_new_user(self, user: User) -> None:
        with Session(self.engine) as session:
            session.add(user)
            session.commit()

    def add_new_repository_validation(
        self, user: User, result: bool, payload: Dict[str, Any], event: str, info: str = ""
    ) -> None:
        repository_validation = RepositoryValidation(
            repository=payload["repository"]["full_name"],
            branch=reduce(operator.getitem, commit_ref_path[event], payload),
            created_at=datetime.now(),
            organization_or_user=user.organization_or_user,
            user_id=user.id,
            is_valid=result,
            info=info,
        )
        with Session(self.engine) as session:
            session.add(repository_validation)
            session.commit()

    def add_new_pytest_summary(
        self,
        artifact: Dict[str, Any],
        workflow_run_id: int,
        user: User,
        repository: str,
        branch: str,
        info: str,
    ) -> None:
        pytest_summary = WorkflowRun(
            id=workflow_run_id,
            organization_or_user=user.organization_or_user,
            user_id=user.id,
            repository=repository,
            branch=branch,
            duration=artifact.get("duration", None),
            total_tests_collected=artifact.get("summary", {}).get("collected", None),
            total_passed_test=artifact.get("summary", {}).get("passed", None),
            total_failed_test=artifact.get("summary", {}).get("failed", None),
            info=info,
        )
        with Session(self.engine) as session:
            session.add(pytest_summary)
            session.commit()

    def add_new_pytest_detail(
        self,
        user: User,
        repository: str,
        branch: str,
        results: List[Dict[str, Any]],
        workflow_run_id: int,
    ) -> None:
        with Session(self.engine) as session:
            for test in results:
                pytest_detail = WorkflowRunDetail(
                    repository=repository, branch=branch, workflow_run_id=workflow_run_id, **test
                )
                session.add(pytest_detail)
            session.commit()
