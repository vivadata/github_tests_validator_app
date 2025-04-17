#!/bin/bash

# echo "Please specify GCP project ID : "
# read PROJECT_ID
# echo "Please specify GCP region : "
# read REGION
# unset GOOGLE_APPLICATION_CREDENTIALS
source .env
gcloud config set project $PROJECT_ID
# gcloud auth application-default login
export TF_VAR_project_id=$PROJECT_ID
export TF_VAR_region=$REGION
export TF_VAR_docker_image="${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/no_image"
# terraform -chdir=examples/cloud_run apply -input=true
set +o history
echo "$GH_APP_ID" | gcloud secrets versions add GH_APP_ID --data-file=-
echo "$GH_APP_KEY" | gcloud secrets versions add GH_APP_KEY --data-file=-
echo "$GH_PAT" | gcloud secrets versions add GH_PAT --data-file=-
echo "$GH_TESTS_REPO_NAME" | gcloud secrets versions add GH_TESTS_REPO_NAME --data-file=-
echo "$SQLALCHEMY_URI" | gcloud secrets versions add SQLALCHEMY_URI --data-file=-
# echo "$LOGGING" | gcloud secrets versions add LOGGING --data-file=-
set -o history
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://${REGION}-docker.pkg.dev
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app:latest --platform=linux/amd64 -f ./docker/Dockerfile .
docker tag github_tests_validator_app:latest ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app:latest
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app:latest
# export TF_VAR_docker_image=$(gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry --filter="package=${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app" --sort-by="~UPDATE_TIME" --limit=1 --format="value(format("{0}@{1}",package,version))")
export TF_VAR_docker_image=$(gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry --filter="package=${REGION}-docker.pkg.dev/${PROJECT_ID}/github-app-registry/github_tests_validator_app:latest" --sort-by="~UPDATE_TIME" --format="value(format("{0}@{1}",package,version))" | head -n 1)
echo $TF_VAR_docker_image
# terraform -chdir=examples/cloud_run apply -input=true
