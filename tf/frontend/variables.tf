variable "base_name" {
  type        = string
  description = "Base name for all resources."
}

variable "rg_name" {
  type        = string
  description = "Name of the resource group."
}

variable "container_app_environment_id" {
  type        = string
  description = "container app environment id."
}

variable "container_app_environment_static_ip" {
  type        = string
  description = "static ip address of the container app environment."
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

variable "backend_domain_name" {
  type        = string
  description = "Domain name for the backend."
}