SHELL := /usr/bin/env bash

IMAGE := github_tests_validator_app
VERSION := latest

NO_CHECK_FLAG =  || true

ifeq ($(STRICT), 1)
	POETRY_COMMAND_FLAG =
	PIP_COMMAND_FLAG =
	SAFETY_COMMAND_FLAG =
	BANDIT_COMMAND_FLAG =
	SECRETS_COMMAND_FLAG =
	BLACK_COMMAND_FLAG =
	DARGLINT_COMMAND_FLAG =
	ISORT_COMMAND_FLAG =
	MYPY_COMMAND_FLAG =
else
	POETRY_COMMAND_FLAG = $(NO_CHECK_FLAG)
	PIP_COMMAND_FLAG = $(NO_CHECK_FLAG)
	SAFETY_COMMAND_FLAG = $(NO_CHECK_FLAG)
	BANDIT_COMMAND_FLAG = $(NO_CHECK_FLAG)
	SECRETS_COMMAND_FLAG = $(NO_CHECK_FLAG)
	BLACK_COMMAND_FLAG = $(NO_CHECK_FLAG)
	DARGLINT_COMMAND_FLAG = $(NO_CHECK_FLAG)
	ISORT_COMMAND_FLAG = $(NO_CHECK_FLAG)
	MYPY_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(POETRY_STRICT), 1)
	POETRY_COMMAND_FLAG =
else ifeq ($(POETRY_STRICT), 0)
	POETRY_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(PIP_STRICT), 1)
	PIP_COMMAND_FLAG =
else ifeq ($(PIP_STRICT), 0)
	PIP_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(SAFETY_STRICT), 1)
	SAFETY_COMMAND_FLAG =
else ifeq ($(SAFETY_STRICT), 0)
	SAFETY_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(BANDIT_STRICT), 1)
	BANDIT_COMMAND_FLAG =
else ifeq ($(BANDIT_STRICT), 0)
	BANDIT_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(SECRETS_STRICT), 1)
	SECRETS_COMMAND_FLAG =
else ifeq ($(SECRETS_STRICT), 0)
	SECRETS_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(BLACK_STRICT), 1)
	BLACK_COMMAND_FLAG =
else ifeq ($(BLACK_STRICT), 0)
	BLACK_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(DARGLINT_STRICT), 1)
	DARGLINT_COMMAND_FLAG =
else ifeq ($(DARGLINT_STRICT), 0)
	DARGLINT_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(ISORT_STRICT), 1)
	ISORT_COMMAND_FLAG =
else ifeq ($(ISORT_STRICT), 0)
	ISORT_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

ifeq ($(MYPY_STRICT), 1)
	MYPY_COMMAND_FLAG =
else ifeq ($(MYPY_STRICT), 0)
	MYPY_COMMAND_FLAG = $(NO_CHECK_FLAG)
endif

.PHONY: download-poetry
download-poetry:
	curl -sSL https://install.python-poetry.org | python3 -

.PHONY: install
install:
	poetry env use python3.9
	poetry lock -n
	poetry install -n
ifneq ($(NO_PRE_COMMIT), 1)
	poetry run pre-commit install -t pre-commit -t pre-push
endif

.PHONY: check-safety
check-safety:
	poetry check$(POETRY_COMMAND_FLAG) && \
	poetry run pip check$(PIP_COMMAND_FLAG) && \
	poetry run safety check --full-report$(SAFETY_COMMAND_FLAG) && \
	poetry run bandit -r github_tests_validator_app/$(BANDIT_COMMAND_FLAG)

.PHONY: gitleaks
gitleaks:
	commits="$$(git rev-list --ancestry-path $$(git rev-parse $$(git branch -r --sort=committerdate | tail -1))..$$(git rev-parse HEAD))"; \
	if [ "$${commits}" != "" ]; then docker run --rm -v $$(pwd):/code/ zricethezav/gitleaks --path=/code/ -v --commits=$$(echo $${commits} | paste -s -d, -)$(SECRETS_COMMAND_FLAG); fi;

.PHONY: check-style
check-style:
	poetry run black --config pyproject.toml --diff --check ./$(BLACK_COMMAND_FLAG) && \
	poetry run darglint -v 2 **/*.py$(DARGLINT_COMMAND_FLAG) && \
	poetry run isort --settings-path pyproject.toml --check-only **/*.py$(ISORT_COMMAND_FLAG) && \
	poetry run mypy --config-file setup.cfg github_tests_validator_app tests/**/*.py$(MYPY_COMMAND_FLAG)

.PHONY: format-code
format-code:
	poetry run pre-commit run

.PHONY: test
test:
	poetry run pytest

.PHONY: lint
lint: test check-safety check-style

# Example: make docker VERSION=latest
# Example: make docker IMAGE=some_name VERSION=0.1.0
.PHONY: docker
docker:
	@echo Building docker $(IMAGE):$(VERSION) ...
	docker build \
		--platform=linux/amd64 \
		-t $(IMAGE):$(VERSION) . \
		-f ./docker/Dockerfile

# Example: make clean_docker VERSION=latest
# Example: make clean_docker IMAGE=some_name VERSION=0.1.0
.PHONY: clean_docker
clean_docker:
	@echo Removing docker $(IMAGE):$(VERSION) ...
	docker rmi -f $(IMAGE):$(VERSION)

.PHONY: clean_build
clean_build:
	rm -rf build/

.PHONY: clean
clean: clean_build clean_docker


include .env
export

.PHONY: deploy_gcp
deploy_gcp: docker
	@echo Deploying to GCP ...
	docker tag github_tests_validator_app:latest ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app:latest
	docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app:latest

.PHONY: deploy_gcp_terraform
deploy_gcp_terraform:
	@echo Deploying to GCP with Terraform ...
	@if ! gcloud artifacts repositories describe github-app-registry --location=${REGION} >/dev/null 2>&1; then \
	  echo "Repository not found. Creating repository..."; \
	  gcloud artifacts repositories create github-app-registry \
	    --repository-format=docker \
	    --location=${REGION} \
	    --description="Repository for app validator Docker images"; \
	else \
	  echo "Repository already exists. Skipping creation."; \
	fi
	gcloud builds submit --config=cloudbuild.yaml .  --substitutions=_IMAGE_NAME=${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/${IMAGE}:${VERSION}
	terraform -chdir=iac/ workspace select default
	source iac/get_env_variables.sh
	terraform -chdir=iac/ apply

.PHONY: deploy_gcp_terraform_dev
deploy_gcp_terraform_dev:
	@echo Deploying to GCP in dev version with Terraform ...
	@if ! gcloud artifacts repositories describe github-app-registry-dev --location=${REGION} >/dev/null 2>&1; then \
	  echo "Repository not found. Creating repository..."; \
	  gcloud artifacts repositories create github-app-registry-dev \
	    --repository-format=docker \
	    --location=${REGION} \
	    --description="Repository for app validator Docker images"; \
	else \
	  echo "Repository already exists. Skipping creation."; \
	fi
	gcloud builds submit --config=cloudbuild.yaml .  --substitutions=_IMAGE_NAME=${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry-dev/${IMAGE}:${VERSION}
	terraform -chdir=iac/ workspace select dev
	source iac/get_env_variables.sh
	terraform -chdir=iac/ apply -target=google_cloud_run_service.github_test_validator_app \
								-target=google_cloud_run_service_iam_policy.noauth \
								-target=google_cloud_run_service.github_test_validator_app \
								-target=google_secret_manager_secret.SQLALCHEMY_URI \
								-target=google_secret_manager_secret_version.SQLALCHEMY_URI_version
