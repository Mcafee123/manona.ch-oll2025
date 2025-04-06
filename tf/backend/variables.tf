variable "base_name" {
  type        = string
  description = "Base name for all resources."
}

variable "rg_name" {
  type        = string
  description = "Name of the resource group."
}

variable "storage_account_id" {
  type        = string
  description = "Storage account id."
}

variable "storage_account_name" {
  type        = string
  description = "Storage account name."
}

variable "storage_account_key" {
  type        = string
  description = "Storage account key."
}

variable "container_app_environment_id" {
  type        = string
  description = "container app environment id."
}

variable "acr_identity_id" {
  type       = string
  description = "webapi acr identity id."
}

variable "acr_login_server" {
  type        = string
  description = "login server for acr."
}

variable "image_name" {
  type        = string
  description = "Name of the keycloak image."
}

variable "domain_name" {
  type        = string
  description = "Domain name for the keycloak instance."
}

variable "cloudflare_zone_id" {
  type        = string
  description = "Cloudflare zone id."
}

variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API token."
  sensitive   = true
}

variable "client_api_key" {
  type        = string
  description = "Client API key for Keycloak."
  sensitive   = true
}

variable "openai_api_key" {
  type        = string
  description = "Client API key for Keycloak."
  sensitive   = true
}