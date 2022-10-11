variable "project_id" {
    type    = string
    description = "GCP Project ID"
}

variable "region" {
    type        = string
    description = "GCP region where resources will be deployed"
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.39.0"
    }
  }
}

provider "google" {
  project     = "${var.project_id}"
  region      = "${var.region}"
}

resource "google_project_service" "drive_api_service" {
  project = "${var.project_id}"
  service = "drive.googleapis.com"
  disable_dependent_services = true
}

resource "google_cloud_run_service" "github_test_validator_app" {
    name     = "github-test-validator-app"
    location = "${var.region}"
    template {
        spec {
            timeout_seconds = 300
            service_account_name = "github_tests_validator_app@${var.project_id}.iam.gserviceaccount.com"
            containers {
                image = "ghcr.io/artefactory/github_tests_validator_app:latest"
                env {
                    name = "GH_APP_ID"
                    value_from {
                        secret_key_ref {
                            name = "GH_APP_ID"
                            key = "latest"
                        }
                    }
                }
                env {
                    name = "GH_APP_KEY"
                    value_from {
                        secret_key_ref {
                            name = "GH_APP_KEY"
                            key = "latest"
                        }
                    }
                }
                env {
                    name = "GH_PAT"
                    value_from {
                        secret_key_ref {
                            name = "GH_PAT"
                            key = "latest"
                        }
                    }
                }
                env {
                    name = "GH_TESTS_REPO_NAME"
                    value_from {
                        secret_key_ref {
                            name = "GH_TESTS_REPO_NAME"
                            key = "latest"
                        }
                    }
                }
                env {
                    name = "GDRIVE_MAIN_DIRECTORY_NAME"
                    value_from {
                        secret_key_ref {
                            name = "GDRIVE_MAIN_DIRECTORY_NAME"
                            key = "latest"
                        }
                    }
                }
                env {
                    name = "USER_SHARE"
                    value_from {
                        secret_key_ref {
                            name = "USER_SHARE"
                            key = "latest"
                        }
                    }
                }
                env {
                    name = "LOGGING"
                    value_from {
                        secret_key_ref {
                            name = "LOGGING"
                            key = "latest"
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
  location    = google_cloud_run_service.github_test_validator_app.location
  project     = google_cloud_run_service.github_test_validator_app.project
  service     = google_cloud_run_service.github_test_validator_app.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

resource "google_secret_manager_secret" "GH_APP_ID" {
  secret_id = "GH_APP_ID"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}
resource "google_secret_manager_secret" "GH_APP_KEY" {
  secret_id = "GH_APP_KEY"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}
resource "google_secret_manager_secret" "GH_PAT" {
  secret_id = "GH_PAT"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}
resource "google_secret_manager_secret" "GH_TESTS_REPO_NAME" {
  secret_id = "GH_TESTS_REPO_NAME"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}
resource "google_secret_manager_secret" "GDRIVE_MAIN_DIRECTORY_NAME" {
  secret_id = "GDRIVE_MAIN_DIRECTORY_NAME"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}
resource "google_secret_manager_secret" "USER_SHARE" {
  secret_id = "USER_SHARE"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}

resource "google_secret_manager_secret" "LOGGING" {
  secret_id = "LOGGING"

  replication {
    user_managed {
      replicas {
        location = "${var.region}"
      }
    }
  }
}
