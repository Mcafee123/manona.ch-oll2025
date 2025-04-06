variable "subscription_id" {
  type        = string
  description = "Azure subscription ID."
}

variable "base_name" {
  type        = string
  description = "Base name for all resources."
}

variable "location" {
  type        = string
  description = "location of resources."
}

variable "restart_var" {
  type        = string
  description = "Dummy restart environment variable name."
}

# CLoudflare
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
  description = "Domain name for the backend instance."
}

variable "frontend_domain_name" {
  type        = string
  description = "Domain name for the frontend instance."
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