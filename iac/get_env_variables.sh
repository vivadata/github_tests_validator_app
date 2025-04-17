echo "Setting environment variables for Terraform"
source .env
export TF_VAR_project_id=$PROJECT_ID
export TF_VAR_region=$REGION
export TF_VAR_GH_APP_ID=$GH_APP_ID
export TF_VAR_GH_APP_KEY="$(cat asod-test-validator.private-key.pem)"
export TF_VAR_SQLALCHEMY_URI=$SQLALCHEMY_URI