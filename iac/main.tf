# Changing the cloud run service name based on the workspace
locals {
  dynamic_service_name = terraform.workspace == "default" ? var.google_cloud_run_service_name : "${var.google_cloud_run_service_name}-dev"
  artifact_registry_name = terraform.workspace == "default" ? "github-app-registry" : "github-app-registry-dev"
  sql_uri = terraform.workspace == "default" ? var.SQLALCHEMY_URI : "${var.SQLALCHEMY_URI}_dev"
  secret_sql_uri_name = terraform.workspace == "default" ? "SQLALCHEMY_URI" : "SQLALCHEMY_URI_dev"
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.8.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}


# Managing IAM permissions
resource "google_service_account" "service_account" {
  project      = var.project_id
  account_id   = "github-tests-validator-app"
  display_name = "Service Account for Cloud Run that sends data to Google Drive"
}

resource "google_project_iam_member" "service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:github-tests-validator-app@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:github-tests-validator-app@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:github-tests-validator-app@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:github-tests-validator-app@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:github-tests-validator-app@${var.project_id}.iam.gserviceaccount.com"
}



# Creating secrets and updating them if required
# GH_APP_ID
resource "google_secret_manager_secret" "GH_APP_ID" {
  secret_id = "GH_APP_ID"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "GH_APP_ID_version" {
  secret      = google_secret_manager_secret.GH_APP_ID.id
  secret_data = var.GH_APP_ID
}

# GH_APP_KEY
resource "google_secret_manager_secret" "GH_APP_KEY" {
  secret_id = "GH_APP_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "GH_APP_KEY_version" {
  secret      = google_secret_manager_secret.GH_APP_KEY.id
  secret_data = var.GH_APP_KEY
}

# SQLALCHEMY_URI
resource "google_secret_manager_secret" "SQLALCHEMY_URI" {
  secret_id = local.secret_sql_uri_name
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "SQLALCHEMY_URI_version" {
  secret      = google_secret_manager_secret.SQLALCHEMY_URI.id
  secret_data = local.sql_uri
}


# Building docker image
# resource "google_artifact_registry_repository" "github_test_validator_app_registry" {
#   location      = var.region
#   repository_id = "github-app-registry"
#   description   = "Docker repository to store the GitHub App docker image"
#   format        = "DOCKER"
# }

# resource "null_resource" "build_docker_image" {
#   provisioner "local-exec" {
#     command = "gcloud builds submit --tag ${var.region}-docker.pkg.dev/${var.project_id}/github-app-registry/${var.image}:${var.image_version} ."
#   }
# }

# Deploying the Cloud Run service
resource "google_cloud_run_service" "github_test_validator_app" {
  name     = local.dynamic_service_name
  location = var.region

  template {
    metadata {
      annotations = {
        "run.googleapis.com/rollout-timestamp" = timestamp()
      }
    }
    spec {
      timeout_seconds      = 300
      service_account_name = "github-tests-validator-app@${var.project_id}.iam.gserviceaccount.com"
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${local.artifact_registry_name}/${var.image}:${var.image_version}"
        env {
          name = "GH_APP_ID"
          value_from {
            secret_key_ref {
              name = "GH_APP_ID"
              key  = "latest"
            }
          }
        }
        env {
          name = "GH_APP_KEY"
          value_from {
            secret_key_ref {
              name = "GH_APP_KEY"
              key  = "latest"
            }
          }
        }
        env {
          name = local.secret_sql_uri_name
          value_from {
            secret_key_ref {
              name = local.secret_sql_uri_name
              key  = "latest"
            }
          }
        }
      }
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_service.github_test_validator_app.location
  project  = google_cloud_run_service.github_test_validator_app.project
  service  = google_cloud_run_service.github_test_validator_app.name
  policy_data = data.google_iam_policy.noauth.policy_data
}