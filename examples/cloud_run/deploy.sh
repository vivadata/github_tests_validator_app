#!/bin/bash

echo "Please specify GCP project ID : "
read PROJECT_ID
source .env
gcloud config set project $PROJECT_ID
gcloud auth application-default login
export TF_project_id=$PROJECT_ID
terraform -chdir=examples/cloud_run apply -input=true
set +o history
echo "$GH_APP_ID" | gcloud secrets versions add GH_APP_ID --data-file=-
echo "$GH_APP_KEY" | gcloud secrets versions add GH_APP_KEY --data-file=-
echo "$GH_PAT" | gcloud secrets versions add GH_PAT --data-file=-
echo "$GH_TESTS_REPO_NAME" | gcloud secrets versions add GH_TESTS_REPO_NAME --data-file=-
echo "$GDRIVE_MAIN_DIRECTORY_NAME" | gcloud secrets versions add GDRIVE_MAIN_DIRECTORY_NAME --data-file=-
echo "$USER_SHARE" | gcloud secrets versions add USER_SHARE --data-file=-
echo "$LOGGING" | gcloud secrets versions add LOGGING --data-file=-
set -o history
