#!/bin/bash

echo "Please specify GCP project ID : "
read PROJECT_ID
source .env
gcloud config set project $PROJECT_ID
gcloud auth application-default logins
export TF_project_id=$PROJECT_ID
terraform -chdir=examples/cloud_run apply -input=true
set +o history
gcloud secrets versions add GH_APP_ID $GH_APP_ID
gcloud secrets versions add GH_APP_KEY $GH_APP_KEY
gcloud secrets versions add GH_PAT $GH_PAT
gcloud secrets versions add GH_TESTS_REPO_NAME $GH_TESTS_REPO_NAME
gcloud secrets versions add GDRIVE_MAIN_DIRECTORY_NAME $GDRIVE_MAIN_DIRECTORY_NAME
gcloud secrets versions add USER_SHARE $USER_SHARE
gcloud secrets versions add LOGGING $LOGGING
set -o history
