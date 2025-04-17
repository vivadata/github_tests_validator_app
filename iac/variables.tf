variable "project_id" {
  description = "The project ID."
  type        = string
}

variable "region" {
  description = "The region."
  type        = string
}

variable "image" {
  description = "Name of the docker image"
  type        = string
  default     = "github_tests_validator_app"
}

variable "image_version" {
  description = "Version of the docker image"
  type        = string
  default     = "latest"
}

variable "GH_APP_ID" {
  description = "The GitHub App ID."
  type        = string
}

variable "GH_APP_KEY" {
  description = "The GitHub App private key."
  type        = string
}

variable "SQLALCHEMY_URI" {
  description = "The SQLAlchemy connection URI."
  type        = string
}

